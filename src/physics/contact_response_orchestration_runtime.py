"""Reference oracle for the proven portions of FUN_00766510 orchestration.

The exact primary FUN_007551e0 response application is intentionally represented
as an evidence barrier.  The caller must provide the BODY accumulator state after
that unresolved application before the source-visible two-record auxiliary path
may execute.  No zero/default accumulator is synthesized.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

from aux_contact_response_runtime import build_local_response
from sdf_body_impulse_runtime import apply_body_accumulator_delta
from wheel_contact_response_runtime import (
    ContactResponse,
    CurveParameters,
    ResponseTable,
    evaluate_contact_response,
)

FORMAT = "SHIFT.ContactResponseOrchestrationRuntime/1"
FUNCTION = "FUN_00766510"
QUERY_PRODUCER = "FUN_00765c40"
PRIMARY_BUILDER = "FUN_007551e0"
PRIMARY_APPLICATION = "FUN_007baa70"
AUX_HELPER = "FUN_00758fc0"
AUX_RECORD_OFFSETS = (0x37D8, 0x3858)


@dataclass(frozen=True)
class AuxRecordOracleInput:
    active: bool
    transformed_record_point: tuple[float, float, float]
    local_point: tuple[float, float, float]
    directional_multiplier: float
    gain: float
    scale: float


@dataclass(frozen=True)
class ContactResponseOrchestrationResult:
    query_scalar: float
    response: ContactResponse
    body_accumulator_at_primary_barrier: dict[str, tuple[float, float, float]]
    body_accumulator: dict[str, tuple[float, float, float]]
    auxiliary_applied_count: int
    auxiliary_order: tuple[int, ...]


def _vec3(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    result = tuple(float(value) for value in values)
    if not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def _accumulator(
    value: Mapping[str, Sequence[float]] | None,
) -> dict[str, tuple[float, float, float]]:
    if value is None:
        raise ValueError("FUN_00766510 primary response application state is unresolved")
    return {
        "angular": _vec3(value.get("angular", ()), "post-primary angular accumulator"),
        "linear": _vec3(value.get("linear", ()), "post-primary linear accumulator"),
    }


def execute_fun_00766510_partial_contact_chain(
    *,
    original_world_y: float,
    returned_contact_height: float | None,
    fallback_and_query_limit: float,
    depth_slope: float,
    base_offset: float,
    directional_curve: CurveParameters,
    response_table: ResponseTable,
    tangent_x: float,
    tangent_z: float,
    response_input: Sequence[float],
    body_accumulator_after_primary_application: Mapping[str, Sequence[float]] | None,
    aux_reference_point: Sequence[float],
    aux_records: Sequence[AuxRecordOracleInput],
) -> ContactResponseOrchestrationResult:
    """Compose proven response and auxiliary stages around an explicit barrier."""
    original_world_y = float(original_world_y)
    fallback_and_query_limit = float(fallback_and_query_limit)
    if not isfinite(original_world_y) or not isfinite(fallback_and_query_limit):
        raise ValueError("query scalar inputs must be finite")
    if returned_contact_height is None:
        query_scalar = fallback_and_query_limit
    else:
        contact_height = float(returned_contact_height)
        if not isfinite(contact_height):
            raise ValueError("returned contact height must be finite")
        query_scalar = original_world_y - contact_height

    # Proven FUN_00765c40 -> FUN_00766510 response stage.
    response = evaluate_contact_response(
        query_scalar=query_scalar,
        query_limit=fallback_and_query_limit,
        depth_slope=depth_slope,
        base_offset=base_offset,
        directional_curve=directional_curve,
        response_table=response_table,
        tangent_x=tangent_x,
        tangent_z=tangent_z,
        response_input=response_input,
    )

    # Evidence barrier: exact primary response transform/application is not yet
    # frozen.  Do not infer the accumulator state from response.response_vector.
    barrier = _accumulator(body_accumulator_after_primary_application)
    state = {
        "angular": list(barrier["angular"]),
        "linear": list(barrier["linear"]),
    }

    if len(aux_records) != 2:
        raise ValueError("FUN_00766510 requires exactly two auxiliary records")
    reference = _vec3(aux_reference_point, "auxiliary reference point")
    applied_order: list[int] = []

    for index, record in enumerate(aux_records):
        transformed_point = _vec3(
            record.transformed_record_point,
            f"aux[{index}] transformed record point",
        )
        local_point = _vec3(record.local_point, f"aux[{index}] local point")
        local = build_local_response(
            record_active=record.active,
            transformed_record_point=local_point,
            reference_point=reference,
            directional_multiplier=record.directional_multiplier,
            gain=record.gain,
            scale=record.scale,
        )
        if not record.active or local.relative_point.z >= 0.0:
            continue
        applied = apply_body_accumulator_delta(
            state,
            transformed_point,
            local.local_response.as_tuple(),
            sign=1,
        )
        state = {
            "angular": list(applied["angular"]),
            "linear": list(applied["linear"]),
        }
        applied_order.append(index)

    final_state = {
        "angular": tuple(state["angular"]),
        "linear": tuple(state["linear"]),
    }
    return ContactResponseOrchestrationResult(
        query_scalar=query_scalar,
        response=response,
        body_accumulator_at_primary_barrier=barrier,
        body_accumulator=final_state,
        auxiliary_applied_count=len(applied_order),
        auxiliary_order=tuple(applied_order),
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "proven_order": [
            "FUN_00765c40 query scalar -> FUN_00766510 response stage",
            "explicit unresolved primary-application barrier",
            "FUN_00758fc0 at +0x37d8",
            "FUN_00758fc0 at +0x3858",
        ],
        "primary_application": {
            "builder": PRIMARY_BUILDER,
            "consumer": PRIMARY_APPLICATION,
            "state": "required external post-application BODY accumulator",
            "missing_state": "reject",
        },
        "auxiliary": {
            "helper": AUX_HELPER,
            "record_offsets": ["+0x37d8", "+0x3858"],
            "count": 2,
            "sequential_accumulator_handoff": True,
        },
        "runtime_scheduling": "unproven",
        "full_FUN_00766510_ported": False,
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "AUX_RECORD_OFFSETS",
    "AuxRecordOracleInput",
    "ContactResponseOrchestrationResult",
    "execute_fun_00766510_partial_contact_chain",
    "build_contract",
]
