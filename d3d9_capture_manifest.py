"""Build a non-authoritative provenance manifest for an external D3D9 capture."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_capture_schema import validate_capture_events
from d3d9_runtime_trace_integrity import validate_runtime_trace_integrity

FORMAT = "SHIFT.D3D9RuntimeCaptureManifest/1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(events)
    frames = [row.get("frame") for row in rows if row.get("frame") is not None]
    frame_values = sorted({int(value) for value in frames if isinstance(value, int)})
    draws = sum(1 for row in rows if row.get("event") == "draw_indexed_primitive")
    presents = sum(
        1
        for row in rows
        if row.get("event") in {"present_screenshot", "present_screenshot_failed"}
    )
    event_indices = [
        row.get("event_index")
        for row in rows
        if isinstance(row.get("event_index"), int)
    ]
    return {
        "event_count": len(rows),
        "draw_indexed_primitive_count": draws,
        "present_boundary_artifact_count": presents,
        "frame_count": len(frame_values),
        "first_frame": frame_values[0] if frame_values else None,
        "last_frame": frame_values[-1] if frame_values else None,
        "first_event_index": min(event_indices) if event_indices else None,
        "last_event_index": max(event_indices) if event_indices else None,
    }


def build_capture_manifest(
    capture_path: str | Path,
    *,
    events: Iterable[Mapping[str, Any]] | None = None,
    producer_binary: str | Path | None = None,
) -> dict[str, Any]:
    capture = Path(capture_path)
    if not capture.is_file():
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["capture:file-not-found"],
            "authenticity": {
                "status": "unverified",
                "reason": "retail-runtime-execution-not-independently-attested",
            },
            "source": {"path": str(capture)},
        }

    rows = list(events or [])
    schema = validate_capture_events(rows)
    integrity = validate_runtime_trace_integrity(rows)
    producer = None
    if producer_binary is not None:
        producer_path = Path(producer_binary)
        producer = {
            "path": str(producer_path),
            "exists": producer_path.is_file(),
            "sha256": _sha256_file(producer_path) if producer_path.is_file() else None,
            "size": producer_path.stat().st_size if producer_path.is_file() else None,
        }

    blockers = []
    if not schema.get("ready"):
        blockers.extend(
            "capture-schema:" + str(reason.get("reason"))
            for reason in schema.get("blocking_reasons") or []
        )
    if integrity.get("status") not in {"observed", "not-supplied"}:
        blockers.extend(
            "capture-integrity:" + str(reason.get("reason"))
            for reason in integrity.get("blocking_reasons") or []
        )

    return {
        "format": FORMAT,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "authenticity": {
            "status": "unverified",
            "reason": "retail-runtime-execution-not-independently-attested",
        },
        "source": {
            "path": str(capture),
            "sha256": _sha256_file(capture),
            "size": capture.stat().st_size,
        },
        "producer": producer,
        "schema": {
            "format": schema["format"],
            "status": schema["status"],
            "event_count": schema["event_count"],
        },
        "integrity": {
            "format": integrity["format"],
            "status": integrity["status"],
            "event_index": integrity.get("event_index") or {},
        },
        "statistics": _stats(rows),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build D3D9 capture provenance manifest")
    parser.add_argument("capture")
    parser.add_argument("output")
    parser.add_argument("--producer-binary")
    args = parser.parse_args(argv)

    report = build_capture_manifest(
        args.capture,
        producer_binary=args.producer_binary,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "authenticity": report["authenticity"]["status"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
