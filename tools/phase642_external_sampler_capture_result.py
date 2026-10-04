#!/usr/bin/env python3
"""Verify that an exact Phase 641 sampler capture produced usable snapshot inputs.

This is deliberately weaker than renderer attribution.  It consumes the exact
``SHIFT.Phase641ExternalSamplerCapturePlan/1`` frontier, scans the resulting raw
D3D9 JSONL, and proves only that every requested D3D9 sampler stage/resource
class has at least one captured snapshot event whose referenced PPM files still
exist.  It never promotes a stage-level observation into binding, draw, scene,
material, or resource identity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from phase641_external_sampler_capture_plan import (
    FORMAT as PLAN_FORMAT,
    build_capture_plan,
)

FORMAT = "SHIFT.Phase642ExternalSamplerCaptureResult/1"
CUBE_FACES = ("px", "nx", "py", "ny", "pz", "nz")


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _cube_face_name(raw_path: str) -> str | None:
    stem = PureWindowsPath(raw_path).stem.lower()
    for face in CUBE_FACES:
        if stem.endswith("_face_" + face):
            return face
    return None


def _resolve_snapshot_path(
    raw_path: str,
    capture_root: Path,
) -> tuple[Path | None, str]:
    """Resolve one producer snapshot without basename search.

    The Wine capture launcher owns one portable layout:

    ``<capture_root>/shift_d3d9_capture.jsonl``
    ``<capture_root>/textures/*.ppm``

    Existing absolute files are accepted as-is. Relative paths are resolved
    below the supplied capture root with traversal rejection. A Windows/POSIX
    absolute path may be relocated only when its immediate source parent is
    exactly ``textures``; this mirrors the established Phase 590 relocation
    contract and never recursively searches by basename.
    """
    root = capture_root.resolve()
    direct = Path(raw_path)
    if direct.is_absolute() and direct.is_file():
        return direct.resolve(), "absolute-existing"

    windows_path = PureWindowsPath(raw_path)
    windows_absolute = windows_path.is_absolute()
    normalized = raw_path.replace("\\", "/")
    normalized_path = Path(normalized)
    posix_absolute = normalized_path.is_absolute()

    if not windows_absolute and not posix_absolute:
        joined = (root / normalized_path).resolve()
        try:
            joined.relative_to(root)
        except ValueError:
            return None, "path-escapes-capture-root"
        if joined.is_file():
            return joined, "capture-root-relative"
        return None, "relative-path-not-found"

    source_name = windows_path.name if windows_absolute else normalized_path.name
    source_parent = (
        windows_path.parent.name if windows_absolute else normalized_path.parent.name
    )
    if not source_name:
        return None, "snapshot-name-missing"
    if str(source_parent).casefold() != "textures":
        return None, "no-exact-launcher-relocation"

    relocated = (root / "textures" / source_name).resolve()
    try:
        relocated.relative_to(root)
    except ValueError:
        return None, "path-escapes-capture-root"
    if relocated.is_file():
        return relocated, "capture-launcher-textures-relative"
    return None, "launcher-layout-path-not-found"


def _expectations(plan: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    if plan.get("format") != PLAN_FORMAT:
        return [], ["phase642-capture-result:plan-invalid-format"]
    if plan.get("version") != 1:
        blockers.append("phase642-capture-result:plan-version-invalid")
    if plan.get("ready") is not True:
        blockers.append("phase642-capture-result:plan-not-ready")

    rows = plan.get("requirements")
    if not isinstance(rows, list):
        blockers.append("phase642-capture-result:plan-requirements-not-list")
        rows = []

    grouped: dict[tuple[int, str, int, str], dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        prefix = f"phase642-capture-result:requirement-{index}"
        if not isinstance(raw, Mapping):
            blockers.append(prefix + ":not-object")
            continue
        stage = _safe_int(raw.get("requested_texture_stage"))
        resource_type = str(raw.get("expected_d3d9_resource_type") or "")
        path_count = _safe_int(raw.get("required_snapshot_path_count"))
        sampler_type = str(raw.get("sampler_type") or "")
        if stage is None or not 0 <= stage <= 15:
            blockers.append(prefix + ":stage-invalid")
            continue
        if sampler_type == "sampler2D":
            expected_resource_type, expected_count = "texture2d", 1
        elif sampler_type == "samplerCube":
            expected_resource_type, expected_count = "cube_texture", 6
        else:
            blockers.append(prefix + ":sampler-type-invalid")
            continue
        if resource_type != expected_resource_type:
            blockers.append(prefix + ":resource-type-mismatch")
            continue
        if path_count != expected_count:
            blockers.append(prefix + ":snapshot-path-count-mismatch")
            continue

        key = (stage, resource_type, expected_count, sampler_type)
        bucket = grouped.setdefault(key, {
            "stage": stage,
            "sampler_type": sampler_type,
            "expected_d3d9_resource_type": resource_type,
            "required_snapshot_path_count": expected_count,
            "binding_indices": [],
        })
        binding_index = _safe_int(raw.get("binding_index"))
        if binding_index is not None:
            bucket["binding_indices"].append(binding_index)

    expectations = list(grouped.values())
    for row in expectations:
        row["binding_indices"] = sorted(set(row["binding_indices"]))
    expectations.sort(key=lambda row: (
        int(row["stage"]),
        str(row["expected_d3d9_resource_type"]),
        str(row["sampler_type"]),
    ))
    if plan.get("ready") is True and not expectations:
        blockers.append("phase642-capture-result:ready-plan-has-no-expectations")
    return expectations, list(dict.fromkeys(blockers))


def audit_capture_result_lines(
    plan: Mapping[str, Any],
    lines: Iterable[str],
    *,
    capture_root: str | Path,
) -> dict[str, Any]:
    expectations, blockers = _expectations(plan)
    root = Path(capture_root)

    wanted_by_stage: dict[int, list[dict[str, Any]]] = {}
    for expectation in expectations:
        wanted_by_stage.setdefault(int(expectation["stage"]), []).append(expectation)

    candidates: dict[tuple[int, str, int, str], list[dict[str, Any]]] = {}
    for expectation in expectations:
        key = (
            int(expectation["stage"]),
            str(expectation["expected_d3d9_resource_type"]),
            int(expectation["required_snapshot_path_count"]),
            str(expectation["sampler_type"]),
        )
        candidates[key] = []

    nonempty_line_count = 0
    valid_object_count = 0
    invalid_json_count = 0
    non_object_count = 0
    set_texture_count = 0
    requested_stage_set_texture_count = 0

    for raw_line in lines:
        text = raw_line.strip()
        if not text:
            continue
        nonempty_line_count += 1
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            invalid_json_count += 1
            continue
        if not isinstance(value, dict):
            non_object_count += 1
            continue
        valid_object_count += 1
        if value.get("event") != "set_texture":
            continue
        set_texture_count += 1
        stage = _safe_int(value.get("stage"))
        if stage is None or stage not in wanted_by_stage:
            continue
        requested_stage_set_texture_count += 1

        resource_type = str(value.get("resource_type_name") or "")
        snapshot_status = str(value.get("snapshot_status") or "")
        raw_paths = [
            str(path)
            for path in (value.get("snapshot_paths") or [])
            if isinstance(path, str) and path
        ]

        for expectation in wanted_by_stage[stage]:
            expected_type = str(expectation["expected_d3d9_resource_type"])
            required_count = int(expectation["required_snapshot_path_count"])
            sampler_type = str(expectation["sampler_type"])
            if resource_type != expected_type:
                continue

            row_blockers: list[str] = []
            if snapshot_status != "captured":
                row_blockers.append("snapshot-status-not-captured")
            if len(raw_paths) != required_count:
                row_blockers.append(
                    f"snapshot-path-count:{len(raw_paths)}!={required_count}"
                )

            resolved_paths: list[str] = []
            resolution_modes: list[str] = []
            face_names: list[str] = []
            seen_faces: set[str] = set()
            for raw_path in raw_paths:
                resolved, mode = _resolve_snapshot_path(raw_path, root)
                resolution_modes.append(mode)
                if resolved is None:
                    row_blockers.append("snapshot-path-unresolved:" + mode)
                else:
                    resolved_paths.append(str(resolved))

                if sampler_type == "samplerCube":
                    face = _cube_face_name(raw_path)
                    if face is None:
                        row_blockers.append("cube-face-name-unrecognized")
                    elif face in seen_faces:
                        row_blockers.append("cube-face-duplicate:" + face)
                    else:
                        seen_faces.add(face)
                        face_names.append(face)

            if sampler_type == "samplerCube" and set(face_names) != set(CUBE_FACES):
                missing = [face for face in CUBE_FACES if face not in seen_faces]
                if missing:
                    row_blockers.append("cube-faces-missing:" + ",".join(missing))

            key = (stage, expected_type, required_count, sampler_type)
            candidates[key].append({
                "event_index": value.get("event_index"),
                "frame": value.get("frame"),
                "texture_ptr": value.get("texture_ptr"),
                "stage": stage,
                "resource_type_name": resource_type,
                "snapshot_status": snapshot_status,
                "snapshot_paths": raw_paths,
                "resolved_snapshot_paths": resolved_paths,
                "snapshot_path_resolution_modes": resolution_modes,
                "cube_faces": sorted(face_names),
                "ready": not row_blockers,
                "blocking_reasons": list(dict.fromkeys(row_blockers)),
            })

    if invalid_json_count:
        blockers.append(
            f"phase642-capture-result:invalid-json-lines:{invalid_json_count}"
        )
    if non_object_count:
        blockers.append(
            f"phase642-capture-result:non-object-lines:{non_object_count}"
        )

    expectation_reports: list[dict[str, Any]] = []
    ready_keys: set[tuple[int, str, int, str]] = set()
    for expectation in expectations:
        key = (
            int(expectation["stage"]),
            str(expectation["expected_d3d9_resource_type"]),
            int(expectation["required_snapshot_path_count"]),
            str(expectation["sampler_type"]),
        )
        observed = candidates.get(key, [])
        ready_rows = [row for row in observed if row.get("ready") is True]
        expectation_ready = bool(ready_rows)
        if expectation_ready:
            ready_keys.add(key)
        else:
            blockers.append(
                "phase642-capture-result:requested-input-not-observed:"
                f"s{key[0]}:{key[1]}:{key[3]}"
            )
        expectation_reports.append({
            **expectation,
            "ready": expectation_ready,
            "candidate_event_count": len(observed),
            "ready_event_count": len(ready_rows),
            "observations": observed,
        })

    requirement_reports: list[dict[str, Any]] = []
    for raw in plan.get("requirements") or []:
        if not isinstance(raw, Mapping):
            continue
        stage = _safe_int(raw.get("requested_texture_stage"))
        required_count = _safe_int(raw.get("required_snapshot_path_count"))
        resource_type = str(raw.get("expected_d3d9_resource_type") or "")
        sampler_type = str(raw.get("sampler_type") or "")
        key = (
            stage if stage is not None else -1,
            resource_type,
            required_count if required_count is not None else -1,
            sampler_type,
        )
        requirement_reports.append({
            "binding_index": raw.get("binding_index"),
            "requested_texture_stage": stage,
            "sampler": raw.get("sampler"),
            "sampler_type": sampler_type,
            "expected_d3d9_resource_type": resource_type,
            "required_snapshot_path_count": required_count,
            "capture_input_class_ready": key in ready_keys,
            "binding_identity_revalidated": False,
        })

    blockers = list(dict.fromkeys(blockers))
    ready = bool(expectations) and not blockers and len(ready_keys) == len(expectations)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "capture_input_class_ready": ready,
        "blocking_reasons": blockers,
        "source": {
            "capture_plan_format": plan.get("format"),
            "capture_plan_requirement_count": plan.get("requirement_count"),
            "capture_root": str(root),
        },
        "summary": {
            "nonempty_line_count": nonempty_line_count,
            "valid_object_count": valid_object_count,
            "invalid_json_count": invalid_json_count,
            "non_object_count": non_object_count,
            "set_texture_event_count": set_texture_count,
            "requested_stage_set_texture_event_count": (
                requested_stage_set_texture_count
            ),
            "expectation_count": len(expectations),
            "ready_expectation_count": len(ready_keys),
            "requirement_count": len(requirement_reports),
        },
        "expectations": expectation_reports,
        "requirements": requirement_reports,
        "boundary": {
            "phase641_capture_plan_authoritative": True,
            "stage_and_resource_type_only_preflight": True,
            "snapshot_status_captured_required": True,
            "exact_snapshot_path_count_required": True,
            "snapshot_files_must_exist": True,
            "snapshot_basename_search_allowed": False,
            "cube_face_set_required": list(CUBE_FACES),
            "binding_identity_claimed": False,
            "draw_identity_claimed": False,
            "scene_identity_claimed": False,
            "resource_identity_claimed": False,
            "scene_set_ready_claimed": False,
            "full_renderer_reattribution_required": True,
        },
    }


def build_capture_result(
    handoff: Mapping[str, Any],
    lines: Iterable[str],
    *,
    capture_root: str | Path,
) -> dict[str, Any]:
    return audit_capture_result_lines(
        build_capture_plan(handoff),
        lines,
        capture_root=capture_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", help="Phase 641 renderer native-scene handoff")
    parser.add_argument("capture_jsonl", help="new raw D3D9 capture JSONL")
    parser.add_argument(
        "--capture-root",
        help=(
            "launcher output root containing textures/; defaults to the capture "
            "JSONL parent"
        ),
    )
    parser.add_argument("--output", help="optional JSON report path")
    args = parser.parse_args(argv)

    capture_path = Path(args.capture_jsonl)
    root = Path(args.capture_root) if args.capture_root else capture_path.parent
    with capture_path.open("r", encoding="utf-8", errors="replace") as stream:
        report = build_capture_result(
            _load(args.handoff),
            stream,
            capture_root=root,
        )

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "expectation_count": report["summary"]["expectation_count"],
        "ready_expectation_count": report["summary"]["ready_expectation_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
