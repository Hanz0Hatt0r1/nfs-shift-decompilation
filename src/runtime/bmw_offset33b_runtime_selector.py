#!/usr/bin/env python3
"""Bind a source-backed BMW race-mode selector to one proven BODY0->outer matrix.

Consumes SHIFT.BMWOffset33bSelectorCompleteNumeric/1 from Process 1.  This module
never recomputes retail physics algebra; it only selects one already-proven row
from the exact selector family and emits a compact Process 2 runtime contract.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWOffset33bRuntimeSelectorBinding/1"
PROOF_FORMAT = "SHIFT.BMWOffset33bSelectorCompleteNumeric/1"


class SelectorBindingError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SelectorBindingError(f"selector-family proof not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SelectorBindingError(f"selector-family proof is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SelectorBindingError("selector-family proof must be a JSON object")
    return value


def _finite_vec(values: Any, size: int, field: str) -> list[float]:
    if not isinstance(values, list) or len(values) != size:
        raise SelectorBindingError(f"{field} must contain {size} values")
    result: list[float] = []
    for value in values:
        if isinstance(value, bool):
            raise SelectorBindingError(f"{field} contains a boolean")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise SelectorBindingError(f"{field} contains a non-number") from exc
        if not math.isfinite(number):
            raise SelectorBindingError(f"{field} contains a non-finite number")
        result.append(number)
    return result


def _validate_matrix(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 4:
        raise SelectorBindingError("selected matrix must have four rows")
    matrix = [_finite_vec(row, 4, "selected matrix row") for row in value]
    expected_basis = (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
    )
    for index, expected in enumerate(expected_basis):
        if tuple(matrix[index]) != expected:
            raise SelectorBindingError("BODY0->outer matrix basis drifted from proven identity rotation")
    if matrix[3][3] != 1.0:
        raise SelectorBindingError("BODY0->outer matrix affine w component must be 1")
    return matrix


def bind_selector_family(
    proof: Mapping[str, Any],
    *,
    player_difficulty: int,
    use_drift_cgheight_scale: bool,
) -> dict[str, Any]:
    if proof.get("format") != PROOF_FORMAT or proof.get("ready") is not True:
        raise SelectorBindingError(f"proof must be ready {PROOF_FORMAT}")
    if isinstance(player_difficulty, bool) or player_difficulty not in (0, 1, 2):
        raise SelectorBindingError("player_difficulty must be one of 0, 1, 2")
    if not isinstance(use_drift_cgheight_scale, bool):
        raise SelectorBindingError("use_drift_cgheight_scale must be boolean")

    handoff = proof.get("handoff")
    scope = proof.get("scope")
    family = proof.get("selector_family")
    if not isinstance(handoff, Mapping) or not isinstance(scope, Mapping):
        raise SelectorBindingError("selector-family handoff/scope missing")
    if handoff.get("BMW_numeric_offset33b_selector_family_ready") is not True:
        raise SelectorBindingError("numeric offset33b selector family is not ready")
    if handoff.get("BODY0_to_outer_vehicle_root_selector_family_ready") is not True:
        raise SelectorBindingError("BODY0->outer Vehicle selector family is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise SelectorBindingError("upstream proof unexpectedly preclaims outer Vehicle->VHF join")
    if scope.get("player_difficulty_index_3_admitted") is not False:
        raise SelectorBindingError("upstream proof unexpectedly admits difficulty index 3")
    if not isinstance(family, list) or len(family) != 6:
        raise SelectorBindingError("selector family must contain exactly six admitted rows")

    matches = []
    keys: set[tuple[bool, int]] = set()
    for index, row in enumerate(family):
        if not isinstance(row, Mapping):
            raise SelectorBindingError(f"selector_family[{index}] must be an object")
        drift = row.get("use_drift_cgheight_scale")
        difficulty = row.get("player_difficulty")
        if not isinstance(drift, bool) or isinstance(difficulty, bool) or difficulty not in (0, 1, 2):
            raise SelectorBindingError(f"selector_family[{index}] has invalid selector identity")
        key = (drift, difficulty)
        if key in keys:
            raise SelectorBindingError(f"duplicate selector row: {key}")
        keys.add(key)
        matrix = _validate_matrix(row.get("BODY0_to_outer_vehicle_root_row_vector_matrix"))
        translation = _finite_vec(
            row.get("BODY0_to_outer_vehicle_root_translation"),
            3,
            "BODY0_to_outer_vehicle_root_translation",
        )
        if matrix[3][:3] != translation:
            raise SelectorBindingError(f"selector_family[{index}] matrix/translation mismatch")
        if key == (use_drift_cgheight_scale, player_difficulty):
            matches.append((row, matrix, translation))

    expected_keys = {(drift, difficulty) for drift in (False, True) for difficulty in (0, 1, 2)}
    if keys != expected_keys:
        raise SelectorBindingError("selector family does not cover the exact admitted domain")
    if len(matches) != 1:
        raise SelectorBindingError("requested selector does not resolve to exactly one matrix")

    row, matrix, translation = matches[0]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "race-mode-selector-bound",
        "ready": True,
        "selector": {
            "player_difficulty": player_difficulty,
            "use_drift_cgheight_scale": use_drift_cgheight_scale,
            "cgheight_scale": float(row["cgheight_scale"]),
        },
        "BODY0_to_outer_vehicle_root_translation": translation,
        "BODY0_to_outer_vehicle_root_row_vector_matrix": matrix,
        "handoff": {
            "race_mode_selector_bound_to_native_bootstrap": True,
            "BMW_numeric_offset33b_ready_for_bound_session": True,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready_for_bound_session": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "retail_offset33b_algebra_recomputed_by_process2": False,
            "selector_default_assumed": False,
            "difficulty_index_3_admitted": False,
            "outer_vehicle_to_VHF_identity_assumed": False,
            "vehicle_world_transform_ready": False,
        },
    }


def bind_selector_file(
    proof_path: str | Path,
    *,
    player_difficulty: int,
    use_drift_cgheight_scale: bool,
) -> dict[str, Any]:
    return bind_selector_family(
        _load_json(Path(proof_path)),
        player_difficulty=player_difficulty,
        use_drift_cgheight_scale=use_drift_cgheight_scale,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selector_family", type=Path)
    parser.add_argument("--player-difficulty", required=True, type=int, choices=(0, 1, 2))
    branch = parser.add_mutually_exclusive_group(required=True)
    branch.add_argument("--normal", action="store_true")
    branch.add_argument("--drift", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = bind_selector_file(
            args.selector_family,
            player_difficulty=args.player_difficulty,
            use_drift_cgheight_scale=args.drift,
        )
    except (OSError, SelectorBindingError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
