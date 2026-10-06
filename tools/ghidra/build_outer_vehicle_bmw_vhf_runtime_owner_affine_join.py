#!/usr/bin/env python3
"""Join the proven outer-Vehicle render affine to the exact BMW VHF runtime owner.

This pass is a deterministic join over already-positive committed Process-1
contracts. It does not re-decompile the renderer and it does not infer ownership
from callgraph adjacency:

* SHIFT.OuterVehicleRenderSnapshotAffineBridge/1 proves the selected outer
  Vehicle snapshot -> participant render affine path and records that the same
  participant uses +0x1340 as the Vehicle Render Model consumed by FUN_004a8c20;
* SHIFT.BMWVehicleRenderModelResourceJoin/1 carries positive
  SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1 provenance and proves that
  the selected BMW Vehicle Render Model is the canonical BMW_M3_E36 VHF.

The result proves the executable-side affine-carrier/runtime-owner join only.
The outer Vehicle-root -> VHF HIERARCHY-root frame relation remains fail-closed
until an independent resource-local HIERARCHY-root contract is consumed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleBMWVHFRuntimeOwnerAffineJoin/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
OWNER_FORMAT = "SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1"
BMW_RESOURCE_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
CANONICAL_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
VEHICLE_RENDER_MODEL = "BMW_M3_E36.vhf"

DEFAULT_BRIDGE = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "process1_outer_vehicle_render_snapshot_affine_bridge.json"
)
DEFAULT_BMW_RESOURCE_JOIN = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "process1_bmw_vehicle_render_model_resource_join.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _require_retail_identity(value: Mapping[str, Any], label: str) -> None:
    retail = value.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError(f"{label}: retail identity missing")
    if retail.get("program") != PROGRAM or retail.get("md5") != PE_MD5:
        raise ValueError(f"{label}: retail executable identity drift")


def _validate_bridge(bridge: Mapping[str, Any]) -> dict[str, Any]:
    if bridge.get("format") != BRIDGE_FORMAT or bridge.get("ready") is not True:
        raise ValueError("outer Vehicle render-snapshot affine bridge is not positive")
    _require_retail_identity(bridge, "bridge")
    retail = bridge.get("retail")
    assert isinstance(retail, Mapping)
    if retail.get("source_sha256") != CANONICAL_SOURCE_SHA256:
        raise ValueError("bridge decompiler-source identity drift")

    handoff = bridge.get("handoff")
    relation = bridge.get("render_participant_relation")
    snapshot = bridge.get("snapshot_relation")
    slot = bridge.get("slot_identity")
    if not all(isinstance(row, Mapping) for row in (handoff, relation, snapshot, slot)):
        raise ValueError("bridge required sections missing")
    assert isinstance(handoff, Mapping)
    assert isinstance(relation, Mapping)
    assert isinstance(snapshot, Mapping)
    assert isinstance(slot, Mapping)

    for gate in (
        "outer_vehicle_render_snapshot_slot_identity_ready",
        "outer_vehicle_to_render_root_symbolic_affine_ready",
        "render_root_translation_delta_producer_bounded",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"bridge gate not ready: {gate}")
    if slot.get("physical_slot_producer_consumer_bridge_ready") is not True:
        raise ValueError("bridge physical slot continuity is not ready")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(gate) is not False:
            raise ValueError(f"bridge unexpectedly preclaims downstream gate: {gate}")

    expected = {
        "vehicle_render_model": "participant+0x1340",
        "derived_rotation_matrix": "participant+0x1028",
        "root_translation": [
            "participant+0xa10",
            "participant+0xa14",
            "participant+0xa18",
        ],
        "world_affine_consumed_by": "FUN_004a8c20",
        "world_affine_translation_slots": [12, 13, 14],
    }
    for key, expected_value in expected.items():
        if relation.get(key) != expected_value:
            raise ValueError(f"bridge render participant relation drift: {key}")
    if relation.get("node_local_FUN_004ae150_promoted_to_root_setter") is not False:
        raise ValueError("bridge unexpectedly promotes FUN_004ae150 to root setter")
    if snapshot.get("translation_formula") != "P_snapshot = P_outer + R_outer * delta_local":
        raise ValueError("bridge translation formula drift")
    if snapshot.get("independent_rotation_source_present") is not False:
        raise ValueError("bridge unexpectedly admits an independent snapshot rotation source")
    return dict(relation)


def _validate_bmw_join(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if value.get("format") != BMW_RESOURCE_FORMAT or value.get("ready") is not True:
        raise ValueError("BMW Vehicle Render Model resource join is not positive")
    _require_retail_identity(value, "BMW resource join")

    owner = value.get("input_owner_proof")
    selected = value.get("selected_vehicle_descriptor")
    resource = value.get("canonical_bmw_vhf_resource")
    handoff = value.get("handoff")
    if not all(isinstance(row, Mapping) for row in (owner, selected, resource, handoff)):
        raise ValueError("BMW resource join required sections missing")
    assert isinstance(owner, Mapping)
    assert isinstance(selected, Mapping)
    assert isinstance(resource, Mapping)
    assert isinstance(handoff, Mapping)

    if owner.get("format") != OWNER_FORMAT or owner.get("vehicle_render_hierarchy_owner_ready") is not True:
        raise ValueError("BMW resource join does not consume a positive RenderHierarchy owner proof")
    source_commit = str(owner.get("source_commit") or "")
    if len(source_commit) != 40:
        raise ValueError("upstream RenderHierarchy owner source commit missing")
    if owner.get("vehicle_render_model_property_name") != "Vehicle Render Model":
        raise ValueError("Vehicle Render Model property-name drift")
    if owner.get("vehicle_render_model_property_field") != "+0x54":
        raise ValueError("Vehicle Render Model descriptor field drift")

    if selected.get("vehicle_name") != "BMW_M3_E36":
        raise ValueError("selected BMW descriptor identity drift")
    if selected.get("property_name") != "Vehicle Render Model":
        raise ValueError("selected BMW property-name drift")
    if selected.get("property_value") != VEHICLE_RENDER_MODEL:
        raise ValueError("selected BMW Vehicle Render Model value drift")
    if selected.get("selected_BMW_vehicle_render_model_value_ready") is not True:
        raise ValueError("selected BMW Vehicle Render Model gate is not ready")

    if str(resource.get("resolved_path") or "").lower() != CANONICAL_VHF:
        raise ValueError("canonical BMW VHF resource path drift")
    if resource.get("root_tag") != "CAR" or resource.get("root_name") != "BMW_M3_E36":
        raise ValueError("canonical BMW VHF CAR identity drift")
    if resource.get("root_node_type") != "HIERARCHY":
        raise ValueError("canonical BMW VHF root-node type drift")
    if resource.get("canonical_BMW_VHF_resource_join_ready") is not True:
        raise ValueError("canonical BMW VHF resource gate is not ready")
    decoded_sha = str(resource.get("decoded_sha256") or "")
    if len(decoded_sha) != 64:
        raise ValueError("canonical BMW VHF decoded SHA-256 missing")

    for gate in (
        "vehicle_render_hierarchy_owner_ready",
        "selected_BMW_vehicle_render_model_value_ready",
        "canonical_BMW_VHF_resource_join_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"BMW resource join gate not ready: {gate}")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(gate) is not False:
            raise ValueError(f"BMW resource join unexpectedly preclaims downstream gate: {gate}")
    return dict(owner), dict(selected), dict(resource)


def analyze(bridge: Mapping[str, Any], bmw_join: Mapping[str, Any]) -> dict[str, Any]:
    participant_relation = _validate_bridge(bridge)
    owner_proof, selected, resource = _validate_bmw_join(bmw_join)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "outer-render-affine-to-canonical-bmw-vhf-runtime-owner-proven-resource-local-root-pending",
        "ready": True,
        "BLOCKER": "SHIFT.BMWBody0BindFrameProof/1: outer Vehicle-root -> exact BMW VHF HIERARCHY root relation",
        "INPUT": [BRIDGE_FORMAT, OWNER_FORMAT, BMW_RESOURCE_FORMAT],
        "OUTPUT": "exact executable-side outer Vehicle render affine -> canonical BMW VHF runtime render-model owner join",
        "CONSUMER": "Process 1 final outer Vehicle-root -> BMW VHF HIERARCHY-root identity/fixed-affine adjudication using Process 3 resource-local root semantics",
        "retail": {
            "program": PROGRAM,
            "md5": PE_MD5,
            "decompiler_source_sha256": CANONICAL_SOURCE_SHA256,
        },
        "upstream": {
            "affine_bridge": {
                "format": BRIDGE_FORMAT,
                "status": bridge.get("status"),
                "translation_formula": bridge["snapshot_relation"]["translation_formula"],
                "physical_slot_producer_consumer_bridge_ready": bridge["slot_identity"]["physical_slot_producer_consumer_bridge_ready"],
                "vehicle_render_model_field": participant_relation["vehicle_render_model"],
                "world_affine_consumer": participant_relation["world_affine_consumed_by"],
            },
            "render_hierarchy_owner": {
                "format": OWNER_FORMAT,
                "source_commit": owner_proof["source_commit"],
                "vehicle_render_hierarchy_owner_ready": True,
                "vehicle_render_model_property_name": owner_proof["vehicle_render_model_property_name"],
                "vehicle_render_model_property_field": owner_proof["vehicle_render_model_property_field"],
            },
            "bmw_resource_join": {
                "format": BMW_RESOURCE_FORMAT,
                "vehicle_name": selected["vehicle_name"],
                "selected_vehicle_render_model": selected["property_value"],
                "canonical_vhf": resource["resolved_path"],
                "decoded_sha256": resource["decoded_sha256"],
            },
        },
        "same_participant_executable_join": {
            "root_rotation_source": participant_relation["derived_rotation_matrix"],
            "root_translation_source": participant_relation["root_translation"],
            "render_model_owner": participant_relation["vehicle_render_model"],
            "world_affine_consumer": participant_relation["world_affine_consumed_by"],
            "world_affine_translation_slots": participant_relation["world_affine_translation_slots"],
            "selected_runtime_render_model_resource": CANONICAL_VHF,
            "same_participant_affine_and_render_model_owner_ready": True,
            "callgraph_adjacency_used_as_owner_proof": False,
        },
        "claim": {
            "outer_vehicle_translation_to_runtime_render_owner_formula": "P_runtime_owner = P_outer + R_outer * delta_local",
            "outer_vehicle_rotation_to_runtime_render_owner_provenance": "common source R_outer through normalize -> matrix_to_quaternion -> participant root quaternion -> participant+0x1028 derived matrix",
            "canonical_bmw_vhf_runtime_render_model_owner": CANONICAL_VHF,
            "outer_vehicle_affine_reaches_exact_bmw_vhf_runtime_owner": True,
            "resource_local_vhf_hierarchy_root_affine_applied_or_identity": False,
        },
        "handoff": {
            "outer_vehicle_affine_to_canonical_BMW_VHF_runtime_owner_ready": True,
            "canonical_BMW_VHF_runtime_affine_carrier_ready": True,
            "canonical_BMW_VHF_resource_local_root_semantics_required": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": "consume Process 3 exact canonical BMW VHF HIERARCHY Root local/frame semantics; compose it with this proven runtime affine carrier and adjudicate identity or exact fixed affine delta",
        },
        "limits": {
            "FUN_004ae150_promoted_to_root_setter": False,
            "runtime_render_model_owner_equals_hierarchy_root_node": False,
            "resource_identity_implies_frame_identity": False,
            "identity_valued_resource_matrix_implies_dynamic_identity": False,
            "orientation_roundtrip_bitwise_identity_claimed": False,
            "callgraph_adjacency_is_ownership": False,
            "equal_numeric_values_are_provenance": False,
            "visual_similarity_is_frame_identity": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--bmw-resource-join", type=Path, default=DEFAULT_BMW_RESOURCE_JOIN)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze(_read_json(args.bridge), _read_json(args.bmw_resource_join))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
