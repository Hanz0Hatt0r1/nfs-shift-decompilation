"""Compare captured BMW D3D9 buffer payloads with canonical MEB-derived bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3RuntimeBufferPayloadParity/1"
TARGET_VB = "0x27b39460"
TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"


def _read(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _creation_index(snapshot: Mapping[str, Any], kind: str, pointer: str) -> int | None:
    key = "vertex_buffer" if kind == "vertex_buffer" else "index_buffer"
    binding = (
        (snapshot.get("active_stream_sources") or [])[0]
        if kind == "vertex_buffer" and snapshot.get("active_stream_sources")
        else snapshot.get("index_binding")
    )
    if not isinstance(binding, Mapping) or str(binding.get(key + "_ptr") or "").lower() != pointer.lower():
        return None
    creation = binding.get("resource_creation")
    if not isinstance(creation, Mapping):
        return None
    try:
        return int(creation.get("event_index"))
    except (TypeError, ValueError):
        return None


def _payload_rows(
    runtime_report: Mapping[str, Any],
    pointer: str,
    *,
    kind: str,
    creation_event_index: int | None,
    draw_event_index: int | None,
) -> list[Mapping[str, Any]]:
    rows = []
    for row in runtime_report.get("buffer_payloads") or []:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("buffer_ptr") or "").lower() != pointer.lower():
            continue
        if row.get("resource_type_name") != kind:
            continue
        if row.get("snapshot_status") != "captured" or not row.get("payload_path"):
            continue
        try:
            event_index = int(row.get("event_index", -1))
            offset = int(row.get("offset", -1))
        except (TypeError, ValueError):
            continue
        if offset != 0:
            continue
        if creation_event_index is not None and event_index <= creation_event_index:
            continue
        if draw_event_index is not None and event_index > draw_event_index:
            continue
        rows.append(row)
    return sorted(rows, key=lambda row: int(row.get("event_index", -1)))


def _target_draws(runtime_report: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    out = []
    for frame in runtime_report.get("frames") or []:
        if not isinstance(frame, Mapping):
            continue
        for snapshot in frame.get("draw_snapshots") or []:
            if not isinstance(snapshot, Mapping):
                continue
            draw = snapshot.get("draw") or {}
            streams = snapshot.get("active_stream_sources") or []
            stream0 = next(
                (row for row in streams if isinstance(row, Mapping) and int(row.get("stream", -1)) == 0),
                None,
            )
            if not isinstance(stream0, Mapping):
                continue
            if str(stream0.get("vertex_buffer_ptr") or "").lower() != TARGET_VB:
                continue
            if int(stream0.get("stride", -1)) != 76 or int(draw.get("base_vertex_index", -1)) != 0:
                continue
            if int(draw.get("num_vertices", -1)) != 3550:
                continue
            out.append((frame, snapshot))
    return out


def compare_payload(
    payload_path: str | Path,
    expected: bytes,
    *,
    label: str,
) -> dict[str, Any]:
    path = Path(payload_path)
    if not path.is_file():
        return {
            "label": label,
            "status": "missing",
            "ready": False,
            "payload_path": str(path),
            "blocking_reasons": ["buffer-payload:file-not-found"],
        }
    actual = path.read_bytes()
    actual_sha = _sha(actual)
    expected_sha = _sha(expected)
    reasons = []
    if len(actual) != len(expected):
        reasons.append(
            f"buffer-payload:length-mismatch:{label}:{len(actual)}:{len(expected)}"
        )
    if actual != expected:
        reasons.append(
            f"buffer-payload:sha256-mismatch:{label}:{actual_sha}:{expected_sha}"
        )
    return {
        "label": label,
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "payload_path": str(path),
        "observed_byte_size": len(actual),
        "expected_byte_size": len(expected),
        "observed_sha256": actual_sha,
        "expected_sha256": expected_sha,
        "blocking_reasons": reasons,
    }


def build_report(
    runtime_report: Mapping[str, Any],
    geometry_evidence: Mapping[str, Any],
    *,
    expected_vb: str | Path,
    expected_ib16: str | Path,
) -> dict[str, Any]:
    resource = geometry_evidence.get("expected") or geometry_evidence.get("resource") or {}
    resource_path = str(resource.get("resource") or resource.get("path") or "")
    resource_sha = str(resource.get("resource_sha256") or resource.get("sha256") or "").lower()
    if resource_path and resource_path != TARGET_MEB:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["geometry-resource:path-mismatch"],
        }
    if resource_sha and resource_sha != TARGET_SHA256:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["geometry-resource:sha256-mismatch"],
        }

    vb_expected = _read(expected_vb)
    ib_expected = _read(expected_ib16)
    target_draws = _target_draws(runtime_report)
    if not target_draws:
        return {
            "format": FORMAT,
            "status": "not-found",
            "ready": False,
            "resource": {"path": TARGET_MEB, "sha256": TARGET_SHA256},
            "blocking_reasons": ["runtime:target-bmw-draw-not-observed"],
        }

    results = []
    seen_ib = set()
    for frame, snapshot in target_draws:
        draw = snapshot.get("draw") or {}
        draw_event_index = None
        try:
            draw_event_index = int(draw.get("event_index"))
        except (TypeError, ValueError):
            pass
        stream0 = next(
            row for row in snapshot.get("active_stream_sources") or []
            if isinstance(row, Mapping) and int(row.get("stream", -1)) == 0
        )
        vb_pointer = str(stream0.get("vertex_buffer_ptr"))
        vb_creation = _creation_index(snapshot, "vertex_buffer", vb_pointer)
        vb_payloads = _payload_rows(
            runtime_report,
            vb_pointer,
            kind="vertex_buffer",
            creation_event_index=vb_creation,
            draw_event_index=draw_event_index,
        )
        if vb_payloads:
            results.append({
                "frame": frame.get("frame"),
                "draw_index": snapshot.get("draw_index"),
                "kind": "vertex_buffer",
                "pointer": vb_pointer,
                "comparison": compare_payload(vb_payloads[-1]["payload_path"], vb_expected, label="vertex-buffer"),
            })

        index_binding = snapshot.get("index_binding") or {}
        ib_pointer = str(index_binding.get("index_buffer_ptr") or "")
        if ib_pointer and ib_pointer not in seen_ib:
            seen_ib.add(ib_pointer)
            creation = _creation_index(snapshot, "index_buffer", ib_pointer)
            payloads = _payload_rows(
                runtime_report,
                ib_pointer,
                kind="index_buffer",
                creation_event_index=creation,
                draw_event_index=draw_event_index,
            )
            primitive_count = int(draw.get("primitive_count", 0))
            start_index = int(draw.get("start_index", 0))
            expected_slice = ib_expected[start_index * 2:(start_index + primitive_count * 3) * 2]
            if payloads:
                results.append({
                    "frame": frame.get("frame"),
                    "draw_index": snapshot.get("draw_index"),
                    "kind": "index_buffer",
                    "pointer": ib_pointer,
                    "primitive_count": primitive_count,
                    "expected_slice_offset": start_index * 2,
                    "comparison": compare_payload(
                        payloads[-1]["payload_path"],
                        expected_slice,
                        label=f"index-buffer:{ib_pointer}",
                    ),
                })

    blockers = [
        reason
        for row in results
        for reason in row.get("comparison", {}).get("blocking_reasons") or []
    ]
    complete_vertex = any(
        row["kind"] == "vertex_buffer" and row["comparison"].get("ready")
        for row in results
    )
    matched_ibs = {
        row["pointer"]
        for row in results
        if row["kind"] == "index_buffer" and row["comparison"].get("ready")
    }
    ready = complete_vertex and len(matched_ibs) >= 6 and not blockers
    return {
        "format": FORMAT,
        "status": "match" if ready else ("partial" if results and not blockers else "blocked"),
        "ready": ready,
        "resource": {"path": TARGET_MEB, "sha256": TARGET_SHA256},
        "target_draw_count": len(target_draws),
        "matched_vertex_buffer": complete_vertex,
        "matched_index_buffer_count": len(matched_ibs),
        "results": results,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "boundary": {
            "creation_instance": "consumed",
            "raw_runtime_vb_bytes": "proven" if complete_vertex and not blockers else "not-proven",
            "raw_runtime_ib_bytes": "proven" if len(matched_ibs) >= 6 and not blockers else "not-proven",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare BMW runtime VB/IB payloads with canonical MEB bytes")
    parser.add_argument("runtime_report")
    parser.add_argument("geometry_evidence")
    parser.add_argument("expected_vb")
    parser.add_argument("expected_ib16")
    parser.add_argument("output")
    args = parser.parse_args()
    runtime = json.loads(Path(args.runtime_report).read_text(encoding="utf-8"))
    geometry = json.loads(Path(args.geometry_evidence).read_text(encoding="utf-8"))
    report = build_report(
        runtime,
        geometry,
        expected_vb=args.expected_vb,
        expected_ib16=args.expected_ib16,
    )
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
