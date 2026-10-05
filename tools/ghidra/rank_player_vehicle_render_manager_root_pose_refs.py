#!/usr/bin/env python3
"""Rank render-manager global xrefs against the real SMS root-pose/render lane.

The earlier global-xref ranker treated FUN_007a3d60 as a positive
"vehicle-visual/LOD" anchor.  Decompiler inspection now shows that function is
wheel collision-convex setup, so lexical _WHEEL_*_LODA proximity must not pull a
candidate toward RenderHierarchy/VHF identity.

This wrapper preserves the existing exact-xref/callgraph machinery, replaces the
positive vehicle/render anchor set with the independently frozen SMS root-pose
transport frontier, and records proximity to FUN_007a3d60 separately as a
negative/discovery-only signal.  No pointer identity or VHF frame gate is opened.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import build_vehicle_render_root_pose_transport_frontier as _pose
import rank_player_vehicle_render_manager_global_refs as _base

FORMAT = "SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1"
PROGRAM = _base.PROGRAM
PE_MD5 = _base.PE_MD5
DEFAULT_GLOBAL = _base.DEFAULT_GLOBAL
DEFAULT_LIMIT = _base.DEFAULT_LIMIT
DEFAULT_MAX_DEPTH = _base.DEFAULT_MAX_DEPTH

COLLISION_WHEEL_ANCHOR = {
    "address": "0x007a3d60",
    "mnemonic_sha256": "689d88dc93c57813b682d5b8b7147f99032457307d3b2dab1d21adb1c61e8f45",
    "domain": "wheel-collision-convex-setup",
    "positive_render_signal": False,
}

POSITIVE_ANCHORS: dict[str, dict[str, Any]] = {
    "render_manager_constructor": dict(_base.ANCHORS["render_manager_constructor"]),
    "car_body_CHASSIS_init": dict(_base.ANCHORS["car_body_CHASSIS_init"]),
    "sms_participant_render_tick": {
        "address": "0x004848bc",
        "mnemonic_sha256": _pose.TARGETS["0x004848bc"]["mnemonic_sha256"],
        "domain": "SMS-participant-render-tick",
    },
    "sms_vehicle_hierarchy_node_update_lane": {
        "address": "0x004ae150",
        "mnemonic_sha256": _pose.TARGETS["0x004ae150"]["mnemonic_sha256"],
        "domain": "vehicle-RenderHierarchy-node-local-update",
    },
    "sms_vehicle_world_affine_consumer": {
        "address": "0x00480700",
        "mnemonic_sha256": _pose.TARGETS["0x00480700"]["mnemonic_sha256"],
        "domain": "SMS-vehicle-world-affine-consumer",
    },
    "sms_vehicle_render_model_world_point_consumer": {
        "address": "0x004a8c20",
        "mnemonic_sha256": _pose.TARGETS["0x004a8c20"]["mnemonic_sha256"],
        "domain": "vehicle-render-model-world-point-consumer",
    },
}
POSITIVE_VEHICLE_ANCHOR_NAMES = tuple(
    name for name in POSITIVE_ANCHORS if name != "render_manager_constructor"
)


def _validate_collision_anchor(functions: dict[str, dict[str, Any]]) -> None:
    address = COLLISION_WHEEL_ANCHOR["address"]
    row = functions.get(address)
    if row is None:
        raise ValueError(f"missing collision negative-control anchor {address}")
    if row.get("mnemonic_sha256") != COLLISION_WHEEL_ANCHOR["mnemonic_sha256"]:
        raise ValueError(f"collision negative-control mnemonic drift: {address}")
    if row.get("external") is True or row.get("thunk") is True:
        raise ValueError(f"collision negative-control is not a concrete retail function: {address}")


def rank(
    ghidra_export: Path,
    global_export: Path,
    *,
    expected_global: str = DEFAULT_GLOBAL,
    limit: int = DEFAULT_LIMIT,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> dict[str, Any]:
    original_anchors = _base.ANCHORS
    original_vehicle_names = _base.VEHICLE_ANCHOR_NAMES
    try:
        _base.ANCHORS = POSITIVE_ANCHORS
        _base.VEHICLE_ANCHOR_NAMES = POSITIVE_VEHICLE_ANCHOR_NAMES
        report = _base.rank(
            ghidra_export,
            global_export,
            expected_global=expected_global,
            limit=limit,
            max_depth=max_depth,
        )
        functions, forward, reverse = _base._load_database(ghidra_export)
    finally:
        _base.ANCHORS = original_anchors
        _base.VEHICLE_ANCHOR_NAMES = original_vehicle_names

    _validate_collision_anchor(functions)
    collision = COLLISION_WHEEL_ANCHOR["address"]
    for row in report["ranking"]["functions"]:
        function = str(row["function"])
        forward_distance = _base._distance(forward, function, collision, max_depth)
        reverse_distance = _base._distance(reverse, function, collision, max_depth)
        values = [value for value in (forward_distance, reverse_distance) if value is not None]
        row["collision_wheel_anchor_distance"] = min(values) if values else None
        row["collision_wheel_anchor_forward_distance"] = forward_distance
        row["collision_wheel_anchor_reverse_distance"] = reverse_distance
        row["collision_proximity_used_as_positive_render_signal"] = False

    report["format"] = FORMAT
    report["status"] = "root-pose-ranked-global-xref-worklist-ready"
    report["anchors"] = {
        name: {
            "address": data["address"],
            "domain": data["domain"],
            "identity": "source/static-anchor",
            "positive_render_signal": True,
        }
        for name, data in POSITIVE_ANCHORS.items()
    }
    report["negative_control_anchor"] = {
        **COLLISION_WHEEL_ANCHOR,
        "classification_basis": "decompiler collision-convex/material construction; instruction-level negative classification pending",
        "used_for_ranking_score": False,
    }
    report["blockers"] = [
        {
            "id": "candidate-render-manager-global-instance-identity-unproven",
            "required_evidence": "inspect ranked global-reference functions; callgraph distance remains discovery evidence only",
        },
        {
            "id": "player-vehicle-renderables-field-runtime-access-unproven",
            "required_evidence": "targeted instruction export must prove a concrete render-manager +0xca4 runtime access",
        },
        {
            "id": "render-manager-owner-to-SMS-root-pose-owner-join-unproven",
            "required_evidence": (
                "join one selected render-manager user to FUN_004848bc/FUN_00480700/FUN_004a8c20 "
                "by physical pointer/value flow, then identify the external RenderHierarchy owner"
            ),
        },
    ]
    report["handoff"].update(
        {
            "root_pose_positive_anchor_ranking_ready": True,
            "collision_wheel_LOD_anchor_removed_from_positive_render_score": True,
            "collision_wheel_LOD_negative_classification_instruction_proof_ready": False,
            "render_manager_owner_to_SMS_root_pose_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        }
    )
    report["scope"].update(
        {
            "wheel_collision_LOD_proximity_promoted_to_render_identity": False,
            "SMS_root_pose_callgraph_proximity_promoted_to_pointer_identity": False,
            "VHF_frame_identity_claimed": False,
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("global_reference_export", type=Path)
    parser.add_argument("--global-address", default=DEFAULT_GLOBAL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = rank(
        args.ghidra_export,
        args.global_reference_export,
        expected_global=args.global_address,
        limit=args.limit,
        max_depth=args.max_depth,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
