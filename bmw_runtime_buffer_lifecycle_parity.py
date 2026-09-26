"""Correlate BMW M3 runtime buffer pointers with D3D9 creation lifecycle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3RuntimeBufferLifecycleParity/1"
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"

_VB_RE = re.compile(
    r"^(?P<call>\d+)\s+IDirect3DDevice9::CreateVertexBuffer\(.*?"
    r"Length = (?P<length>\d+), Usage = (?P<usage>.*?), FVF = (?P<fvf>0x[0-9A-Fa-f]+), "
    r"Pool = (?P<pool>D3DPOOL_[A-Z_]+), ppVertexBuffer = &(?P<ptr>0x[0-9A-Fa-f]+)"
)
_IB_RE = re.compile(
    r"^(?P<call>\d+)\s+IDirect3DDevice9::CreateIndexBuffer\(.*?"
    r"Length = (?P<length>\d+), Usage = (?P<usage>.*?), Format = (?P<format>D3DFMT_[A-Z0-9_]+), "
    r"Pool = (?P<pool>D3DPOOL_[A-Z_]+), ppIndexBuffer = &(?P<ptr>0x[0-9A-Fa-f]+)"
)
_DRAW_RE = re.compile(r"^(?P<call>\d+)\s+IDirect3DDevice9::DrawIndexedPrimitive\(")


def parse_buffer_creations(text: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"vertex": [], "index": []}
    for line_no, line in enumerate(text.splitlines(), 1):
        match = _VB_RE.match(line)
        if match:
            row = match.groupdict()
            result["vertex"].append({
                "call": int(row["call"]),
                "line": line_no,
                "pointer": row["ptr"].lower(),
                "length": int(row["length"]),
                "usage": row["usage"].strip(),
                "fvf": int(row["fvf"], 0),
                "pool": row["pool"],
            })
            continue
        match = _IB_RE.match(line)
        if match:
            row = match.groupdict()
            result["index"].append({
                "call": int(row["call"]),
                "line": line_no,
                "pointer": row["ptr"].lower(),
                "length": int(row["length"]),
                "usage": row["usage"].strip(),
                "format": row["format"],
                "pool": row["pool"],
            })
    return result


def _latest_before(rows: list[Mapping[str, Any]], pointer: str, call: int) -> Mapping[str, Any] | None:
    pointer = str(pointer).lower()
    candidates = [
        row for row in rows
        if str(row.get("pointer", "")).lower() == pointer
        and int(row.get("call", -1)) < call
    ]
    return max(candidates, key=lambda row: int(row.get("call", -1)), default=None)


def build_report(geometry_evidence: Mapping[str, Any], resource_create_log: str) -> dict[str, Any]:
    resource = geometry_evidence.get("resource") or {}
    resource_path = str(resource.get("path") or "").replace("\\", "/")
    resource_sha256 = str(resource.get("sha256") or "").lower()
    runtime_stream = geometry_evidence.get("runtime_stream") or {}
    vb_pointer = str(runtime_stream.get("vertex_buffer") or "").lower()
    expected_vb_bytes = int(runtime_stream.get("derived_vertex_buffer_bytes") or 0)

    primitive_rows = geometry_evidence.get("primitive_correlations") or []
    expected_ibs = []
    for primitive in primitive_rows:
        runtime_ib = str(primitive.get("runtime_ib") or "").lower()
        if not runtime_ib:
            representative = primitive.get("representative") or {}
            runtime_ib = str(representative.get("runtime_ib") or "").lower()
        expected_ibs.append({
            "primitive_index": int(primitive.get("index", len(expected_ibs))),
            "pointer": runtime_ib,
            "expected_bytes": int(primitive.get("triangle_count", 0)) * 3 * 2,
            "triangle_count": int(primitive.get("triangle_count", 0)),
        })

    creates = parse_buffer_creations(resource_create_log)
    draw_calls = [
        int(match.group("call"))
        for line in resource_create_log.splitlines()
        if (match := _DRAW_RE.match(line))
    ]
    target_draw_call = max(draw_calls, default=-1)
    blockers: list[str] = []

    vb_creation = _latest_before(creates["vertex"], vb_pointer, target_draw_call)
    if not vb_creation:
        blockers.append("vertex-buffer:create-not-observed-before-draw")
    else:
        if vb_creation["length"] != expected_vb_bytes:
            blockers.append(
                f"vertex-buffer:length-mismatch:{vb_creation['length']}:{expected_vb_bytes}"
            )
        if vb_creation["fvf"] != 0:
            blockers.append(f"vertex-buffer:fvf-unexpected:{vb_creation['fvf']}")
        if vb_creation["pool"] != "D3DPOOL_MANAGED":
            blockers.append(f"vertex-buffer:pool-unexpected:{vb_creation['pool']}")

    index_rows = []
    for expected in expected_ibs:
        creation = _latest_before(creates["index"], expected["pointer"], target_draw_call)
        row = {
            **expected,
            "status": "match" if creation else "not-observed",
            "creation": dict(creation) if creation else None,
        }
        if not creation:
            blockers.append(
                f"index-buffer:create-not-observed-before-draw:{expected['pointer']}"
            )
        else:
            if creation["length"] != expected["expected_bytes"]:
                blockers.append(
                    f"index-buffer:length-mismatch:{expected['pointer']}:"
                    f"{creation['length']}:{expected['expected_bytes']}"
                )
            if creation["format"] != "D3DFMT_INDEX16":
                blockers.append(
                    f"index-buffer:format-unexpected:{expected['pointer']}:{creation['format']}"
                )
            if creation["pool"] != "D3DPOOL_MANAGED":
                blockers.append(
                    f"index-buffer:pool-unexpected:{expected['pointer']}:{creation['pool']}"
                )
        index_rows.append(row)

    if resource_path != TARGET_RESOURCE:
        blockers.append("geometry-resource:path-mismatch")
    if resource_sha256 != TARGET_SHA256:
        blockers.append("geometry-resource:sha256-mismatch")

    return {
        "format": FORMAT,
        "status": "match" if not blockers else "blocked",
        "ready": not blockers,
        "resource": {
            "path": resource_path,
            "sha256": resource_sha256,
        },
        "target_draw_call": target_draw_call,
        "target_draw_count": int((geometry_evidence.get("runtime_stream") or {}).get("observed_target_draw_count", 0)),
        "vertex_buffer": {
            "pointer": vb_pointer,
            "expected_bytes": expected_vb_bytes,
            "creation": dict(vb_creation) if vb_creation else None,
            "status": "match" if vb_creation and vb_creation["length"] == expected_vb_bytes else "blocked",
        },
        "index_buffers": index_rows,
        "creation_counts": {
            "vertex": len(creates["vertex"]),
            "index": len(creates["index"]),
        },
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "boundary": {
            "pointer_to_create_instance": "proven" if not blockers else "partial",
            "raw_runtime_vb_ib_bytes": "not-captured",
        },
    }


def validate_files(
    geometry_evidence_path: str | Path,
    resource_create_log_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    geometry_path = Path(geometry_evidence_path)
    log_path = Path(resource_create_log_path)
    evidence = json.loads(geometry_path.read_text(encoding="utf-8"))
    log_bytes = log_path.read_bytes()
    report = build_report(evidence, log_bytes.decode("utf-8", errors="replace"))
    report["source"] = {
        "geometry_evidence": geometry_path.name,
        "resource_create_log": log_path.name,
        "resource_create_log_sha256": hashlib.sha256(log_bytes).hexdigest(),
        "resource_create_log_size": len(log_bytes),
    }
    reasons = list(report["blocking_reasons"])
    report["validation"] = {
        "format": FORMAT,
        "status": "match" if not reasons else "blocked",
        "ready": not reasons,
        "blocking_reasons": reasons,
    }
    Path(output_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BMW M3 D3D9 buffer creation lifecycle")
    parser.add_argument("geometry_evidence")
    parser.add_argument("resource_create_log")
    parser.add_argument("output")
    args = parser.parse_args()
    report = validate_files(args.geometry_evidence, args.resource_create_log, args.output)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
