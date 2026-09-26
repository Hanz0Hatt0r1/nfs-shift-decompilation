#!/usr/bin/env python3
"""Intake a real BMW D3D9 buffer capture and produce one parity report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_meb_runtime_buffer_artifacts import build_artifact_report, extract_meb_from_bff
from bmw_runtime_buffer_payload_parity import build_report as build_buffer_parity_report
from d3d9_runtime_trace import build_runtime_binding_evidence, load_events

FORMAT = "SHIFT.BMWM3BufferCaptureIntake/1"


def normalize_payload_paths(events: list[dict[str, Any]], payload_dir: str | Path) -> list[dict[str, Any]]:
    """Resolve capture-relative buffer payload paths without touching absolute paths."""
    root = Path(payload_dir)
    normalized = []
    for row in events:
        item = dict(row)
        if item.get("event") == "buffer_payload":
            raw = item.get("payload_path")
            if isinstance(raw, str) and raw and not Path(raw).is_absolute():
                item["payload_path"] = str(root / raw)
        normalized.append(item)
    return normalized


def write_expected_artifacts(output_dir: Path, bff: str | Path) -> tuple[dict[str, Any], Path, Path]:
    meb_bytes, provenance = extract_meb_from_bff(bff)
    artifact_dir = output_dir / "expected"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report, vertex_bytes, index_bytes, primitive_bytes = build_artifact_report(
        meb_bytes,
        source=provenance,
    )
    vertex_path = artifact_dir / "vertex_buffer.meb-order.bin"
    index_path = artifact_dir / "index_buffer.uint16.bin"
    vertex_path.write_bytes(vertex_bytes)
    index_path.write_bytes(index_bytes)
    for index, payload in enumerate(primitive_bytes):
        (artifact_dir / f"index_buffer_{index:02d}.uint16.bin").write_bytes(payload)
    report["outputs"] = {
        "vertex_buffer": str(vertex_path),
        "index_buffer": str(index_path),
        "primitive_buffers": [
            str(artifact_dir / f"index_buffer_{index:02d}.uint16.bin")
            for index in range(len(primitive_bytes))
        ],
    }
    (artifact_dir / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report, vertex_path, index_path


def run_intake(
    capture_jsonl: str | Path,
    payload_dir: str | Path,
    geometry_evidence: str | Path,
    bff: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    raw_events = load_events(capture_jsonl)
    events = normalize_payload_paths(raw_events, payload_dir)
    runtime = build_runtime_binding_evidence(events)
    geometry = json.loads(Path(geometry_evidence).read_text(encoding="utf-8"))
    artifact_manifest, expected_vb, expected_ib = write_expected_artifacts(output, bff)
    parity = build_buffer_parity_report(
        runtime,
        geometry,
        expected_vb=expected_vb,
        expected_ib16=expected_ib,
    )

    runtime_blockers = list(runtime.get("blocking_reasons") or [])
    result_blockers = list(dict.fromkeys(
        runtime_blockers + list(parity.get("blocking_reasons") or [])
    ))
    result = {
        "format": FORMAT,
        "status": "match" if parity.get("ready") and not runtime_blockers else (
            "blocked" if result_blockers else "partial"
        ),
        "ready": bool(parity.get("ready")) and not runtime_blockers,
        "source": {
            "capture_jsonl": str(Path(capture_jsonl).resolve()),
            "payload_dir": str(Path(payload_dir).resolve()),
            "geometry_evidence": str(Path(geometry_evidence).resolve()),
            "bff": str(Path(bff).resolve()),
        },
        "capture": {
            "event_count": len(events),
            "buffer_payload_event_count": sum(
                1 for row in events if row.get("event") == "buffer_payload"
            ),
            "runtime_frame_count": runtime.get("trace", {}).get("frame_count", 0),
            "target_draw_count": parity.get("target_draw_count", 0),
        },
        "expected_artifacts": artifact_manifest,
        "runtime": {
            "format": runtime.get("format"),
            "status": runtime.get("status"),
            "trace": runtime.get("trace"),
        },
        "parity": parity,
        "blocking_reasons": result_blockers,
        "evidence_boundary": {
            "raw_runtime_vb_bytes": (
                "proven" if result.get("ready") else "not-proven"
            ),
            "raw_runtime_ib_bytes": (
                "proven" if result.get("ready") else "not-proven"
            ),
        },
    }
    (output / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl")
    parser.add_argument("payload_dir")
    parser.add_argument("geometry_evidence")
    parser.add_argument("bff")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)
    result = run_intake(
        args.capture_jsonl,
        args.payload_dir,
        args.geometry_evidence,
        args.bff,
        args.output_dir,
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "buffer_payload_event_count": result["capture"]["buffer_payload_event_count"],
        "target_draw_count": result["capture"]["target_draw_count"],
        "blocking_reasons": result["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
