"""Index and pair provider runtime capture files by provider/hit/frame.

Phase 499 turns the raw Phase 463 provider_pre/provider_post files plus the
Phase 485 scalar-reset JSONL stream into deterministic capture bundles. It does
not infer new solver semantics; it only verifies pairing and cross-file
provenance.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from specialized_provider_capture_session_runtime import (
    build_provider_session_contract,
)
from specialized_provider_reset_solve_order_runtime import (
    compare_provider_pre_post_order,
)
from specialized_provider_scalar_reset_sequence_runtime import (
    build_event_sequence_contract,
)

FORMAT = "SHIFT.SpecializedProviderCaptureBundleRuntime/1"

SNAPSHOT_RE = re.compile(
    r"^provider_(pre|post)_(0|1)_(\d{6})\.json$"
)


def parse_snapshot_filename(name: str) -> dict[str, Any] | None:
    match = SNAPSHOT_RE.match(Path(name).name)
    if match is None:
        return None

    return {
        "stage": (
            "pre-solve-provider"
            if match.group(1) == "pre"
            else "post-solve-provider"
        ),
        "provider_id": int(match.group(2)),
        "hit": int(match.group(3)),
        "filename": Path(name).name,
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_number}: expected JSON object"
            )
        events.append(value)
    return events


def index_provider_snapshot_directory(
    directory: str | Path,
) -> dict[str, Any]:
    root = Path(directory)
    if not root.exists():
        raise ValueError(f"capture directory does not exist: {root}")

    files: list[dict[str, Any]] = []
    ignored: list[str] = []
    for path in sorted(root.glob("provider_*.json")):
        parsed = parse_snapshot_filename(path.name)
        if parsed is None:
            ignored.append(path.name)
            continue
        parsed["path"] = str(path)
        files.append(parsed)

    groups: dict[tuple[int, int], dict[str, Any]] = {}
    errors: list[str] = []
    for item in files:
        key = (int(item["provider_id"]), int(item["hit"]))
        stage = str(item["stage"])
        group = groups.setdefault(
            key,
            {
                "provider_id": key[0],
                "hit": key[1],
                "pre": None,
                "post": None,
                "files": [],
            },
        )
        if stage == "pre-solve-provider":
            if group["pre"] is not None:
                errors.append(
                    f"duplicate-pre:{key[0]}:{key[1]}"
                )
            else:
                group["pre"] = item
        else:
            if group["post"] is not None:
                errors.append(
                    f"duplicate-post:{key[0]}:{key[1]}"
                )
            else:
                group["post"] = item
        group["files"].append(item)

    bundles = [
        group
        for _, group in sorted(groups.items())
    ]
    for bundle in bundles:
        if bundle["pre"] is None:
            errors.append(
                f"missing-pre:{bundle['provider_id']}:{bundle['hit']}"
            )

    return {
        "format": FORMAT,
        "version": 1,
        "directory": str(root),
        "file_count": len(files),
        "ignored_file_count": len(ignored),
        "ignored_files": ignored,
        "bundle_count": len(bundles),
        "bundles": bundles,
        "errors": list(dict.fromkeys(errors)),
        "ready": not errors,
    }


def _frame_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        frame = event.get("frame_index")
        if frame is None:
            continue
        grouped[int(frame)].append(event)
    return grouped


def analyze_capture_bundle(
    bundle: Mapping[str, Any],
    *,
    reset_events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    provider_id = int(bundle["provider_id"])
    errors: list[str] = []

    pre_info = bundle.get("pre")
    post_info = bundle.get("post")
    if pre_info is None:
        return {
            "provider_id": provider_id,
            "hit": int(bundle["hit"]),
            "ready": False,
            "status": "blocked",
            "errors": ["missing-pre"],
        }

    pre = _load_json(Path(pre_info["path"]))
    post = (
        None
        if post_info is None
        else _load_json(Path(post_info["path"]))
    )

    report = build_provider_session_contract(
        pre,
        post_solve=post,
    )
    errors.extend(report.get("errors") or [])

    frame_index = pre.get("frame_index")
    if frame_index is None:
        errors.append("pre-frame-index-missing")
        frame_index_value = None
    else:
        frame_index_value = int(frame_index)

    event_frame_map = _frame_events(reset_events)
    frame_events = (
        []
        if frame_index_value is None
        else event_frame_map.get(frame_index_value, [])
    )

    reset_sequence = (
        None
        if not frame_events
        else build_event_sequence_contract(frame_events)
    )

    pre_post_order = (
        None
        if post is None
        else compare_provider_pre_post_order(
            pre,
            post,
            reset_events,
        )
    )
    if pre_post_order is not None:
        errors.extend(pre_post_order.get("errors") or [])

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "hit": int(bundle["hit"]),
        "frame_index": frame_index_value,
        "paths": {
            "pre": str(pre_info["path"]),
            "post": None
            if post_info is None
            else str(post_info["path"]),
        },
        "session": report,
        "reset_events": {
            "frame_event_count": len(frame_events),
            "sequence": reset_sequence,
            "pre_post_order": pre_post_order,
        },
        "ready": not errors,
        "status": "ready" if not errors else "blocked",
        "errors": list(dict.fromkeys(errors)),
    }


def analyze_capture_directory(
    directory: str | Path,
    *,
    reset_events_path: str | Path | None = None,
) -> dict[str, Any]:
    index = index_provider_snapshot_directory(directory)
    reset_events = (
        []
        if reset_events_path is None
        else _load_events(Path(reset_events_path))
    )

    bundles = [
        analyze_capture_bundle(
            bundle,
            reset_events=reset_events,
        )
        for bundle in index.get("bundles") or []
    ]

    errors = list(index.get("errors") or [])
    errors.extend(
        f"bundle-{bundle['provider_id']}-{bundle['hit']}:{error}"
        for bundle in bundles
        for error in bundle.get("errors") or []
    )

    return {
        "format": FORMAT,
        "version": 1,
        "directory": str(directory),
        "bundle_count": len(bundles),
        "bundles": bundles,
        "index": index,
        "reset_event_count": len(reset_events),
        "ready": not errors and all(
            bundle.get("ready") is True
            for bundle in bundles
        ),
        "status": "ready" if not errors else "blocked",
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_capture_directory(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    providers = defaultdict(int)
    with_post = 0
    frame_events = 0

    for bundle in report.get("bundles") or []:
        providers[str(bundle["provider_id"])] += 1
        if bundle["paths"].get("post") is not None:
            with_post += 1
        frame_events += int(
            bundle["reset_events"]["frame_event_count"]
        )

    return {
        "format": "SHIFT.SpecializedProviderCaptureBundleSummary/1",
        "version": 1,
        "directory": report.get("directory"),
        "bundle_count": int(report.get("bundle_count", 0)),
        "provider_bundle_counts": dict(sorted(providers.items())),
        "bundles_with_post": with_post,
        "reset_events_reconciled": frame_events,
        "reset_event_count_total": int(
            report.get("reset_event_count", 0)
        ),
        "ready_bundle_count": sum(
            bool(bundle.get("ready"))
            for bundle in report.get("bundles") or []
        ),
        "ready": bool(report.get("ready")),
    }


def build_capture_bundle_contract(
    directory: str | Path,
    *,
    reset_events_path: str | Path | None = None,
) -> dict[str, Any]:
    report = analyze_capture_directory(
        directory,
        reset_events_path=reset_events_path,
    )
    report["summary"] = summarize_capture_directory(report)
    return report


__all__ = [
    "FORMAT",
    "SNAPSHOT_RE",
    "parse_snapshot_filename",
    "index_provider_snapshot_directory",
    "analyze_capture_bundle",
    "analyze_capture_directory",
    "summarize_capture_directory",
    "build_capture_bundle_contract",
]
