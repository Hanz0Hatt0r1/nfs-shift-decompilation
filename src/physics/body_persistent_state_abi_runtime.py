"""Neutral BODY/vehicle ABI and persistent-writer frontier for Process B.

This module consolidates source-, machine-code- and cross-contract evidence that
already exists in the repository.  It intentionally does not invent the missing
bridge from solver/contact accumulator state into BODY pose or the +0x78 motion
triplet.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.BodyPersistentStateABI/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

BODY_LANES: dict[str, dict[str, Any]] = {
    "origin": {
        "offsets": (0x00, 0x08, 0x10),
        "storage": "f64x3",
        "observed_roles": (
            "world-point origin subtraction in FUN_00753810/FUN_007ba9e0",
            "body.position input in JOINT/BAR projection",
        ),
        "readers": ("FUN_00753810", "FUN_007ba9e0", "FUN_007bac60", "FUN_007bb090"),
        "writers": (),
        "evidence_level": "source-backed-read-side",
        "writer_status": "unresolved",
    },
    "cross_vector": {
        "offsets": (0x18, 0x20, 0x28),
        "storage": "f64x3",
        "observed_roles": (
            "cross term in FUN_007537b0",
            "body.axis operand in JOINT/BAR projection",
            "input transformed by FUN_007ba7e0",
            "BODY-source input joined into FUN_00766510 in Phase 663",
        ),
        "readers": ("FUN_007537b0", "FUN_007ba7e0", "FUN_007bac60", "FUN_007bb090", "FUN_00766510"),
        "writers": (),
        "evidence_level": "cross-consumer-structural",
        "writer_status": "unresolved",
    },
    "prepared_vector": {
        "offsets": (0x30, 0x38, 0x40),
        "storage": "f64x3",
        "observed_roles": ("FUN_007ba7e0 transformed/scaled output",),
        "readers": ("solver projection path",),
        "writers": ("FUN_007ba7e0",),
        "evidence_level": "source-backed",
        "writer_status": "proven",
    },
    "accumulator_a": {
        "offsets": (0x48, 0x50, 0x58),
        "storage": "f64x3",
        "observed_roles": (
            "angular accumulator in FUN_007ba9e0/FUN_007baa70/FUN_007baaf0",
            "shared velocity triplet in the wheel-local FUN_00755f80 contract",
            "persistent solver-feedback channel in Phases 651-653",
        ),
        "readers": ("FUN_007bc680", "FUN_00755f80"),
        "writers": ("FUN_007ba9e0", "FUN_007baa70", "FUN_007baaf0", "FUN_007b4110", "FUN_00755f80"),
        "evidence_level": "source-backed-with-object-domain-alias",
        "writer_status": "proven-for-accumulator-and-wheel-body-domains",
    },
    "accumulator_b": {
        "offsets": (0x60, 0x68, 0x70),
        "storage": "f64x3",
        "observed_roles": (
            "linear accumulator in FUN_007ba9e0/FUN_007baa70/FUN_007baaf0",
            "persistent solver-feedback channel in Phases 651-653",
        ),
        "readers": ("FUN_007bc680",),
        "writers": ("FUN_007ba9e0", "FUN_007baa70", "FUN_007baaf0", "FUN_007b4110"),
        "evidence_level": "source-backed",
        "writer_status": "proven-for-accumulator-domain",
    },
    "motion_triplet": {
        "offsets": (0x78, 0x80, 0x88),
        "storage": "f64x3",
        "observed_roles": (
            "three BODY velocity doubles in the machine-code-backed FUN_007682c0 speed gate",
            "X/Z BODY speed source in FUN_007675f0",
            "translation term added after the cross product in FUN_007537b0",
            "named correction vector by older solver-projection contracts",
        ),
        "readers": ("FUN_007537b0", "FUN_00753810", "FUN_007675f0", "FUN_007682c0", "FUN_007bac60", "FUN_007bb090"),
        "writers": (),
        "evidence_level": "machine-code-plus-cross-consumer-read-side",
        "writer_status": "unresolved",
    },
    "symmetric_tensor": {
        "offsets": (0xB0, 0xB8, 0xC0, 0xC8, 0xD0),
        "storage": "symmetric-3x3-f64-packed",
        "observed_roles": ("FUN_007ba630 B*diag(D)*B^T output",),
        "readers": ("solver/body preparation path",),
        "writers": ("FUN_007ba630",),
        "evidence_level": "source-backed",
        "writer_status": "proven",
    },
    "basis": {
        "offsets": (0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4),
        "storage": "f32-3x3",
        "observed_roles": (
            "FUN_007aefb0/FUN_007af0a0 transform matrix",
            "BODY frame input to solver/contact/wheel response paths",
        ),
        "readers": ("FUN_007aefb0", "FUN_007af0a0", "FUN_007ba630", "FUN_007ba7e0", "FUN_00766510"),
        "writers": (),
        "evidence_level": "source-backed-read-side",
        "writer_status": "unresolved",
    },
    "diagonal_coefficients": {
        "offsets": (0x128, 0x12C, 0x130),
        "storage": "f32x3",
        "observed_roles": ("FUN_007ba860 coefficient storage",),
        "readers": ("FUN_007ba7e0",),
        "writers": ("FUN_007ba860",),
        "evidence_level": "source-backed",
        "writer_status": "proven",
    },
    "reciprocal_coefficients": {
        "offsets": (0x138, 0x140, 0x148),
        "storage": "f64x3",
        "observed_roles": ("reciprocals of FUN_007ba860 double inputs",),
        "readers": ("FUN_007ba630",),
        "writers": ("FUN_007ba860",),
        "evidence_level": "source-backed",
        "writer_status": "proven",
    },
}

VEHICLE_TOPOLOGY: dict[str, Any] = {
    "component_slots": {
        "count": 4,
        "names": ("FL", "FR", "RL", "RR"),
        "base": 0x400,
        "stride": 0xA80,
        "component_offsets": (0x400, 0xE80, 0x1900, 0x2380),
        "wheel_body_pointer_relative": 0x420,
        "spindle_body_pointer_relative": 0x424,
        "wheel_body_pointer_absolute": (0x820, 0x12A0, 0x1D20, 0x27A0),
        "spindle_body_pointer_absolute": (0x824, 0x12A4, 0x1D24, 0x27A4),
        "evidence": "FUN_0076ed60 + raw disassembly + Phase 634",
    },
    "rear_axle_body_pointer": 0x2E00,
    "wheel_state_slots": {
        "count": 4,
        "base": 0x848,
        "stride": 0xA80,
        "caller": "FUN_00758b50",
    },
    "wheel_runtime_slots": {
        "count": 4,
        "base": 0x400,
        "stride": 0xA80,
        "caller": "FUN_00758b50/FUN_00763570",
    },
    "aux_contact_records": {
        "count": 2,
        "offsets": (0x37D8, 0x3858),
        "caller": "FUN_00766510",
        "callee": "FUN_00758fc0",
    },
    "contact_factor_records": {
        "count": 4,
        "stride": 0x150,
        "previous_base": 0xA70,
        "factor_base": 0xA78,
        "caller": "FUN_00765c40",
    },
}

WRITER_FRONTIER: dict[str, dict[str, Any]] = {
    "FUN_00755f80": {
        "address": 0x00755F80,
        "callers": ("FUN_00763570",),
        "callees": ("FUN_007af0a0", "FUN_007af010"),
        "object_domain": "wheel BODY-compatible object",
        "input_offsets": (0x48, 0x50, 0x58, 0xD4),
        "output_offsets": (0x48, 0x50, 0x58),
        "writes": "shared triplet -= reconstructed transformed longitudinal vector",
        "evidence_level": "source-backed",
        "proven": "direct three-lane state mutation for each wheel object",
        "unknown": "does not establish a writer for BODY +0x78 motion or pose",
    },
    "FUN_00758b50": {
        "address": 0x00758B50,
        "callers": ("FUN_0076d100",),
        "callees": ("FUN_00755950", "FUN_007baa70", "FUN_007baaf0"),
        "object_domain": "vehicle four-wheel runtime",
        "input_offsets": (0x848, 0x400),
        "output_offsets": (0x528, 0x530, 0x548, 0x948, 0x13C8, 0x1E48, 0x28C8),
        "writes": "wheel runtime state plus final BODY accumulator application",
        "evidence_level": "source-backed",
        "proven": "four slots at 0xA80 stride; final helper application reaches wheel and vehicle accumulator paths",
        "unknown": "outer scheduling relationship to SDF solve and pose integration",
    },
    "FUN_00766510": {
        "address": 0x00766510,
        "callers": (),
        "callees": ("FUN_007551e0", "FUN_00758fc0"),
        "object_domain": "wheel/contact vehicle path",
        "input_offsets": (0x18, 0xD4, 0x37D8, 0x3858),
        "output_offsets": (0x48, 0x50, 0x58, 0x60, 0x68, 0x70),
        "writes": "primary/auxiliary response paths reach BODY accumulator helpers",
        "evidence_level": "source-backed-composed",
        "proven": "Phase 663 BODY-source response input and Phase 664 two-record auxiliary pair",
        "unknown": "caller ownership/timing and primary response application transform remain incomplete",
    },
    "FUN_007675f0": {
        "address": 0x007675F0,
        "callers": (),
        "callees": ("FUN_00783a30", "FUN_00759210", "FUN_00759c90", "FUN_007ba9e0"),
        "object_domain": "contact outer path",
        "input_offsets": (0x78, 0x88),
        "output_offsets": (0x48, 0x50, 0x58, 0x60, 0x68, 0x70),
        "writes": "two source-visible FUN_007ba9e0 submissions into BODY accumulators",
        "evidence_level": "source-backed-arithmetic-plus-known-consumer",
        "proven": "outer gate/arithmetic and two accumulator submission calls",
        "unknown": "exact world-point/contribution vectors and caller scheduling",
    },
    "FUN_007ba9e0": {
        "address": 0x007BA9E0,
        "callers": ("FUN_007675f0",),
        "callees": (),
        "object_domain": "BODY",
        "input_offsets": (0x00, 0x08, 0x10),
        "output_offsets": (0x48, 0x50, 0x58, 0x60, 0x68, 0x70),
        "writes": "linear += contribution; angular += (point-origin) x contribution",
        "evidence_level": "source-backed",
        "proven": "exact point contribution arithmetic",
        "unknown": "physical units and higher-level submission meaning",
    },
    "FUN_007b4110": {
        "address": 0x007B4110,
        "callers": ("SDF frame lifecycle",),
        "callees": ("FUN_007baa70", "FUN_007baaf0"),
        "object_domain": "BODY",
        "input_offsets": (),
        "output_offsets": (0x48, 0x50, 0x58, 0x60, 0x68, 0x70),
        "writes": "solved JOINT/HINGE/BAR scalars applied back through BODY accumulator helpers",
        "evidence_level": "source-backed",
        "proven": "terminal post-solve application of the recovered SDF frame",
        "unknown": "no proven subsequent writer into +0x18/+0x78/origin/basis",
    },
    "FUN_00770e80": {
        "address": 0x00770E80,
        "callers": (),
        "callees": ("FUN_0076d100", "FUN_00755a60", "FUN_00760b50"),
        "object_domain": "vehicle",
        "input_offsets": (),
        "output_offsets": (),
        "writes": "orchestration boundary; two FUN_0076d100 physics passes then per-wheel post-pass work",
        "evidence_level": "source-backed-ordering",
        "proven": "two main physics passes with half-step helper work between them",
        "unknown": "caller and exact placement of SDF solve/pose integration inside or around those passes",
    },
}

PERSISTENT_GRAPH = (
    {
        "from": "input/control",
        "to": "vehicle update / FUN_00770e80 frontier",
        "status": "unresolved",
        "evidence": "input tick boundary exists, but force/state mapping is not source-closed",
    },
    {
        "from": "vehicle update / FUN_0076d100",
        "to": "wheel/contact BODY accumulator writers",
        "status": "partially-proven",
        "evidence": "FUN_00758b50 plus FUN_00766510/FUN_007675f0 paths reach BODY accumulator helpers",
    },
    {
        "from": "BODY accumulators +0x48..+0x70",
        "to": "constraints/contact contribution and solve",
        "status": "proven",
        "evidence": "Phases 651-653 plus FUN_007bc680/FUN_007ba570/FUN_007b3f40 lifecycle",
    },
    {
        "from": "solve",
        "to": "FUN_007b4110 post-solve BODY accumulators",
        "status": "proven",
        "evidence": "Phase 409 exact SDF lifecycle and post-solve contracts",
    },
    {
        "from": "post-solve BODY accumulators",
        "to": "BODY +0x18 cross vector / +0x78 motion triplet",
        "status": "unresolved",
        "evidence": "no indexed source-backed writer bridges these offset groups",
    },
    {
        "from": "BODY +0x18/+0x78 motion-side lanes",
        "to": "origin +0x00 and basis +0xd4",
        "status": "unresolved",
        "evidence": "read-side consumers are proven; integration writers are not",
    },
    {
        "from": "origin/basis/motion read-side state",
        "to": "next frame contact/solver consumers",
        "status": "proven-read-side",
        "evidence": "FUN_007537b0/FUN_00753810/FUN_007675f0/FUN_007682c0 and transform helpers consume it",
    },
)

PRIORITY_HANDOFF_ADDRESSES = (
    0x00770E80,
    0x0076D100,
    0x00763570,
    0x00755F80,
    0x00758B50,
    0x00765C40,
    0x00766510,
    0x007675F0,
    0x007B3F40,
    0x007B4110,
    0x007537B0,
    0x00753810,
    0x007BA7E0,
    0x007BA9E0,
    0x007BAA70,
    0x007BAAF0,
)


def writers_for_offset(offset: int) -> tuple[str, ...]:
    """Return functions with a proven write that covers *offset* in this contract."""
    target = int(offset)
    return tuple(
        function
        for function, entry in WRITER_FRONTIER.items()
        if target in entry["output_offsets"]
    )


def unresolved_persistent_lanes() -> tuple[str, ...]:
    """Return BODY lanes that have no source-backed writer in indexed evidence."""
    return tuple(
        name
        for name, lane in BODY_LANES.items()
        if lane["writer_status"] == "unresolved"
    )


def native_pose_handoff() -> dict[str, Any]:
    """Describe the exact blocker before a native pose integrator may be ported."""
    return {
        "ready": False,
        "reason": "persistent BODY pose/motion writer ABI is not closed",
        "required_writer_targets": ("origin", "cross_vector", "motion_triplet", "basis"),
        "priority_function_addresses": PRIORITY_HANDOFF_ADDRESSES,
        "do_not_infer": (
            "accumulator +0x48/+0x60 is not automatically BODY +0x18/+0x78",
            "FUN_00755f80 wheel triplet write is not a chassis pose integrator",
            "read-side transform semantics do not prove frame-to-frame integration order",
        ),
    }


def build_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "source_sha256": SOURCE_SHA256,
        "body_lanes": BODY_LANES,
        "vehicle_topology": VEHICLE_TOPOLOGY,
        "writer_frontier": WRITER_FRONTIER,
        "persistent_graph": PERSISTENT_GRAPH,
        "unresolved_persistent_lanes": unresolved_persistent_lanes(),
        "native_pose_handoff": native_pose_handoff(),
        "status": "writer-frontier-proven-pose-bridge-unresolved",
    }


__all__ = [
    "FORMAT",
    "SOURCE_SHA256",
    "BODY_LANES",
    "VEHICLE_TOPOLOGY",
    "WRITER_FRONTIER",
    "PERSISTENT_GRAPH",
    "PRIORITY_HANDOFF_ADDRESSES",
    "writers_for_offset",
    "unresolved_persistent_lanes",
    "native_pose_handoff",
    "build_contract",
]
