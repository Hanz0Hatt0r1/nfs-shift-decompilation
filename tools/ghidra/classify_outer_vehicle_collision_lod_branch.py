#!/usr/bin/env python3
"""Retire FUN_007a3d60 as a VHF/render-root candidate using frozen retail evidence.

This is a deliberately narrow negative classifier.  It does not claim that the
outer Vehicle -> VHF relation is absent.  It proves only that the previously
ranked `_WHEEL_*_LODA` branch is collision/material construction evidence and
therefore must not be promoted to RenderHierarchy/VHF identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.OuterVehicleCollisionLodNegative/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
UPSTREAM_FORMAT = "SHIFT.OuterVehicleChassisOwnerJoin/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

CHASSIS_INIT = "0x007ac4d0"
COLLISION_LOD = "0x007a3d60"
COLLISION_ENTRY_HELPER = "0x00778fb0"
RESOLVER_THUNK = "0x0047bdf0"

FUNCTION_FINGERPRINTS = {
    COLLISION_LOD: "689d88dc93c57813b682d5b8b7147f99032457307d3b2dab1d21adb1c61e8f45",
    COLLISION_ENTRY_HELPER: "b24f9251b9abc6608340ffb0c44c50b9ad71631f62e54de44208f19b276c5305",
    RESOLVER_THUNK: "68de32f85d6daf246c1b8163a07400b82021cdc7a881415976e223547625a126",
}

STRING_WITNESSES = {
    "0x00b0c3c0": ("rubber tyre", "0x007a3f41"),
    "0x00b0c3cc": ("COLLISION_CONVEX_%s_%x", "0x007a3f33"),
    "0x00b0c3e4": ("_WHEEL_RR_LODA", "0x007a3ef4"),
    "0x00b0c3f4": ("_WHEEL_RL_LODA", "0x007a3eea"),
    "0x00b0c404": ("_WHEEL_FR_LODA", "0x007a3ee0"),
    "0x00b0c414": ("_WHEEL_FL_LODA", "0x007a3ed6"),
}

REQUIRED_CALLS = {
    (CHASSIS_INIT, "0x007accc3", COLLISION_LOD),
    (COLLISION_LOD, "0x007a3ffe", COLLISION_ENTRY_HELPER),
    (COLLISION_LOD, "0x007a402a", RESOLVER_THUNK),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _validate_upstream(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != UPSTREAM_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {UPSTREAM_FORMAT}")
    handoff = report.get("handoff") or {}
    if handoff.get("HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain") is not True:
        raise ValueError("upstream car-body/CHASSIS join is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("upstream unexpectedly preclaims VHF-root identity")
    chassis = report.get("chassis_init") or {}
    edges = chassis.get("embedded_owner_edges") or []
    if not any(
        isinstance(row, dict)
        and row.get("offset") == "+0x534"
        and COLLISION_LOD in [str(x).lower() for x in row.get("callees") or []]
        for row in edges
    ):
        raise ValueError("upstream +0x534 -> FUN_007a3d60 edge missing")
    return report


def analyze(database_root: Path, upstream_path: Path) -> dict[str, Any]:
    upstream = _validate_upstream(upstream_path)
    binary = _load_json(database_root / "binary.json")
    if binary.get("format") != DB_FORMAT or binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("retail Ghidra database identity drift")

    wanted = set(FUNCTION_FINGERPRINTS)
    functions: dict[str, dict[str, Any]] = {}
    for row in _jsonl(database_root / "functions.jsonl"):
        address = str(row.get("address") or "").lower()
        if address in wanted:
            functions[address] = row
    if set(functions) != wanted:
        raise ValueError(f"missing function rows: {sorted(wanted - set(functions))}")
    for address, fingerprint in FUNCTION_FINGERPRINTS.items():
        if functions[address].get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
    if functions[COLLISION_LOD].get("calling_convention") != "__thiscall":
        raise ValueError("FUN_007a3d60 calling convention drift")
    if functions[RESOLVER_THUNK].get("thunk") is not True:
        raise ValueError("resolver thunk identity drift")

    seen_strings: dict[str, dict[str, Any]] = {}
    for row in _jsonl(database_root / "strings_xrefs.jsonl"):
        address = str(row.get("address") or "").lower()
        if address in STRING_WITNESSES:
            seen_strings[address] = row
    for address, (value, xref) in STRING_WITNESSES.items():
        row = seen_strings.get(address)
        if row is None or row.get("value") != value:
            raise ValueError(f"{address}: string witness drift")
        if xref not in [str(x).lower() for x in row.get("xrefs") or []]:
            raise ValueError(f"{address}: xref witness drift")
        if COLLISION_LOD not in [str(x).lower() for x in row.get("functions") or []]:
            raise ValueError(f"{address}: function ownership drift")

    seen_calls: set[tuple[str, str, str]] = set()
    for row in _jsonl(database_root / "callgraph.jsonl"):
        edge = (
            str(row.get("from_function") or "").lower(),
            str(row.get("instruction") or "").lower(),
            str(row.get("to") or "").lower(),
        )
        if edge in REQUIRED_CALLS and row.get("indirect") is False:
            seen_calls.add(edge)
    missing_calls = REQUIRED_CALLS - seen_calls
    if missing_calls:
        raise ValueError(f"required call edge drift: {sorted(missing_calls)}")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "collision-lod-vhf-candidate-retired",
        "ready": True,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "subject": {
            "function": COLLISION_LOD,
            "upstream_receiver": "car-body/CHASSIS +0x534 child",
            "previous_candidate_role": "vehicle visual/LOD -> VHF/RenderHierarchy candidate",
            "proven_role_boundary": "collision/material wheel-object construction lane",
        },
        "evidence": {
            "function_fingerprints": FUNCTION_FINGERPRINTS,
            "semantic_strings": [
                {"address": address, "value": value, "xref": xref}
                for address, (value, xref) in STRING_WITNESSES.items()
            ],
            "required_calls": [
                {"from": src, "instruction": ins, "to": dst}
                for src, ins, dst in sorted(REQUIRED_CALLS)
            ],
            "collision_format_string_proven": True,
            "rubber_tyre_material_string_proven": True,
            "four_wheel_lod_names_proven": True,
            "collision_entry_helper_call_proven": True,
            "post_collision_resolver_thunk_call_proven": True,
        },
        "negative_classification": {
            "wheel_lod_name_proximity_is_render_identity": False,
            "FUN_007a3d60_is_admissible_VHF_root_candidate": False,
            "resolver_result_is_promoted_to_VHF_node": False,
            "resolver_thunk_is_promoted_to_RenderHierarchy": False,
            "branch_removed_from_outer_vehicle_to_VHF_search": True,
        },
        "handoff": {
            "collision_wheel_LOD_negative_classification_ready": True,
            "outer_vehicle_visual_hierarchy_collision_branch_retired": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": "SHIFT.VehicleRenderRootPoseTransportFrontier/1",
        },
        "blockers": [
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": "join an independently identified SMS/RenderHierarchy runtime owner/root pose to the canonical BMW VHF assembly/root frame",
            }
        ],
        "scope": {
            "broad_callgraph_expansion_used": False,
            "new_runtime_capture_used": False,
            "original_game_executed": False,
            "collision_semantics_promoted_to_render_semantics": False,
            "VHF_identity_inferred_from_wheel_names": False,
            "absence_of_any_outer_vehicle_to_VHF_path_claimed": False,
            "direct_and_indirect_render_manager_ca4_branches_reopened": False,
            "upstream_chassis_owner_join_revalidated": upstream.get("ready") is True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_root", type=Path)
    parser.add_argument("upstream_chassis_owner_join", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze(args.database_root, args.upstream_chassis_owner_join)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print("collision wheel LOD negative classification: ready")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
