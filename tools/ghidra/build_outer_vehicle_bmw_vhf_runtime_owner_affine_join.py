#!/usr/bin/env python3
"""Join the proven outer-Vehicle render affine to the exact BMW VHF runtime owner.

This is intentionally *not* a VHF HIERARCHY-root frame-identity proof.  It joins
three already-positive Process-1 contracts and one exact decompiler-source
witness:

* SHIFT.OuterVehicleRenderSnapshotAffineBridge/1 proves the selected outer
  Vehicle snapshot -> participant render affine path;
* SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1 proves participant+0x1340 is
  the selected Vehicle Render Model / RenderHierarchy materialization owner;
* SHIFT.BMWVehicleRenderModelResourceJoin/1 proves that selected BMW resource is
  vehicles/bmw_m3_e36/bmw_m3_e36.vhf;
* FUN_00480700 passes the affine assembled from the same participant root pose
  directly to FUN_004a8c20(participant+0x1340, affine).

The output therefore proves the executable-side affine carrier/owner join.  It
keeps the outer Vehicle-root -> VHF HIERARCHY-root relation fail-closed until an
independent resource-local root-frame contract is joined.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OuterVehicleBMWVHFRuntimeOwnerAffineJoin/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
OWNER_FORMAT = "SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1"
BMW_RESOURCE_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
VEHICLE_RENDER_MODEL = "BMW_M3_E36.vhf"
PARTICIPANT_WORLD_CONSUMER = "FUN_00480700"
EXPECTED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

# These are exact source witnesses already used by the positive upstream
# contracts.  Requiring them in one function establishes the same-participant
# affine/owner join without treating callgraph adjacency as ownership.
WORLD_CONSUMER_FACTS = (
    "FUN_0042fc90(local_50,(undefined4 *)(param_1 + 0x1028));",
    "local_20=*(undefined4 *)(param_1 + 0xa10);",
    "local_1c=*(undefined4 *)(param_1 + 0xa14);",
    "local_18=*(undefined4 *)(param_1 + 0xa18);",
    "FUN_004a8c20(param_1 + 0x1340,local_50);",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(value: str) -> str:
    return "".join(value.split())


def _skip_quoted(text: str, index: int, quote: str) -> int:
    index += 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        ch = text[index]
        index += 1
        if ch == quote:
            return index
    raise ValueError("unterminated quoted literal in decompiler source")


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 1
    index = start + 1
    while index < len(text):
        ch = text[index]
        if ch in {'\"', "'"}:
            index = _skip_quoted(text, index, ch)
            continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            index = len(text) if end < 0 else end + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated block comment in decompiler source")
            index = end + 2
            continue
        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError(f"unterminated {opening}{closing} region")


def _extract_function(source: str, name: str) -> str:
    offset = 0
    while True:
        position = source.find(name, offset)
        if position < 0:
            raise ValueError(f"decompiler source missing definition for {name}")
        cursor = position + len(name)
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source) or source[cursor] != "(":
            offset = position + len(name)
            continue
        end_args = _matching(source, cursor, "(", ")")
        cursor = end_args + 1
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor < len(source) and source[cursor] == "{":
            end_body = _matching(source, cursor, "{", "}")
            return source[position : end_body + 1]
        offset = position + len(name)


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
    handoff = bridge.get("handoff")
    relation = bridge.get("render_participant_relation")
    snapshot = bridge.get("snapshot_relation")
    if not isinstance(handoff, Mapping) or not isinstance(relation, Mapping) or not isinstance(snapshot, Mapping):
        raise ValueError("bridge required sections missing")
    for gate in (
        "outer_vehicle_render_snapshot_slot_identity_ready",
        "outer_vehicle_to_render_root_symbolic_affine_ready",
        "render_root_translation_delta_producer_bounded",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"bridge gate not ready: {gate}")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims outer/VHF root identity")
    if handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims outer/VHF fixed affine delta")
    if handoff.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims BODY0 bind-frame proof")
    if relation.get("vehicle_render_model") != "participant+0x1340":
        raise ValueError("bridge participant Vehicle Render Model field drift")
    if relation.get("derived_rotation_matrix") != "participant+0x1028":
        raise ValueError("bridge participant derived rotation field drift")
    if relation.get("root_translation") != [
        "participant+0xa10", "participant+0xa14", "participant+0xa18"
    ]:
        raise ValueError("bridge participant root translation fields drift")
    if relation.get("world_affine_consumed_by") != "FUN_004a8c20":
        raise ValueError("bridge world-affine consumer drift")
    if snapshot.get("translation_formula") != "P_snapshot = P_outer + R_outer * delta_local":
        raise ValueError("bridge translation formula drift")
    return dict(relation)


def _validate_bmw_join(value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
    if owner.get("vehicle_render_model_property_name") != "Vehicle Render Model":
        raise ValueError("Vehicle Render Model property-name drift")
    if owner.get("vehicle_render_model_property_field") != "+0x54":
        raise ValueError("Vehicle Render Model descriptor field drift")
    if selected.get("property_value") != VEHICLE_RENDER_MODEL:
        raise ValueError("selected BMW Vehicle Render Model value drift")
    if selected.get("selected_BMW_vehicle_render_model_value_ready") is not True:
        raise ValueError("selected BMW Vehicle Render Model gate is not ready")
    if str(resource.get("resolved_path") or "").lower() != CANONICAL_VHF:
        raise ValueError("canonical BMW VHF resource path drift")
    if resource.get("canonical_BMW_VHF_resource_join_ready") is not True:
        raise ValueError("canonical BMW VHF resource gate is not ready")
    for gate in (
        "vehicle_render_hierarchy_owner_ready",
        "selected_BMW_vehicle_render_model_value_ready",
        "canonical_BMW_VHF_resource_join_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"BMW resource join gate not ready: {gate}")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("BMW resource join unexpectedly preclaims outer/VHF root identity")
    if handoff.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("BMW resource join unexpectedly preclaims BODY0 bind-frame proof")
    return dict(owner), dict(resource)


def analyze(
    bridge_path: Path,
    bmw_resource_join_path: Path,
    decompiler_source: Path,
) -> dict[str, Any]:
    bridge = _read_json(bridge_path)
    bmw_join = _read_json(bmw_resource_join_path)
    participant_relation = _validate_bridge(bridge)
    owner_proof, resource = _validate_bmw_join(bmw_join)

    source_sha = _sha256(decompiler_source)
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise ValueError("retail decompiler-source SHA-256 drift")
    bridge_source_sha = str((bridge.get("retail") or {}).get("source_sha256") or "")
    if bridge_source_sha != source_sha:
        raise ValueError("bridge source SHA-256 does not match supplied decompiler source")

    source = decompiler_source.read_text(encoding="utf-8", errors="strict")
    body = _extract_function(source, PARTICIPANT_WORLD_CONSUMER)
    compact = _compact(body)
    for fact in WORLD_CONSUMER_FACTS:
        if _compact(fact) not in compact:
            raise ValueError(f"{PARTICIPANT_WORLD_CONSUMER}: required source fact drift: {fact}")

    owner_source_commit = str(owner_proof.get("source_commit") or "")
    if len(owner_source_commit) != 40:
        raise ValueError("upstream RenderHierarchy owner source commit missing")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "outer-render-affine-to-canonical-bmw-vhf-runtime-owner-proven-resource-local-root-pending",
        "ready": True,
        "BLOCKER": "SHIFT.BMWBody0BindFrameProof/1: outer Vehicle-root -> exact BMW VHF HIERARCHY root relation",
        "INPUT": [
            BRIDGE_FORMAT,
            OWNER_FORMAT,
            BMW_RESOURCE_FORMAT,
            "exact retail SHIFT.exe.c source witness",
        ],
        "OUTPUT": "exact executable-side outer Vehicle render affine -> canonical BMW VHF runtime render-model owner join",
        "CONSUMER": "Process 1 final outer Vehicle-root -> BMW VHF HIERARCHY-root identity/fixed-affine adjudication using Process 3 resource-local root semantics",
        "retail": {
            "program": PROGRAM,
            "md5": PE_MD5,
            "decompiler_source_sha256": source_sha,
        },
        "upstream": {
            "affine_bridge": {
                "format": BRIDGE_FORMAT,
                "status": bridge.get("status"),
                "translation_formula": bridge["snapshot_relation"]["translation_formula"],
                "vehicle_render_model_field": participant_relation["vehicle_render_model"],
                "world_affine_consumer": participant_relation["world_affine_consumed_by"],
            },
            "render_hierarchy_owner": {
                "format": OWNER_FORMAT,
                "source_commit": owner_source_commit,
                "vehicle_render_hierarchy_owner_ready": True,
                "vehicle_render_model_property_name": owner_proof["vehicle_render_model_property_name"],
                "vehicle_render_model_property_field": owner_proof["vehicle_render_model_property_field"],
            },
            "bmw_resource_join": {
                "format": BMW_RESOURCE_FORMAT,
                "selected_vehicle_render_model": VEHICLE_RENDER_MODEL,
                "canonical_vhf": CANONICAL_VHF,
                "decoded_sha256": resource.get("decoded_sha256"),
            },
        },
        "same_participant_executable_join": {
            "function": PARTICIPANT_WORLD_CONSUMER,
            "root_rotation_source": "participant+0x1028",
            "root_translation_source": [
                "participant+0xa10", "participant+0xa14", "participant+0xa18"
            ],
            "render_model_owner": "participant+0x1340",
            "consumer_call": "FUN_004a8c20(participant+0x1340, root_affine)",
            "same_participant_receiver_proven": True,
            "root_affine_and_render_model_owner_meet_at_direct_call": True,
            "callgraph_adjacency_used_as_owner_proof": False,
        },
        "claim": {
            "outer_vehicle_translation_to_runtime_render_owner_formula": "P_runtime_owner = P_outer + R_outer * delta_local",
            "outer_vehicle_rotation_to_runtime_render_owner_provenance": "common source R_outer through normalize -> matrix_to_quaternion -> participant root quaternion -> derived participant+0x1028 matrix",
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
    parser.add_argument("bridge", type=Path)
    parser.add_argument("bmw_resource_join", type=Path)
    parser.add_argument("decompiler_source", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze(args.bridge, args.bmw_resource_join, args.decompiler_source)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
