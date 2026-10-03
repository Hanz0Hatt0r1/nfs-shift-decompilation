"""Closed Process B BODY persistent-state ABI built from the proven frame integrator.

Version 1 intentionally froze the writer frontier before the persistent BODY
integration primitive had been recovered.  Process A subsequently established
`FUN_007b2270 -> FUN_007bab70` and the exact half-step placement inside
`FUN_00770e80`.  This module composes that stronger static evidence without
rewriting the historical v1 contract.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from body_frame_integration_static import (
    FORMAT as FRAME_INTEGRATION_FORMAT,
    build_contract as build_frame_integration_contract,
    validate_contract as validate_frame_integration_contract,
)
from body_persistent_state_abi_runtime import (
    BODY_LANES as V1_BODY_LANES,
    SOURCE_SHA256,
    VEHICLE_TOPOLOGY,
    WRITER_FRONTIER as V1_WRITER_FRONTIER,
)

FORMAT = "SHIFT.BodyPersistentStateABI/2"
BODY_ARRAY_LOOP = "FUN_007b2270"
BODY_INTEGRATOR = "FUN_007bab70"
HALF_STEP_ORCHESTRATOR = "FUN_00765470"
OUTER_VEHICLE_UPDATE = "FUN_00770e80"


def _append_unique(values: tuple[str, ...], *extra: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*values, *extra)))


def _closed_body_lanes() -> dict[str, dict[str, Any]]:
    lanes = deepcopy(V1_BODY_LANES)

    lanes["origin"]["observed_roles"] = _append_unique(
        lanes["origin"]["observed_roles"],
        "persistent translation target: origin += motion_triplet * dt in FUN_007bab70",
    )
    lanes["origin"]["writers"] = _append_unique(lanes["origin"]["writers"], BODY_INTEGRATOR)
    lanes["origin"]["evidence_level"] = "source-plus-retail-machine-code"
    lanes["origin"]["writer_status"] = "proven-persistent-frame-integration"

    lanes["motion_triplet"]["observed_roles"] = _append_unique(
        lanes["motion_triplet"]["observed_roles"],
        "persistent translation rate integrated into origin by FUN_007bab70",
        "updated from accumulator_b through BODY+0x90 scale in FUN_007bab70",
    )
    lanes["motion_triplet"]["readers"] = _append_unique(
        lanes["motion_triplet"]["readers"], BODY_INTEGRATOR
    )
    lanes["motion_triplet"]["writers"] = _append_unique(
        lanes["motion_triplet"]["writers"], BODY_INTEGRATOR
    )
    lanes["motion_triplet"]["evidence_level"] = "source-plus-retail-machine-code"
    lanes["motion_triplet"]["writer_status"] = "proven-persistent-frame-integration"

    lanes["prepared_vector"]["observed_roles"] = _append_unique(
        lanes["prepared_vector"]["observed_roles"],
        "persistent accumulator_a integration target in FUN_007bab70",
    )
    lanes["prepared_vector"]["writers"] = _append_unique(
        lanes["prepared_vector"]["writers"], BODY_INTEGRATOR
    )
    lanes["prepared_vector"]["evidence_level"] = "source-plus-retail-machine-code"
    lanes["prepared_vector"]["writer_status"] = "proven"

    lanes["cross_vector"]["observed_roles"] = _append_unique(
        lanes["cross_vector"]["observed_roles"],
        "persistent rotational-rate state rebuilt as symmetric_tensor * prepared_vector",
        "rotation increment input to basis update in FUN_007bab70",
    )
    lanes["cross_vector"]["readers"] = _append_unique(
        lanes["cross_vector"]["readers"], BODY_INTEGRATOR
    )
    lanes["cross_vector"]["writers"] = _append_unique(
        lanes["cross_vector"]["writers"], BODY_INTEGRATOR
    )
    lanes["cross_vector"]["evidence_level"] = "source-plus-retail-machine-code"
    lanes["cross_vector"]["writer_status"] = "proven-persistent-frame-integration"

    lanes["basis"]["observed_roles"] = _append_unique(
        lanes["basis"]["observed_roles"],
        "persistent orientation basis updated from cross_vector * dt via FUN_007afdd0",
    )
    lanes["basis"]["writers"] = _append_unique(lanes["basis"]["writers"], BODY_INTEGRATOR)
    lanes["basis"]["evidence_level"] = "source-plus-retail-machine-code"
    lanes["basis"]["writer_status"] = "proven-persistent-frame-integration"

    lanes["accumulator_a"]["readers"] = _append_unique(
        lanes["accumulator_a"]["readers"], BODY_INTEGRATOR
    )
    lanes["accumulator_b"]["readers"] = _append_unique(
        lanes["accumulator_b"]["readers"], BODY_INTEGRATOR
    )
    return lanes


BODY_LANES = _closed_body_lanes()


def _closed_writer_frontier() -> dict[str, dict[str, Any]]:
    frontier = deepcopy(V1_WRITER_FRONTIER)
    frontier["FUN_007b4110"]["unknown"] = (
        "persistent feedback is subsequently integrated by "
        "FUN_00765470 -> FUN_007b2270 -> FUN_007bab70"
    )
    frontier[OUTER_VEHICLE_UPDATE]["callees"] = _append_unique(
        frontier[OUTER_VEHICLE_UPDATE]["callees"],
        HALF_STEP_ORCHESTRATOR,
        "FUN_007b8810",
    )
    frontier[OUTER_VEHICLE_UPDATE]["proven"] = (
        "two FUN_0076d100 passes; each is followed by FUN_00765470(0.5 * dt) "
        "and FUN_007b8810"
    )
    frontier[OUTER_VEHICLE_UPDATE]["unknown"] = (
        "caller ownership and exact relationship to rendered-frame cadence"
    )
    frontier[HALF_STEP_ORCHESTRATOR] = {
        "address": 0x00765470,
        "callers": (OUTER_VEHICLE_UPDATE,),
        "callees": ("FUN_00763570", "FUN_007b3f40", "FUN_007b4110", BODY_ARRAY_LOOP),
        "object_domain": "physics half-step orchestration",
        "input_offsets": (),
        "output_offsets": (),
        "writes": "orders wheel/shared work, SDF solve, post-solve feedback, then BODY integration",
        "evidence_level": "direct-callgraph-plus-static-frame-integration-contract",
        "proven": "FUN_00763570 -> FUN_007b3f40 -> FUN_007b4110 -> FUN_007b2270",
        "unknown": "retail semantic class/method name",
    }
    frontier[BODY_ARRAY_LOOP] = {
        "address": 0x007B2270,
        "callers": (HALF_STEP_ORCHESTRATOR,),
        "callees": (BODY_INTEGRATOR,),
        "object_domain": "physics BODY array owner",
        "input_offsets": (),
        "output_offsets": (),
        "writes": "iterates owner+0x14 BODY array with count owner+0x10 and stride 0x170",
        "evidence_level": "source-plus-retail-machine-code",
        "proven": "same f64 timestep is passed to FUN_007bab70 for every BODY element",
        "unknown": "retail semantic class/method name",
    }
    frontier[BODY_INTEGRATOR] = {
        "address": 0x007BAB70,
        "callers": (BODY_ARRAY_LOOP,),
        "callees": ("FUN_007afdd0", "FUN_007ba630", "FUN_007aefb0"),
        "object_domain": "BODY",
        "input_offsets": (
            0x18, 0x20, 0x28,
            0x30, 0x38, 0x40,
            0x48, 0x50, 0x58,
            0x60, 0x68, 0x70,
            0x78, 0x80, 0x88,
            0x90,
            0xB0, 0xB8, 0xC0, 0xC8, 0xD0,
            0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4,
        ),
        "output_offsets": (
            0x00, 0x08, 0x10,
            0x18, 0x20, 0x28,
            0x30, 0x38, 0x40,
            0x78, 0x80, 0x88,
            0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4,
        ),
        "writes": (
            "origin += motion_triplet * dt; "
            "motion_triplet += accumulator_b * BODY[0x90] * dt; "
            "prepared_vector += accumulator_a * dt; "
            "cross_vector = symmetric_tensor * prepared_vector; "
            "basis updated from cross_vector * dt"
        ),
        "evidence_level": "source-plus-retail-machine-code",
        "proven": "persistent BODY frame integration primitive",
        "unknown": "physical unit/name of BODY+0x90 and retail semantic method name",
    }
    return frontier


WRITER_FRONTIER = _closed_writer_frontier()

PERSISTENT_GRAPH = (
    {
        "from": "input/control",
        "to": "vehicle update / FUN_00770e80 frontier",
        "status": "unresolved",
        "evidence": "higher-level input/control ownership remains outside the closed BODY writer bridge",
    },
    {
        "from": "vehicle update / FUN_0076d100",
        "to": "wheel/contact BODY accumulator writers",
        "status": "partially-proven",
        "evidence": "FUN_00758b50 plus FUN_00766510/FUN_007675f0 paths reach BODY accumulator helpers",
    },
    {
        "from": "BODY accumulators +0x48..+0x70",
        "to": "FUN_007b3f40 solve -> FUN_007b4110 post-solve feedback",
        "status": "proven",
        "evidence": "recovered SDF lifecycle and post-solve accumulator application",
    },
    {
        "from": "FUN_007b4110 post-solve feedback",
        "to": "FUN_007b2270 BODY-array loop -> FUN_007bab70",
        "status": "proven",
        "evidence": "FUN_00765470 direct-call order places integration after post-solve feedback",
    },
    {
        "from": "accumulator_b +0x60..+0x70",
        "to": "motion_triplet +0x78..+0x88",
        "status": "proven",
        "evidence": "FUN_007bab70: motion_triplet += accumulator_b * BODY[0x90] * dt",
    },
    {
        "from": "motion_triplet +0x78..+0x88",
        "to": "origin +0x00..+0x10",
        "status": "proven",
        "evidence": "FUN_007bab70: origin += motion_triplet * dt",
    },
    {
        "from": "accumulator_a +0x48..+0x58",
        "to": "prepared_vector +0x30..+0x40",
        "status": "proven",
        "evidence": "FUN_007bab70: prepared_vector += accumulator_a * dt",
    },
    {
        "from": "prepared_vector +0x30..+0x40",
        "to": "cross_vector +0x18..+0x28",
        "status": "proven",
        "evidence": "FUN_007bab70 + machine-code EAX preservation join through FUN_007ba630/FUN_007aefb0",
    },
    {
        "from": "cross_vector +0x18..+0x28",
        "to": "basis +0xd4..+0xf4",
        "status": "proven",
        "evidence": "FUN_007bab70 calls FUN_007afdd0 with cross_vector * dt",
    },
    {
        "from": "origin/basis/motion persistent state",
        "to": "next contact/solver consumers",
        "status": "proven-read-side",
        "evidence": "existing BODY transform/contact/solver readers consume the updated lanes",
    },
)


def writers_for_offset(offset: int) -> tuple[str, ...]:
    target = int(offset)
    return tuple(
        function
        for function, entry in WRITER_FRONTIER.items()
        if target in entry["output_offsets"]
    )


def unresolved_persistent_lanes() -> tuple[str, ...]:
    return tuple(
        name
        for name, lane in BODY_LANES.items()
        if lane["writer_status"] == "unresolved"
    )


def native_pose_handoff() -> dict[str, Any]:
    frame = build_frame_integration_contract()
    validate_frame_integration_contract(frame)
    return {
        "ready": True,
        "static_contract": FRAME_INTEGRATION_FORMAT,
        "body_array_loop": BODY_ARRAY_LOOP,
        "body_integrator": BODY_INTEGRATOR,
        "body_stride": 0x170,
        "half_step_orchestrator": HALF_STEP_ORCHESTRATOR,
        "outer_update": OUTER_VEHICLE_UPDATE,
        "half_step_scale": 0.5,
        "closed_writer_targets": ("origin", "cross_vector", "prepared_vector", "motion_triplet", "basis"),
        "remaining_unknowns": (
            "retail semantic class/method names for integration helpers",
            "physical unit/name of BODY+0x90 beyond multiplicative scale role",
            "whether FUN_00770e80 executes exactly once per rendered frame",
            "higher-level input/control ownership before FUN_00770e80",
        ),
        "scope": "ready for source-backed integrator/oracle/native port; rendered-frame cadence remains separate",
    }


def build_contract() -> dict[str, Any]:
    frame = build_frame_integration_contract()
    validate_frame_integration_contract(frame)
    return {
        "format": FORMAT,
        "version": 2,
        "source_sha256": SOURCE_SHA256,
        "frame_integration_contract": FRAME_INTEGRATION_FORMAT,
        "body_lanes": BODY_LANES,
        "vehicle_topology": VEHICLE_TOPOLOGY,
        "writer_frontier": WRITER_FRONTIER,
        "persistent_graph": PERSISTENT_GRAPH,
        "unresolved_persistent_lanes": unresolved_persistent_lanes(),
        "native_pose_handoff": native_pose_handoff(),
        "status": "persistent-body-writer-bridge-closed",
    }


__all__ = [
    "FORMAT",
    "SOURCE_SHA256",
    "BODY_ARRAY_LOOP",
    "BODY_INTEGRATOR",
    "HALF_STEP_ORCHESTRATOR",
    "OUTER_VEHICLE_UPDATE",
    "BODY_LANES",
    "VEHICLE_TOPOLOGY",
    "WRITER_FRONTIER",
    "PERSISTENT_GRAPH",
    "writers_for_offset",
    "unresolved_persistent_lanes",
    "native_pose_handoff",
    "build_contract",
]
