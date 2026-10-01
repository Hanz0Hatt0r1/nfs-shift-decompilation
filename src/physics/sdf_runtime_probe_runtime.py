"""Pure helpers for the SHIFT SDF runtime probe.

The GDB-facing script uses these helpers so address calculations stay testable
outside GDB. All addresses are derived from the retail frame ABI observed in
SHIFT.exe.c; no address discovery is attempted.
"""
from __future__ import annotations

import struct
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFRuntimeProbe/1"
IMAGE_BASE = 0x00400000

FUNCTIONS = {
    "relation_state_mutation": 0x00757D2C,
    "frame_entry": 0x007B3F40,
    "builtin_solver": 0x007B0F20,
    "post_solve": 0x007B4110,
}

RELATION_STATE_MUTATION_LAYOUT = {
    "component_base_offset": 0x400,
    "component_stride": 0xA80,
    "component_count": 4,
    "wheel_body_offset": 0x420,
    "spindle_body_offset": 0x424,
    "rear_axle_body_offset": 0x2E00,
}
RELATION_STATE_MUTATION_SLOT_NAMES = ("FL", "FR", "RL", "RR")

PHYSICS_OFFSETS = {
    "solver_scalar_count": 0x34,
    "global_matrix_rows": 0x3C,
    "global_rhs": 0x40,
    "provider": 0x48,
    "solver_state": 0x4C,
}


def u32_from_bytes(data: bytes, offset: int = 0) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("u32 read exceeds buffer")
    return struct.unpack_from("<I", data, offset)[0]


def read_pointer_from_memory(memory: bytes, offset: int) -> int:
    return u32_from_bytes(memory, offset)


def solver_call_stack_layout(
    esp: int,
) -> dict[str, int]:
    """Return the addresses of FUN_007b0f20 __thiscall arguments."""
    base = int(esp)
    return {
        "return_address": base,
        "solver_state": base + 0x04,
        "row_pointer_table": base + 0x08,
        "rhs": base + 0x0C,
        "scalar_count": base + 0x10,
    }


def derive_physics_system_from_solver_state(solver_state: int) -> int:
    return int(solver_state) - PHYSICS_OFFSETS["solver_state"]


def describe_frame_entry_backend(
    *,
    physics_system: int,
    scalar_count: int,
    provider: int,
    solver_state: int | None = None,
) -> dict[str, Any]:
    """Describe the backend selected by FUN_007b3f40 from source-backed fields."""
    backend = "provider" if int(provider) != 0 else "builtin"
    return {
        "format": "SHIFT.SDFRuntimeProbeFrameEntry/1",
        "version": 1,
        "status": "captured",
        "ready": True,
        "function": "FUN_007b3f40",
        "physics_system": int(physics_system),
        "scalar_count": int(scalar_count),
        "provider": int(provider),
        "backend": backend,
        "builtin_solver_expected": backend == "builtin",
        "solver_state": None if solver_state is None else int(solver_state),
        "offsets": dict(PHYSICS_OFFSETS),
    }


def describe_relation_state_mutation_entry(
    *,
    vehicle_pointer: int,
    component_offset: int,
    wheel_body_pointer: int,
    spindle_body_pointer: int,
    rear_axle_body_pointer: int,
    caller_return_address: int | None = None,
) -> dict[str, Any]:
    """Normalize the source-backed FUN_00757d2c entry register/memory state.

    Raw retail disassembly proves that the entry uses ECX as the vehicle
    pointer and EAX as component_slot * 0xA80 before the first instruction
    forms vehicle + 0x400 + EAX.
    """
    vehicle = int(vehicle_pointer)
    offset = int(component_offset)
    stride = RELATION_STATE_MUTATION_LAYOUT["component_stride"]
    count = RELATION_STATE_MUTATION_LAYOUT["component_count"]

    errors: list[str] = []
    component_slot: int | None = None
    if offset < 0 or offset % stride != 0:
        errors.append("component-offset-not-slot-stride")
    else:
        candidate = offset // stride
        if not 0 <= candidate < count:
            errors.append("component-slot-out-of-range")
        else:
            component_slot = candidate

    component_block_pointer = (
        vehicle
        + RELATION_STATE_MUTATION_LAYOUT["component_base_offset"]
        + offset
    )
    spindle_present = int(spindle_body_pointer) != 0
    branch = (
        "spindle-bar-endpoint"
        if spindle_present
        else "wheel-rear-axle-pair"
    )

    return {
        "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
        "version": 1,
        "status": "captured" if not errors else "invalid",
        "ready": not errors,
        "capture_errors": errors,
        "source_function": "FUN_00757d2c",
        "source_address": FUNCTIONS["relation_state_mutation"],
        "vehicle_pointer": vehicle,
        "component_offset": offset,
        "component_slot": component_slot,
        "component_slot_name": (
            None
            if component_slot is None
            else RELATION_STATE_MUTATION_SLOT_NAMES[component_slot]
        ),
        "component_block_pointer": component_block_pointer,
        "wheel_body_pointer": int(wheel_body_pointer),
        "spindle_body_pointer": int(spindle_body_pointer),
        "rear_axle_body_pointer": int(rear_axle_body_pointer),
        "spindle_body_present": spindle_present,
        "source_branch": branch,
        "caller_return_address": (
            None
            if caller_return_address is None
            else int(caller_return_address)
        ),
        "entry_abi": {
            "vehicle_pointer_register": "ECX",
            "component_offset_register": "EAX",
        },
        "layout": dict(RELATION_STATE_MUTATION_LAYOUT),
    }

def capture_geometry(
    *,
    physics_system: int,
    scalar_count: int,
    row_pointer_table: int,
    rhs_pointer: int,
    solver_state: int,
) -> dict[str, Any]:
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "probe-layout",
        "ready": True,
        "image_base": IMAGE_BASE,
        "physics_system": int(physics_system),
        "solver_state": int(solver_state),
        "scalar_count": n,
        "matrix_rows_pointer": int(row_pointer_table),
        "rhs_pointer": int(rhs_pointer),
        "sizes": {
            "rhs_bytes": n * 8,
            "matrix_bytes": n * n * 8,
            "row_pointer_bytes": n * 4,
        },
        "functions": FUNCTIONS,
        "physics_offsets": PHYSICS_OFFSETS,
    }


def validate_dump_shape(
    *,
    scalar_count: int,
    rhs: Sequence[float],
    matrix: Sequence[Sequence[float]],
) -> dict[str, Any]:
    n = int(scalar_count)
    errors: list[str] = []
    if len(rhs) != n:
        errors.append("rhs-length")
    if len(matrix) != n:
        errors.append("matrix-row-count")
    if any(len(row) != n for row in matrix):
        errors.append("matrix-column-count")
    return {
        "format": "SHIFT.SDFRuntimeProbeShape/1",
        "version": 1,
        "ready": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "scalar_count": n,
        "matrix_cells": n * n,
        "rhs_bytes": n * 8,
        "matrix_bytes": n * n * 8,
    }


def describe_sdf_runtime_probe_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-runtime-probe",
        "ready": True,
        "image_base": IMAGE_BASE,
        "breakpoints": {
            "relation_state_mutation": {
                "address": FUNCTIONS["relation_state_mutation"],
                "abi": "retail-entry-register-state",
                "vehicle_pointer_register": "ECX",
                "component_offset_register": "EAX",
                "component_offset_rule": "slot * 0xA80",
            },
            "frame_entry": {
                "address": FUNCTIONS["frame_entry"],
                "abi": "__fastcall",
                "physics_system_register": "ECX",
            },
            "builtin_solver": {
                "address": FUNCTIONS["builtin_solver"],
                "abi": "__thiscall",
                "stack_arguments": {
                    "solver_state": "[ESP+0x04]",
                    "row_pointer_table": "[ESP+0x08]",
                    "rhs": "[ESP+0x0c]",
                    "scalar_count": "[ESP+0x10]",
                },
            },
            "post_solve": {
                "address": FUNCTIONS["post_solve"],
                "abi": "__fastcall",
                "physics_system_register": "ECX",
            },
        },
        "capture": {
            "pre_solve": "builtin solver breakpoint dumps matrix/RHS before solve",
            "post_solve": "FUN_007b4110 breakpoint dumps solved RHS/vector",
            "provider_path": "frame entry exposes provider pointer, but provider virtual slot remains opaque",
            "relation_state_mutation": (
                "FUN_00757d2c observer records exact slot/body-pointer branch "
                "inputs without modifying retail state"
            ),
        },
        "output": {
            "format": "SHIFT.SDFSolverCaptureRuntime/1",
            "matrix_order": "row-major logical rows from retail row-pointer table",
            "number_format": "little-endian IEEE-754 binary64",
        },
        "limitations": [
            "This probe targets the builtin solver path; provider implementations remain opaque.",
            "A running retail target and debugger attachment are required.",
            "The script does not modify the retail executable or infer unknown addresses.",
        ],
    }


__all__ = [
    "IMAGE_BASE",
    "FUNCTIONS",
    "PHYSICS_OFFSETS",
    "RELATION_STATE_MUTATION_LAYOUT",
    "RELATION_STATE_MUTATION_SLOT_NAMES",
    "solver_call_stack_layout",
    "derive_physics_system_from_solver_state",
    "capture_geometry",
    "describe_relation_state_mutation_entry",
    "describe_frame_entry_backend",
    "validate_dump_shape",
    "describe_sdf_runtime_probe_contract",
]
