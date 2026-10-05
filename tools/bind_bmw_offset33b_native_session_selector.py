#!/usr/bin/env python3
"""Bind one source-backed BMW offset33b selector-family member to a native session.

The retail static proof deliberately produces a complete selector family instead
of guessing one live-game configuration.  This adapter is the Process 1 ->
Process 2 handoff for the native playable slice: it validates an explicit native
session policy against that already-proven family and materializes exactly one
numeric BODY0 -> outer-Vehicle bind matrix.

Selecting a native policy is not evidence about which selector the original game
would have used in an arbitrary retail session.  The independent outer-Vehicle
root -> VHF vehicle-root relation also remains unproven here.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
FAMILY_FORMAT = "SHIFT.BMWOffset33bSelectorCompleteNumeric/1"
TARGET_VEHICLE = "BMW_M3_E36"
TARGET_SLICE = "Silverstone+BMW_M3_E36"
VALID_DIFFICULTIES = (0, 1, 2)
VALID_MODES = ("normal", "drift")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected finite scalar")
    return result


def _vec3(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label}: expected three components")
    return [_finite(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _matrix(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("BODY0 matrix must contain four rows")
    rows: list[list[float]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"BODY0 matrix row {row_index} must contain four scalars")
        rows.append([
            _finite(item, f"BODY0 matrix[{row_index}][{column}]")
            for column, item in enumerate(row)
        ])
    expected_linear = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]
    if rows[:3] != expected_linear or rows[3][3] != 1.0:
        raise ValueError("BODY0 matrix is not the proven identity-rotation row-vector affine form")
    return rows


def _validate_family(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if report.get("format") != FAMILY_FORMAT or report.get("ready") is not True:
        raise ValueError(f"selector family must be ready {FAMILY_FORMAT}")
    if report.get("status") != "selector-complete-numeric-family-ready":
        raise ValueError("selector family status drift")

    handoff = report.get("handoff")
    scope = report.get("scope")
    if not isinstance(handoff, Mapping) or not isinstance(scope, Mapping):
        raise ValueError("selector family handoff/scope missing")
    for field in (
        "BMW_numeric_offset33b_selector_family_ready",
        "BODY0_to_outer_vehicle_root_selector_family_ready",
        "BMW_numeric_offset33b_ready_when_race_mode_selector_bound",
        "BODY0_to_outer_vehicle_root_numeric_matrix_ready_when_selector_bound",
    ):
        if handoff.get(field) is not True:
            raise ValueError(f"selector family gate {field} is not ready")
    for field in (
        "BMW_numeric_offset33b_ready",
        "BODY0_to_outer_vehicle_root_numeric_matrix_ready",
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        if handoff.get(field) is not False:
            raise ValueError(f"selector family unexpectedly preclaims {field}")
    if scope.get("single_profile_default_assumed") is not False:
        raise ValueError("selector family unexpectedly assumes one profile default")
    if scope.get("outer_vehicle_to_VHF_identity_assumed") is not False:
        raise ValueError("selector family unexpectedly assumes outer Vehicle/VHF identity")

    rows = report.get("selector_family")
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("selector family must contain exactly six retail-domain rows")
    seen: set[tuple[bool, int]] = set()
    normalized: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"selector_family[{index}] must be an object")
        drift = row.get("use_drift_cgheight_scale")
        difficulty = row.get("player_difficulty")
        if not isinstance(drift, bool):
            raise ValueError(f"selector_family[{index}] drift selector must be boolean")
        if isinstance(difficulty, bool) or difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"selector_family[{index}] difficulty outside retail domain")
        key = (drift, int(difficulty))
        if key in seen:
            raise ValueError(f"duplicate selector-family row {key}")
        seen.add(key)

        translation = _vec3(
            row.get("BODY0_to_outer_vehicle_root_translation"),
            f"selector_family[{index}].translation",
        )
        offset = _vec3(row.get("offset33b"), f"selector_family[{index}].offset33b")
        if any(translation[axis] != -offset[axis] for axis in range(3)):
            raise ValueError(f"selector_family[{index}] translation is not -offset33b")
        matrix = _matrix(row.get("BODY0_to_outer_vehicle_root_row_vector_matrix"))
        if matrix[3][:3] != translation:
            raise ValueError(f"selector_family[{index}] matrix translation disagreement")
        _vec3(row.get("target_CG"), f"selector_family[{index}].target_CG")
        normalized.append(row)

    expected = {(drift, difficulty) for drift in (False, True) for difficulty in VALID_DIFFICULTIES}
    if seen != expected:
        raise ValueError("selector family does not cover the complete retail selector domain")
    return normalized


def bind_native_session_selector(
    family: Mapping[str, Any],
    *,
    physics_mode: str,
    player_difficulty: int,
    session_target: str = TARGET_SLICE,
) -> dict[str, Any]:
    rows = _validate_family(family)
    if physics_mode not in VALID_MODES:
        raise ValueError(f"physics_mode must be one of {', '.join(VALID_MODES)}")
    if isinstance(player_difficulty, bool) or player_difficulty not in VALID_DIFFICULTIES:
        raise ValueError("player_difficulty must be one of 0, 1, 2")
    target = str(session_target).strip()
    if not target:
        raise ValueError("session_target must be non-empty")

    use_drift = physics_mode == "drift"
    matches = [
        row
        for row in rows
        if row.get("use_drift_cgheight_scale") is use_drift
        and row.get("player_difficulty") == player_difficulty
    ]
    if len(matches) != 1:
        raise ValueError("native selector does not resolve to exactly one proven family row")
    selected = dict(matches[0])

    return {
        "format": FORMAT,
        "version": 1,
        "status": "native-session-selector-bound",
        "ready": True,
        "vehicle": TARGET_VEHICLE,
        "session_target": target,
        "selector": {
            "physics_mode": physics_mode,
            "use_drift_cgheight_scale": use_drift,
            "player_difficulty": player_difficulty,
            "source": "explicit-native-vertical-slice-policy",
            "validated_against_retail_selector_domain": True,
            "retail_live_session_selector_inferred": False,
        },
        "selected_numeric": selected,
        "handoff": {
            "native_session_selector_bound": True,
            "BMW_numeric_offset33b_ready": True,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "remaining_blockers": [
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-join-unproven",
                "required_evidence": (
                    "prove the retail/source-backed affine relation from the outer Vehicle root "
                    "to the canonical BMW VHF vehicle-root/assembly frame"
                ),
            }
        ],
        "scope": {
            "native_session_policy_is_retail_session_observation": False,
            "retail_player_difficulty_default_inferred": False,
            "retail_drift_mode_default_inferred": False,
            "selector_family_rederived": False,
            "BODY0_to_outer_vehicle_rotation_identity_reused_from_upstream_proof": True,
            "outer_vehicle_to_VHF_identity_assumed": False,
            "BODY0_bind_frame_proof_invented": False,
            "vehicle_world_transform_claimed": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selector_family", type=Path, help=f"ready {FAMILY_FORMAT} JSON")
    parser.add_argument("--physics-mode", choices=VALID_MODES, required=True)
    parser.add_argument("--player-difficulty", type=int, choices=VALID_DIFFICULTIES, required=True)
    parser.add_argument("--session-target", default=TARGET_SLICE)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = bind_native_session_selector(
        _load(args.selector_family),
        physics_mode=args.physics_mode,
        player_difficulty=args.player_difficulty,
        session_target=args.session_target,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
