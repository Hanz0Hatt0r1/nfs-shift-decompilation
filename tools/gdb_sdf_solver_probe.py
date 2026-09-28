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
from pathlib import Path

import gdb

from sdf_runtime_probe_runtime import (
    FUNCTIONS,
    capture_geometry,
    derive_physics_system_from_solver_state,
)


def _u32(inferior: gdb.Inferior, address: int) -> int:
    raw = bytes(inferior.read_memory(int(address), 4))
    return struct.unpack("<I", raw)[0]


def _doubles(inferior: gdb.Inferior, address: int, count: int) -> list[float]:
    if count <= 0:
        return []
    raw = bytes(inferior.read_memory(int(address), int(count) * 8))
    return list(struct.unpack("<" + "d" * int(count), raw))


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
                _u32(inferior, row_table + row * 4) - (
                    _u32(inferior, row_table)
                )
                for row in range(scalar_count)
            ],
            "registers": {
                "esp": esp,
                "ecx": int(gdb.parse_and_eval("$ecx")),
            },
        })
        self.write_json(f"pre_solve_{self.hit:06d}.json", payload)
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
            breakpoint.delete()
        self.breakpoints = [
            SolverEntryProbe(FUNCTIONS["builtin_solver"], "builtin_solver", output),
            PostSolveProbe(FUNCTIONS["post_solve"], "post_solve", output),
        ]
        print(
            "SDF probe installed:",
            f"builtin_solver=0x{FUNCTIONS['builtin_solver']:08x},",
            f"post_solve=0x{FUNCTIONS['post_solve']:08x},",
            f"output={output}",
        )


SDFProbeCommand()
