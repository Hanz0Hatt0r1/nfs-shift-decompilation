"""GDB Python probe for the builtin SHIFT SDF solver path.

Usage from a GDB session attached to the retail SHIFT.exe Wine process:
    source tools/gdb_sdf_solver_probe.py
    sdf-probe /tmp/shift-solver-capture
    continue

The probe automatically writes one JSON file at the builtin solver entry and
one post-solve JSON file at FUN_007b4110 for each hit.
"""
from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gdb

from sdf_runtime_probe_runtime import (
    FUNCTIONS,
    capture_geometry,
    derive_physics_system_from_solver_state,
    describe_frame_entry_backend,
)
from specialized_provider_capture_runtime import build_provider_capture_payload
from specialized_provider_runtime import get_provider
from specialized_provider_vtable_lifecycle_runtime import get_vtable_lifecycle
from specialized_provider_scalar_reset_capture_runtime import (
    validate_scalar_reset_event,
)
from specialized_provider_scalar_reset_effect_runtime import (
    build_reset_effect_event,
)
from specialized_provider_scalar_reset_callsite_runtime import (
    attribute_reset_event,
)
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_row_storage_runtime import get_row_pointers


def _u32(inferior: gdb.Inferior, address: int) -> int:
    raw = bytes(inferior.read_memory(int(address), 4))
    return struct.unpack("<I", raw)[0]


def _doubles(inferior: gdb.Inferior, address: int, count: int) -> list[float]:
    if count <= 0:
        return []
    raw = bytes(inferior.read_memory(int(address), int(count) * 8))
    return list(struct.unpack("<" + "d" * int(count), raw))


_SCALAR_RESET_EVENT_COUNT = 0

_LAST_FRAME_ENTRY = {
    "frame_index": None,
    "physics_system": None,
    "scalar_reset_start_count": 0,
    "scalar_reset_end_count": 0,
}


def _provider_snapshot(
    inferior: gdb.Inferior,
    provider_id: int,
    stage: str,
    hit: int,
) -> dict:
    layout = get_storage_layout(provider_id)
    workspace = _doubles(
        inferior,
        layout.factor_workspace_base,
        layout.factor_workspace_doubles,
    )
    output_vector = _doubles(
        inferior,
        layout.output_vector_base,
        layout.output_vector_doubles,
    )
    row_pointers = [
        _u32(inferior, layout.row_pointer_base + row * 4)
        for row in range(layout.scalar_count)
    ]
    payload = build_provider_capture_payload(
        provider_id=provider_id,
        stage=stage,
        workspace=workspace,
        output_vector=output_vector,
        row_pointers=row_pointers,
        frame_index=_LAST_FRAME_ENTRY["frame_index"],
        physics_system=_LAST_FRAME_ENTRY["physics_system"],
        source="gdb_sdf_solver_probe.py",
        metadata={
            "capture_kind": stage,
            "provider_solve_hit": hit,
            "scalar_reset_event_count": _SCALAR_RESET_EVENT_COUNT,
            "scalar_reset_events_since_frame_entry": (
                _SCALAR_RESET_EVENT_COUNT
                - int(_LAST_FRAME_ENTRY["scalar_reset_start_count"])
            ),
        },
    )
    payload["registers"] = {
        "eip": int(gdb.parse_and_eval("$eip")),
        "esp": int(gdb.parse_and_eval("$esp")),
    }
    payload["source_address"] = hex(
        get_provider(provider_id).solve_function
    )
    return payload


def _append_jsonl(
    output_dir: Path,
    name: str,
    payload: dict,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / name
    with target.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )


def _provider_id_from_runtime_pointer(
    inferior: gdb.Inferior,
    provider_pointer: int,
) -> tuple[int | None, int | None]:
    if provider_pointer == 0:
        return None, None

    try:
        vtable = _u32(inferior, provider_pointer)
    except (gdb.MemoryError, RuntimeError):
        return None, None

    for provider_id in (0, 1):
        if vtable == get_provider(provider_id).vtable_address:
            return provider_id, vtable

    return None, vtable


def _matrix_from_rows(
    inferior: gdb.Inferior,
    row_pointer_table: int,
    scalar_count: int,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for row in range(int(scalar_count)):
        row_ptr = _u32(inferior, row_pointer_table + row * 4)
        rows.append(_doubles(inferior, row_ptr, scalar_count))
    return rows


class _BaseProbe(gdb.Breakpoint):
    def __init__(self, address: int, label: str, output_dir: Path) -> None:
        super().__init__(f"*0x{address:08x}", type=gdb.BP_BREAKPOINT, internal=False)
        self.label = label
        self.output_dir = output_dir
        self.hit = 0

    def write_json(self, name: str, payload: dict) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / name
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def stop(self) -> bool:
        self.hit += 1
        return True


class ProviderResetReturnProbe(gdb.FinishBreakpoint):
    """Capture source-derived reset sentinels after provider reset returns."""

    def __init__(
        self,
        frame: gdb.Frame,
        provider_id: int,
        output_dir: Path,
        selector: int,
        frame_index: int | None,
        reset_event_count: int,
        provider_pointer: int,
        provider_vtable: int,
        diagonal_address: int,
        output_address: int,
        diagonal_before: float,
        output_before: float,
    ) -> None:
        super().__init__(frame, internal=False)
        self.provider_id = provider_id
        self.output_dir = output_dir
        self.selector = selector
        self.frame_index = frame_index
        self.reset_event_count = reset_event_count
        self.provider_pointer = provider_pointer
        self.provider_vtable = provider_vtable
        self.diagonal_address = diagonal_address
        self.output_address = output_address
        self.diagonal_before = diagonal_before
        self.output_before = output_before

    def stop(self) -> bool:
        inferior = gdb.selected_inferior()
        diagonal_after = _doubles(
            inferior,
            self.diagonal_address,
            1,
        )[0]
        output_after = _doubles(
            inferior,
            self.output_address,
            1,
        )[0]
        event = build_reset_effect_event(
            provider_id=self.provider_id,
            selector=self.selector,
            frame_index=self.frame_index,
            reset_event_count=self.reset_event_count,
            provider_pointer=self.provider_pointer,
            provider_vtable=self.provider_vtable,
            diagonal_before=self.diagonal_before,
            diagonal_after=diagonal_after,
            output_before=self.output_before,
            output_after=output_after,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "provider_reset_effects.jsonl"
        with target.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
        return False


class ProviderResetProbe(_BaseProbe):
    """Capture provider reset sentinels at +0x1c entry and on return."""

    def __init__(
        self,
        address: int,
        provider_id: int,
        output_dir: Path,
    ) -> None:
        super().__init__(
            address,
            f"provider{provider_id}_reset",
            output_dir,
        )
        self.provider_id = provider_id
        self.return_breakpoints: list[ProviderResetReturnProbe] = []

    def stop(self) -> bool:
        self.hit += 1
        inferior = gdb.selected_inferior()
        provider_pointer = int(gdb.parse_and_eval("$ecx"))
        esp = int(gdb.parse_and_eval("$esp"))
        selector = _u32(inferior, esp + 0x04)
        provider_id, provider_vtable = _provider_id_from_runtime_pointer(
            inferior,
            provider_pointer,
        )
        if (
            provider_id != self.provider_id
            or provider_vtable is None
        ):
            return False

        addresses = get_storage_layout(self.provider_id)
        if not 0 <= selector < addresses.scalar_count:
            return False
        row_pointer = get_row_pointers(self.provider_id)[selector]
        diagonal_address = row_pointer + selector * 8
        output_address = (
            addresses.output_vector_base + selector * 8
        )
        diagonal_before = _doubles(
            inferior,
            diagonal_address,
            1,
        )[0]
        output_before = _doubles(
            inferior,
            output_address,
            1,
        )[0]

        return_probe = ProviderResetReturnProbe(
            gdb.newest_frame(),
            self.provider_id,
            self.output_dir,
            selector,
            _LAST_FRAME_ENTRY["frame_index"],
            _SCALAR_RESET_EVENT_COUNT,
            provider_pointer,
            provider_vtable,
            diagonal_address,
            output_address,
            diagonal_before,
            output_before,
        )
        self.return_breakpoints.append(return_probe)
        return False


class ScalarResetProbe(_BaseProbe):
    """Capture each FUN_007b2210 selector and provider dispatch context."""

    def __init__(
        self,
        address: int,
        output_dir: Path,
    ) -> None:
        super().__init__(
            address,
            "scalar_reset",
            output_dir,
        )
        self.event_index = 0

    def stop(self) -> bool:
        global _SCALAR_RESET_EVENT_COUNT

        self.hit += 1
        self.event_index += 1
        _SCALAR_RESET_EVENT_COUNT += 1
        _LAST_FRAME_ENTRY["scalar_reset_end_count"] = _SCALAR_RESET_EVENT_COUNT
        inferior = gdb.selected_inferior()

        physics_system = int(gdb.parse_and_eval("$ecx"))
        esp = int(gdb.parse_and_eval("$esp"))
        selector = _u32(inferior, esp + 0x04)
        caller_return_address = _u32(inferior, esp)
        scalar_count = _u32(inferior, physics_system + 0x34)
        provider_pointer = _u32(
            inferior,
            physics_system + 0x48,
        )
        provider_id, provider_vtable = _provider_id_from_runtime_pointer(
            inferior,
            provider_pointer,
        )

        event = {
            "format": "SHIFT.SpecializedProviderScalarResetCaptureRuntime/2",
            "version": 2,
            "frame_index": _LAST_FRAME_ENTRY["frame_index"],
            "call_index": self.event_index,
            "physics_system": physics_system,
            "provider_pointer": provider_pointer,
            "provider_vtable": provider_vtable,
            "provider_id": provider_id,
            "scalar_count": scalar_count,
            "selector": selector,
            "caller_return_address": caller_return_address,
            "source_function": "FUN_007b2210",
            "source_address": 0x007B2210,
            "registers": {
                "ecx": physics_system,
                "esp": esp,
                "eip": int(gdb.parse_and_eval("$eip")),
            },
        }

        validation = validate_scalar_reset_event(event)
        attribution = attribute_reset_event(event)
        event["callsite"] = attribution
        event["capture_ready"] = (
            bool(validation["ready"])
            and bool(attribution["ready"])
        )
        event["capture_errors"] = (
            list(validation["errors"])
            + list(attribution.get("errors") or [])
        )
        _append_jsonl(
            self.output_dir,
            "scalar_reset_events.jsonl",
            event,
        )
        return False



class FrameEntryProbe(_BaseProbe):
    def stop(self) -> bool:
        self.hit += 1
        inferior = gdb.selected_inferior()
        physics_system = int(gdb.parse_and_eval("$ecx"))
        scalar_count = _u32(inferior, physics_system + 0x34)
        provider = _u32(inferior, physics_system + 0x48)
        solver_state = _u32(inferior, physics_system + 0x4C)
        payload = describe_frame_entry_backend(
            physics_system=physics_system,
            scalar_count=scalar_count,
            provider=provider,
            solver_state=solver_state,
        )
        _LAST_FRAME_ENTRY["frame_index"] = self.hit
        _LAST_FRAME_ENTRY["physics_system"] = physics_system
        _LAST_FRAME_ENTRY["scalar_reset_start_count"] = (
            _SCALAR_RESET_EVENT_COUNT
        )
        _LAST_FRAME_ENTRY["scalar_reset_end_count"] = (
            _SCALAR_RESET_EVENT_COUNT
        )
        payload.update({
            "capture_kind": "frame_entry_backend",
            "frame_index": self.hit,
            "registers": {
                "ecx": physics_system,
                "eip": int(gdb.parse_and_eval("$eip")),
            },
        })
        self.write_json(f"frame_entry_{self.hit:06d}.json", payload)
        return False


class SolverEntryProbe(_BaseProbe):
    def stop(self) -> bool:
        self.hit += 1
        inferior = gdb.selected_inferior()
        esp = int(gdb.parse_and_eval("$esp"))
        solver_state = _u32(inferior, esp + 0x04)
        row_table = _u32(inferior, esp + 0x08)
        rhs_ptr = _u32(inferior, esp + 0x0C)
        scalar_count = _u32(inferior, esp + 0x10)
        physics_system = derive_physics_system_from_solver_state(solver_state)

        matrix = _matrix_from_rows(inferior, row_table, scalar_count)
        rhs = _doubles(inferior, rhs_ptr, scalar_count)
        payload = capture_geometry(
            physics_system=physics_system,
            solver_state=solver_state,
            scalar_count=scalar_count,
            row_pointer_table=row_table,
            rhs_pointer=rhs_ptr,
        )
        payload.update({
            "capture_kind": "pre_solve_builtin_solver",
            "frame_index": self.hit,
            "matrix": matrix,
            "rhs": rhs,
            "row_indices": [
                (
                    _u32(inferior, row_table + row * 4)
                    - _u32(inferior, row_table)
                ) // 8
                for row in range(scalar_count)
            ],
            "registers": {
                "esp": esp,
                "ecx": int(gdb.parse_and_eval("$ecx")),
            },
        })
        self.write_json(f"pre_solve_{self.hit:06d}.json", payload)
        return False


class ProviderSolveReturnProbe(gdb.FinishBreakpoint):
    """Capture provider state immediately after a specialized solve returns."""

    def __init__(
        self,
        frame: gdb.Frame,
        provider_id: int,
        output_dir: Path,
        hit: int,
    ) -> None:
        super().__init__(frame, internal=False)
        self.provider_id = provider_id
        self.output_dir = output_dir
        self.hit = hit

    def stop(self) -> bool:
        inferior = gdb.selected_inferior()
        payload = _provider_snapshot(
            inferior,
            self.provider_id,
            "post-solve-provider",
            self.hit,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / (
            f"provider_post_{self.provider_id}_{self.hit:06d}.json"
        )
        target.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        return False


class ProviderSolveProbe(_BaseProbe):
    """Capture raw provider state at solve entry and arm a return probe."""

    def __init__(
        self,
        address: int,
        provider_id: int,
        output_dir: Path,
    ) -> None:
        super().__init__(
            address,
            f"provider{provider_id}_solver",
            output_dir,
        )
        self.provider_id = provider_id
        self.return_breakpoints: list[ProviderSolveReturnProbe] = []

    def stop(self) -> bool:
        self.hit += 1
        inferior = gdb.selected_inferior()
        payload = _provider_snapshot(
            inferior,
            self.provider_id,
            "pre-solve-provider",
            self.hit,
        )
        self.write_json(
            f"provider_pre_{self.provider_id}_{self.hit:06d}.json",
            payload,
        )
        return_probe = ProviderSolveReturnProbe(
            gdb.newest_frame(),
            self.provider_id,
            self.output_dir,
            self.hit,
        )
        self.return_breakpoints.append(return_probe)
        return False


class PostSolveProbe(_BaseProbe):
    def stop(self) -> bool:
        self.hit += 1
        inferior = gdb.selected_inferior()
        physics_system = int(gdb.parse_and_eval("$ecx"))
        scalar_count = _u32(inferior, physics_system + 0x34)
        rhs_ptr = _u32(inferior, physics_system + 0x40)
        rhs = _doubles(inferior, rhs_ptr, scalar_count)
        payload = {
            "format": "SHIFT.SDFSolverPostSolveProbe/1",
            "version": 1,
            "status": "captured",
            "ready": True,
            "capture_kind": "post_solve",
            "frame_index": self.hit,
            "image_base": 0x00400000,
            "physics_system": physics_system,
            "scalar_count": scalar_count,
            "rhs_pointer": rhs_ptr,
            "rhs": rhs,
            "source_function": "FUN_007b4110",
            "source_address": FUNCTIONS["post_solve"],
        }
        self.write_json(f"post_solve_{self.hit:06d}.json", payload)
        return False


class SDFProbeCommand(gdb.Command):
    """Install or replace the SHIFT SDF solver runtime probe."""

    def __init__(self) -> None:
        super().__init__("sdf-probe", gdb.COMMAND_USER)
        self.breakpoints: list[gdb.Breakpoint] = []

    def invoke(self, argument: str, from_tty: bool) -> None:
        args = gdb.string_to_argv(argument)
        if len(args) != 1:
            raise gdb.GdbError("usage: sdf-probe OUTPUT_DIR")
        output = Path(os.path.expanduser(args[0])).resolve()

        for breakpoint in self.breakpoints:
            for return_breakpoint in getattr(
                breakpoint,
                "return_breakpoints",
                [],
            ):
                try:
                    return_breakpoint.delete()
                except RuntimeError:
                    pass
            breakpoint.delete()
        self.breakpoints = [
            FrameEntryProbe(FUNCTIONS["frame_entry"], "frame_entry", output),
            SolverEntryProbe(FUNCTIONS["builtin_solver"], "builtin_solver", output),
            PostSolveProbe(FUNCTIONS["post_solve"], "post_solve", output),
            ProviderSolveProbe(
                get_provider(0).solve_function,
                0,
                output,
            ),
            ProviderSolveProbe(
                get_provider(1).solve_function,
                1,
                output,
            ),
            ScalarResetProbe(
                0x007B2210,
                output,
            ),
            ProviderResetProbe(
                get_vtable_lifecycle(0).reset_function,
                0,
                output,
            ),
            ProviderResetProbe(
                get_vtable_lifecycle(1).reset_function,
                1,
                output,
            ),
        ]
        print(
            "SDF probe installed:",
            f"builtin_solver=0x{FUNCTIONS['builtin_solver']:08x},",
            f"provider0_solver=0x{get_provider(0).solve_function:08x},",
            f"provider1_solver=0x{get_provider(1).solve_function:08x},",
            "scalar_reset=0x007b2210,",
            f"provider0_reset=0x{get_vtable_lifecycle(0).reset_function:08x},",
            f"provider1_reset=0x{get_vtable_lifecycle(1).reset_function:08x},",
            f"post_solve=0x{FUNCTIONS['post_solve']:08x},",
            f"output={output}",
        )


SDFProbeCommand()
