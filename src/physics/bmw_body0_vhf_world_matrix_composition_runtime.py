"""Reference oracle for the merged Process 1 BODY0 -> VHF composition contract."""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct

FORMAT = "SHIFT.NativeBMWBody0VHFWorldMatrixComposition/1"
PROCESS1_FORMAT = "SHIFT.BMWBody0VHFBindFrameFrontier/1"
BODY_INDEX = 0


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _finite(values: tuple[float, ...], count: int, label: str) -> tuple[float, ...]:
    if len(values) != count:
        raise ValueError(f"{label} must contain {count} scalars")
    out = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in out):
        raise ValueError(f"{label} contains non-finite value")
    return out


def _det3(m: tuple[float, ...]) -> float:
    a, b, c = m[0], m[1], m[2]
    d, e, f = m[4], m[5], m[6]
    g, h, i = m[8], m[9], m[10]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _row_affine(values: tuple[float, ...], label: str) -> tuple[float, ...]:
    m = _finite(values, 16, label)
    if any(abs(m[index]) > 1.0e-6 for index in (3, 7, 11)) or abs(m[15] - 1.0) > 1.0e-6:
        raise ValueError(f"{label} is not D3D row-vector affine")
    if abs(_det3(m)) <= 1.0e-12:
        raise ValueError(f"{label} linear block is singular")
    return m


def _mul4(lhs: tuple[float, ...], rhs: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(
        sum(lhs[row * 4 + k] * rhs[k * 4 + column] for k in range(4))
        for row in range(4)
        for column in range(4)
    )


def _inverse_affine_row(values: tuple[float, ...]) -> tuple[float, ...]:
    m = _row_affine(values, "BODY0 bind matrix")
    a, b, c = m[0], m[1], m[2]
    d, e, f = m[4], m[5], m[6]
    g, h, i = m[8], m[9], m[10]
    det = _det3(m)
    inv_det = 1.0 / det
    out = [
        (e * i - f * h) * inv_det, (c * h - b * i) * inv_det, (b * f - c * e) * inv_det, 0.0,
        (f * g - d * i) * inv_det, (a * i - c * g) * inv_det, (c * d - a * f) * inv_det, 0.0,
        (d * h - e * g) * inv_det, (b * g - a * h) * inv_det, (a * e - b * d) * inv_det, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    tx, ty, tz = m[12], m[13], m[14]
    out[12] = -(tx * out[0] + ty * out[4] + tz * out[8])
    out[13] = -(tx * out[1] + ty * out[5] + tz * out[9])
    out[14] = -(tx * out[2] + ty * out[6] + tz * out[10])
    return _row_affine(tuple(out), "inverse BODY0 bind matrix")


def body_pose_row_matrix(
    origin: tuple[float, float, float],
    basis: tuple[float, float, float, float, float, float, float, float, float],
) -> tuple[float, ...]:
    o = _finite(origin, 3, "BODY0 origin")
    b = _finite(basis, 9, "BODY0 basis")
    return _row_affine((
        b[0], b[3], b[6], 0.0,
        b[1], b[4], b[7], 0.0,
        b[2], b[5], b[8], 0.0,
        o[0], o[1], o[2], 1.0,
    ), "BODY0 runtime pose matrix")


@dataclass(frozen=True)
class ProvenVhfBindFrame:
    proven: bool
    matrix: tuple[float, ...]


@dataclass(frozen=True)
class ProvenBody0BindFrame:
    ready: bool
    evidence_proven_static: bool
    body_index: int
    identity_matrix_assumed: bool
    matrix: tuple[float, ...]


def compose(
    *,
    body_index: int,
    origin: tuple[float, float, float],
    basis: tuple[float, float, float, float, float, float, float, float, float],
    vhf_bind: ProvenVhfBindFrame,
    body0_bind: ProvenBody0BindFrame,
) -> dict[str, tuple[float, ...]]:
    if not vhf_bind.proven:
        raise ValueError("Phase 645 VHF bind frame is not proven")
    if not body0_bind.ready or not body0_bind.evidence_proven_static:
        raise ValueError("BODY0 bind-frame proof is not proven-static")
    if body0_bind.body_index != BODY_INDEX or body_index != BODY_INDEX:
        raise ValueError("Phase 704 requires retail BMW chassis BODY 0")
    if body0_bind.identity_matrix_assumed:
        raise ValueError("BODY0 bind frame was produced by identity assumption")

    vhf = _row_affine(vhf_bind.matrix, "Phase 645 VHF bind matrix")
    body_bind_inv = _inverse_affine_row(body0_bind.matrix)
    runtime = body_pose_row_matrix(origin, basis)
    composed = _row_affine(_mul4(_mul4(vhf, body_bind_inv), runtime), "vehicle world matrix")
    return {
        "body0_runtime_row": tuple(_f32(value) for value in runtime),
        "vehicle_world_matrix": tuple(_f32(value) for value in composed),
    }


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "process1_contract": PROCESS1_FORMAT,
        "equation": "M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime",
        "retail_BODY_index": BODY_INDEX,
        "current_retail_BODY0_bind_frame_proven": False,
        "current_retail_world_matrix_ready": False,
        "phase645_VHF_bind_required": True,
        "phase700_selected_BODY_pose_required": True,
        "phase646_output_matrix_float32": True,
        "identity_bind_assumption_allowed": False,
        "live_vulkan_buffer_mutation_enabled": False,
        "fixed_step_auto_schedule": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }
