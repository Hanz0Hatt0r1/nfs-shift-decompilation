#!/usr/bin/env python3
"""Prove the participant root affine belongs to the vehicle RenderHierarchy model domain.

This is intentionally narrower than an outer Vehicle -> VHF hierarchy-root proof.
It joins two already-positive contracts with exact retail source/function witnesses:

* the selected BMW Vehicle Render Model is materialized in participant+0x1340;
* the same participant constructs its root world affine from +0x1028/+0xa10..+0xa18;
* FUN_00480700 passes that affine to FUN_004a8c20 with participant+0x1340;
* FUN_004a8c20 applies the affine to local coordinates owned by that model.

The result proves a shared model/root-affine coordinate domain, but deliberately
keeps the exact VHF HIERARCHY Root local frame composition for the next proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.VehicleRenderModelRootAffineDomainJoin/1"
RESOURCE_JOIN_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
AFFINE_BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"

TARGETS: dict[str, tuple[str, int, str, str]] = {
    "0x00483c50": (
        "FUN_00483c50",
        2766,
        "__fastcall",
        "027711efda8a35e59698871f082ec871beba0fef72a5d36860cd474c096ce051",
    ),
    "0x00480700": (
        "FUN_00480700",
        92,
        "__fastcall",
        "f516ada7168e7af185891058c2e3405389a715a4933cc64acb624502f06f9f6d",
    ),
    "0x004a8c20": (
        "FUN_004a8c20",
        198,
        "__fastcall",
        "1bdaa8f843f668bc4bec2d58d23a62c20efd23c737b78795f687a1cf67e72ece",
    ),
}

SOURCE_FACTS: dict[str, tuple[str, ...]] = {
    "FUN_00483c50": (
        "puVar13=*(undefined1**)(*(int*)((int)param_1+0xf0)+0x54);",
        "FUN_006362e0(local_64,puVar13);",
        "FUN_004aecd0((int*)((int)param_1+0x1340),&local_158);",
    ),
    "FUN_00480700": (
        "FUN_0042fc90(local_50,(undefined4*)(param_1+0x1028));",
        "local_20=*(undefined4*)(param_1+0xa10);",
        "local_1c=*(undefined4*)(param_1+0xa14);",
        "local_18=*(undefined4*)(param_1+0xa18);",
        "FUN_004a8c20(param_1+0x1340,local_50);",
    ),
    "FUN_004a8c20": (
        "pfVar2=(float*)(param_1+0x918);",
        "local_30=param_2[8]**pfVar2+pfVar2[-2]**param_2+param_2[4]*pfVar2[-1]+param_2[0xc];",
        "local_2c=param_2[9]**pfVar2+param_2[1]*pfVar2[-2]+param_2[5]*pfVar2[-1]+param_2[0xd];",
        "local_28=param_2[10]**pfVar2+param_2[2]*pfVar2[-2]+param_2[6]*pfVar2[-1]+param_2[0xe];",
        "FUN_00693940(pfVar1,*(int*)(local_14+0x174),uVar3,pfVar4);",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, Mapping), f"{path} is not a JSON object")
    return value


def _compact(text: str) -> str:
    return "".join(text.split())


def _function_rows(functions_path: Path) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    with functions_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            address = str(row.get("address") or "").lower()
            if address in TARGETS:
                _require(address not in rows, f"duplicate function row {address}")
                rows[address] = row
    return rows


def _validate_functions(ghidra_export: Path) -> list[dict[str, Any]]:
    rows = _function_rows(ghidra_export / "functions.jsonl")
    witnesses: list[dict[str, Any]] = []
    for address, (name, size, convention, mnemonic_sha256) in TARGETS.items():
        row = rows.get(address)
        _require(row is not None, f"missing retail function row {address}")
        _require(row.get("name") == name, f"{address} name drift")
        _require(row.get("size") == size, f"{address} size drift")
        _require(row.get("calling_convention") == convention, f"{address} calling convention drift")
        _require(row.get("mnemonic_sha256") == mnemonic_sha256, f"{address} mnemonic fingerprint drift")
        witnesses.append(
            {
                "address": address,
                "name": name,
                "size": size,
                "calling_convention": convention,
                "mnemonic_sha256": mnemonic_sha256,
            }
        )
    return witnesses


def _validate_resource_join(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == RESOURCE_JOIN_FORMAT, f"expected {RESOURCE_JOIN_FORMAT}")
    _require(value.get("ready") is True, "BMW resource join is not positive")
    retail = value.get("retail") or {}
    _require(retail.get("program") == PROGRAM, "resource join program drift")
    _require(retail.get("md5") == PE_MD5, "resource join retail MD5 drift")
    owner = value.get("input_owner_proof") or {}
    _require(owner.get("vehicle_render_hierarchy_owner_ready") is True, "vehicle RenderHierarchy owner is not ready")
    _require(owner.get("vehicle_render_model_property_name") == "Vehicle Render Model", "Vehicle Render Model semantic field drift")
    _require(owner.get("vehicle_render_model_property_field") == "+0x54", "Vehicle Render Model field offset drift")
    selected = value.get("selected_vehicle_descriptor") or {}
    _require(selected.get("vehicle_name") == "BMW_M3_E36", "selected BMW vehicle drift")
    _require(selected.get("property_value") == "BMW_M3_E36.vhf", "selected Vehicle Render Model value drift")
    _require(selected.get("selected_BMW_vehicle_render_model_value_ready") is True, "selected BMW render-model value is not ready")
    resource = value.get("canonical_bmw_vhf_resource") or {}
    _require(resource.get("resolved_path") == CANONICAL_VHF, "canonical BMW VHF path drift")
    _require(resource.get("decoded_sha256") == DECODED_VHF_SHA256, "canonical BMW VHF decoded SHA drift")
    _require(resource.get("canonical_BMW_VHF_resource_join_ready") is True, "canonical BMW VHF resource join is not ready")
    handoff = value.get("handoff") or {}
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "upstream resource join preclaims outer/VHF relation")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "upstream resource join preclaims BODY0 bind proof")
    return {
        "format": RESOURCE_JOIN_FORMAT,
        "vehicle_name": "BMW_M3_E36",
        "vehicle_render_model_property_field": "+0x54",
        "vehicle_render_model_value": "BMW_M3_E36.vhf",
        "canonical_vhf": CANONICAL_VHF,
        "decoded_sha256": DECODED_VHF_SHA256,
    }


def _validate_affine_bridge(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == AFFINE_BRIDGE_FORMAT, f"expected {AFFINE_BRIDGE_FORMAT}")
    _require(value.get("ready") is True, "outer/render affine bridge is not positive")
    retail = value.get("retail") or {}
    _require(retail.get("program") == PROGRAM, "affine bridge program drift")
    _require(retail.get("md5") == PE_MD5, "affine bridge retail MD5 drift")
    _require(retail.get("source_sha256") == SOURCE_SHA256, "affine bridge source SHA drift")
    outer = value.get("outer_transform") or {}
    _require(outer.get("local_delta_has_concrete_setup_producer") is True, "local delta setup producer not proven")
    _require(outer.get("local_delta_is_runtime_pose_source") is False, "local delta misclassified as runtime pose")
    _require(outer.get("render_root_local_delta_offsets") == ["+0x19c", "+0x1a0", "+0x1a4"], "render-root local delta layout drift")
    snapshot = value.get("snapshot_relation") or {}
    _require(snapshot.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "snapshot translation formula drift")
    _require(snapshot.get("independent_rotation_source_present") is False, "unexpected independent snapshot rotation source")
    participant = value.get("render_participant_relation") or {}
    _require(participant.get("vehicle_render_model") == "participant+0x1340", "participant vehicle render-model offset drift")
    _require(participant.get("derived_rotation_matrix") == "participant+0x1028", "participant root rotation offset drift")
    _require(participant.get("root_translation") == ["participant+0xa10", "participant+0xa14", "participant+0xa18"], "participant root translation drift")
    _require(participant.get("world_affine_consumed_by") == "FUN_004a8c20", "participant world-affine consumer drift")
    _require(participant.get("world_affine_translation_slots") == [12, 13, 14], "participant row-affine translation slots drift")
    _require(participant.get("node_local_FUN_004ae150_promoted_to_root_setter") is False, "node-local helper was incorrectly promoted")
    handoff = value.get("handoff") or {}
    _require(handoff.get("outer_vehicle_to_render_root_symbolic_affine_ready") is True, "outer -> render-root symbolic affine is not ready")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "upstream affine bridge preclaims VHF relation")
    _require(handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is False, "upstream affine bridge preclaims fixed VHF delta")
    return {
        "format": AFFINE_BRIDGE_FORMAT,
        "translation_formula": snapshot.get("translation_formula"),
        "local_delta_offsets": list(outer.get("render_root_local_delta_offsets")),
        "participant_render_model": participant.get("vehicle_render_model"),
        "participant_root_rotation": participant.get("derived_rotation_matrix"),
        "participant_root_translation": list(participant.get("root_translation")),
    }


def analyze_vehicle_render_model_root_affine_domain_join(
    ghidra_export: Path,
    source_path: Path,
    resource_join_path: Path,
    affine_bridge_path: Path,
) -> dict[str, Any]:
    source = source_path.read_text(encoding="utf-8", errors="strict")
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    _require(source_sha256 == SOURCE_SHA256, "retail Ghidra C source SHA-256 drift")
    compact = _compact(source)
    for function_name, facts in SOURCE_FACTS.items():
        for fact in facts:
            _require(fact in compact, f"missing {function_name} source witness: {fact}")

    function_witnesses = _validate_functions(ghidra_export)
    resource = _validate_resource_join(_load(resource_join_path))
    affine = _validate_affine_bridge(_load(affine_bridge_path))

    return {
        "format": FORMAT,
        "version": 1,
        "status": "vehicle-render-model-root-affine-domain-proven",
        "ready": True,
        "retail": {"program": PROGRAM, "md5": PE_MD5, "source_sha256": source_sha256},
        "inputs": {"resource_join": resource, "affine_bridge": affine},
        "provenance": {
            "resource_join_contract": RESOURCE_JOIN_FORMAT,
            "affine_bridge_contract": AFFINE_BRIDGE_FORMAT,
            "retail_source_sha256": source_sha256,
            "retail_function_fingerprints_validated": [row["address"] for row in function_witnesses],
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
        "function_witnesses": function_witnesses,
        "participant_domain": {
            "vehicle_render_model_owner": "participant+0x1340",
            "vehicle_render_model_source": "selected descriptor +0x54 / Vehicle Render Model",
            "canonical_bmw_vhf": CANONICAL_VHF,
            "canonical_bmw_vhf_decoded_sha256": DECODED_VHF_SHA256,
            "root_world_rotation_matrix": "participant+0x1028",
            "root_world_translation": ["participant+0xa10", "participant+0xa14", "participant+0xa18"],
            "root_world_affine_layout": "row-major D3D row-vector affine; translation slots 12/13/14",
            "model_local_points": "vehicle render model +0x918, 17 entries x 4 floats",
            "model_local_point_validity": "vehicle render model +0x8f0, 17 byte flags",
            "model_identity_forward": "vehicle render model +0x174 -> FUN_00693940",
        },
        "proof": {
            "descriptor_vehicle_render_model_materialized_at_participant_plus_0x1340": True,
            "participant_root_affine_passed_to_same_render_model_owner": True,
            "render_model_local_points_transformed_by_participant_root_affine": True,
            "row_vector_translation_slots_consumed": [12, 13, 14],
            "vehicle_render_model_root_affine_domain_join_ready": True,
            "semantic_statement": (
                "participant root affine is the local-to-world affine for coordinates owned by "
                "the same materialized Vehicle Render Model domain selected as canonical BMW VHF"
            ),
        },
        "handoff": {
            "vehicle_render_model_root_affine_domain_join_ready": True,
            "canonical_BMW_VHF_resource_join_ready": True,
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "canonical_BMW_VHF_hierarchy_root_frame_required_next": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "consumer": "Process 1 exact BMW VHF HIERARCHY Root composition",
        },
        "limits": {
            "hierarchy_root_matrix_applied_or_composed_here": False,
            "participant_root_affine_equated_to_hierarchy_root_frame": False,
            "identity_vhf_root_matrix_used_as_frame_identity": False,
            "FUN_004ae150_promoted_to_root_setter": False,
            "numeric_outer_to_vhf_matrix_claimed": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("resource_join", type=Path)
    parser.add_argument("affine_bridge", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_vehicle_render_model_root_affine_domain_join(
        args.ghidra_export, args.source, args.resource_join, args.affine_bridge
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
