#!/usr/bin/env python3
"""Re-enter the unified renderer bootstrap from a ready Phase 650 capture bundle.

This entry point does not promote Phase 650 stage/type observations into renderer
identity.  It only revalidates that the ready Phase 650 result still describes
the canonical sibling raw capture and snapshot files, then delegates to the
existing bootstrap_native_vertical_slice.py with that capture path/root.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from bootstrap_native_vertical_slice import main as bootstrap_main
from phase642_external_sampler_capture_result import (
    CUBE_FACES,
    FORMAT as CAPTURE_RESULT_FORMAT,
    _cube_face_name,
    _resolve_snapshot_path,
)

FORMAT = "SHIFT.Phase652ExternalSamplerCaptureFeedback/1"
CANONICAL_CAPTURE_NAME = "shift_d3d9_capture.jsonl"


def _load_map(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ready_expectations(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    blockers: list[str] = []
    if result.get("format") != CAPTURE_RESULT_FORMAT:
        blockers.append("capture-result:format-invalid")
    if result.get("version") != 1:
        blockers.append("capture-result:version-invalid")
    if result.get("ready") is not True or result.get("capture_input_class_ready") is not True:
        blockers.append("capture-result:not-ready")

    boundary = result.get("boundary")
    if not isinstance(boundary, Mapping):
        boundary = {}
        blockers.append("capture-result:boundary-missing")
    required_boundary = {
        "stage_and_resource_type_only_preflight": True,
        "binding_identity_claimed": False,
        "draw_identity_claimed": False,
        "scene_identity_claimed": False,
        "resource_identity_claimed": False,
        "scene_set_ready_claimed": False,
        "full_renderer_reattribution_required": True,
    }
    for key, expected in required_boundary.items():
        if boundary.get(key) is not expected:
            blockers.append(f"capture-result:boundary-mismatch:{key}")

    raw_expectations = result.get("expectations")
    if not isinstance(raw_expectations, list) or not raw_expectations:
        blockers.append("capture-result:expectations-missing")
        raw_expectations = []

    ready: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_expectations):
        prefix = f"capture-result:expectation-{index}"
        if not isinstance(raw, Mapping):
            blockers.append(prefix + ":not-object")
            continue
        if raw.get("ready") is not True:
            blockers.append(prefix + ":not-ready")
            continue
        stage = _safe_int(raw.get("stage"))
        required_count = _safe_int(raw.get("required_snapshot_path_count"))
        resource_type = str(raw.get("expected_d3d9_resource_type") or "")
        sampler_type = str(raw.get("sampler_type") or "")
        if stage is None or not 0 <= stage <= 15:
            blockers.append(prefix + ":stage-invalid")
            continue
        expected = {
            "sampler2D": ("texture2d", 1),
            "samplerCube": ("cube_texture", 6),
        }.get(sampler_type)
        if expected is None:
            blockers.append(prefix + ":sampler-type-invalid")
            continue
        if (resource_type, required_count) != expected:
            blockers.append(prefix + ":resource-shape-mismatch")
            continue
        observations = [
            dict(row)
            for row in (raw.get("observations") or [])
            if isinstance(row, Mapping) and row.get("ready") is True
        ]
        if not observations:
            blockers.append(prefix + ":ready-observation-missing")
            continue
        ready.append({
            "index": index,
            "stage": stage,
            "sampler_type": sampler_type,
            "resource_type": resource_type,
            "required_snapshot_path_count": required_count,
            "observations": observations,
        })

    summary = result.get("summary")
    if isinstance(summary, Mapping):
        expected_count = _safe_int(summary.get("expectation_count"))
        ready_count = _safe_int(summary.get("ready_expectation_count"))
        if expected_count is not None and expected_count != len(raw_expectations):
            blockers.append("capture-result:summary-expectation-count-mismatch")
        if ready_count is not None and ready_count != len(ready):
            blockers.append("capture-result:summary-ready-count-mismatch")

    blockers = list(dict.fromkeys(blockers))
    if blockers:
        raise ValueError(";".join(blockers))
    return ready


def _observation_matches_raw(
    observation: Mapping[str, Any],
    raw: Mapping[str, Any],
    expectation: Mapping[str, Any],
    capture_root: Path,
) -> bool:
    if raw.get("event") != "set_texture":
        return False
    event_index = _safe_int(observation.get("event_index"))
    if event_index is None or _safe_int(raw.get("event_index")) != event_index:
        return False
    if _safe_int(raw.get("stage")) != int(expectation["stage"]):
        return False
    if str(raw.get("resource_type_name") or "") != expectation["resource_type"]:
        return False
    if raw.get("texture_ptr") != observation.get("texture_ptr"):
        return False
    if str(raw.get("snapshot_status") or "") != "captured":
        return False

    raw_paths = [
        str(path)
        for path in (raw.get("snapshot_paths") or [])
        if isinstance(path, str) and path
    ]
    observation_paths = [
        str(path)
        for path in (observation.get("snapshot_paths") or [])
        if isinstance(path, str) and path
    ]
    if raw_paths != observation_paths:
        return False
    if len(raw_paths) != int(expectation["required_snapshot_path_count"]):
        return False

    faces: set[str] = set()
    for raw_path in raw_paths:
        resolved, _mode = _resolve_snapshot_path(raw_path, capture_root)
        if resolved is None or not resolved.is_file():
            return False
        if expectation["sampler_type"] == "samplerCube":
            face = _cube_face_name(raw_path)
            if face is None or face in faces:
                return False
            faces.add(face)
    if expectation["sampler_type"] == "samplerCube" and faces != set(CUBE_FACES):
        return False
    return True


def resolve_capture_feedback_input(
    capture_result_path: str | Path,
) -> dict[str, Any]:
    result_path = Path(capture_result_path).expanduser().resolve()
    if not result_path.is_file():
        raise ValueError(f"capture-result:file-not-found:{result_path}")
    result = _load_map(result_path)
    expectations = _ready_expectations(result)

    # Phase 650's Wine wrapper owns this exact bundle layout.  Never search for
    # another JSONL by basename and never trust an old absolute capture_root from
    # a result that may have been copied as a bundle.
    capture_root = result_path.parent.resolve()
    capture_jsonl = capture_root / CANONICAL_CAPTURE_NAME
    if not capture_jsonl.is_file():
        raise ValueError(
            "capture-result:canonical-sibling-capture-missing:"
            + str(capture_jsonl)
        )

    wanted_indices: set[int] = set()
    for expectation in expectations:
        for observation in expectation["observations"]:
            event_index = _safe_int(observation.get("event_index"))
            if event_index is None or event_index < 0:
                raise ValueError(
                    f"capture-result:expectation-{expectation['index']}:event-index-invalid"
                )
            wanted_indices.add(event_index)

    raw_by_index: dict[int, list[dict[str, Any]]] = {}
    invalid_json = 0
    with capture_jsonl.open("r", encoding="utf-8", errors="replace") as stream:
        for raw_line in stream:
            text = raw_line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                invalid_json += 1
                continue
            if not isinstance(row, dict):
                continue
            event_index = _safe_int(row.get("event_index"))
            if event_index in wanted_indices:
                raw_by_index.setdefault(event_index, []).append(row)
    if invalid_json:
        raise ValueError(f"capture-result:raw-capture-invalid-json:{invalid_json}")

    verified = 0
    for expectation in expectations:
        matched = False
        for observation in expectation["observations"]:
            event_index = _safe_int(observation.get("event_index"))
            rows = raw_by_index.get(event_index if event_index is not None else -1, [])
            if len(rows) > 1:
                raise ValueError(
                    f"capture-result:raw-event-index-ambiguous:{event_index}"
                )
            if rows and _observation_matches_raw(
                observation,
                rows[0],
                expectation,
                capture_root,
            ):
                matched = True
                break
        if not matched:
            raise ValueError(
                "capture-result:ready-observation-no-longer-matches-raw:"
                f"s{expectation['stage']}:{expectation['resource_type']}"
            )
        verified += 1

    return {
        "format": FORMAT,
        "version": 1,
        "ready": verified == len(expectations) and verified > 0,
        "capture_result": str(result_path),
        "capture_jsonl": str(capture_jsonl),
        "capture_root": str(capture_root),
        "verified_expectation_count": verified,
        "boundary": {
            "canonical_sibling_capture_required": True,
            "stored_capture_root_is_selection_authority": False,
            "basename_search_allowed": False,
            "phase650_observation_integrity_revalidated": True,
            "binding_identity_claimed": False,
            "draw_identity_claimed": False,
            "scene_identity_claimed": False,
            "full_renderer_reattribution_required": True,
        },
    }


def _has_option(argv: list[str], name: str) -> bool:
    return any(value == name or value.startswith(name + "=") for value in argv)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_result")
    parser.add_argument(
        "bootstrap_args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to bootstrap_native_vertical_slice.py",
    )
    args = parser.parse_args(argv)

    forwarded = list(args.bootstrap_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        parser.error("bootstrap arguments are required")
    for forbidden in ("--renderer-capture-jsonl", "--renderer-capture-root"):
        if _has_option(forwarded, forbidden):
            parser.error(
                f"{forbidden} is derived from the verified Phase 650 bundle and cannot be overridden"
            )

    feedback = resolve_capture_feedback_input(args.capture_result)
    forwarded.extend([
        "--renderer-capture-jsonl",
        feedback["capture_jsonl"],
        "--renderer-capture-root",
        feedback["capture_root"],
    ])
    return int(bootstrap_main(forwarded))


if __name__ == "__main__":
    raise SystemExit(main())
