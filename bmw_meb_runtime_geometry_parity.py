#!/usr/bin/env python3
"""Correlate a real SHIFT MEB layout with D3D9 indexed-draw geometry evidence.

This gate proves geometry-side runtime correlation only. It does not claim that
raw D3D9 vertex/index bytes were captured.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3MEBRuntimeGeometryParity/1"
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"

_STREAM_RE = re.compile(
    r"^\s*(?P<call>\d+) .*?SetStreamSource\(.*?StreamNumber = (?P<stream>\d+), "
    r"pStreamData = (?P<vb>0x[0-9a-fA-F]+).*?Stride = (?P<stride>\d+)\)"
)
_INDEX_RE = re.compile(
    r"^\s*(?P<call>\d+) .*?SetIndices\(.*?pIndexData = (?P<ib>0x[0-9a-fA-F]+)\)"
)
_DRAW_RE = re.compile(
    r"^\s*(?P<call>\d+) .*?DrawIndexedPrimitive\(.*?PrimitiveType = (?P<ptype>[^,]+), "
    r"BaseVertexIndex = (?P<base>-?\d+), MinVertexIndex = (?P<min>-?\d+), "
    r"NumVertices = (?P<num_vertices>\d+), startIndex = (?P<start_index>\d+), "
    r"primCount = (?P<prim_count>\d+)\)"
)

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

def _mesh_doc(document: Mapping[str, Any]) -> Mapping[str, Any]:
    mesh = document.get("mesh")
    return mesh if isinstance(mesh, Mapping) else document

def build_expectations(document: Mapping[str, Any]) -> dict[str, Any]:
    mesh = _mesh_doc(document)
    golden = document.get("golden")
    golden = golden if isinstance(golden, Mapping) else {}

    resource = str(golden.get("resource") or document.get("resource") or TARGET_RESOURCE).replace("\\", "/")
    resource_sha = str(golden.get("resource_sha256") or document.get("resource_sha256") or TARGET_SHA256).lower()
    vertex_count = int(mesh.get("vertex_count", 0))

    layouts = list(mesh.get("property_layouts") or [])
    if layouts:
        stride_parts = []
        for row in layouts:
            value = int(row.get("stride", 0) or 0)
            if value <= 0:
                raise ValueError(f"invalid property stride: {row}")
            stride_parts.append({"id": str(row.get("id")), "stride": value})
        vertex_stride = sum(row["stride"] for row in stride_parts)
    else:
        vertex_stride = int(mesh.get("vertex_stride", 0) or 0)
        if vertex_stride <= 0:
            raise ValueError("mesh vertex_stride or property_layouts is required")

    primitives = list(mesh.get("primitives") or [])
    if not primitives:
        raise ValueError("mesh primitives are required")

    primitive_rows = []
    for index, primitive in enumerate(primitives):
        first_index = int(primitive.get("first_index", 0))
        index_count = int(primitive.get("index_count", 0))
        if index_count <= 0 or index_count % 3:
            raise ValueError(f"invalid primitive index_count at {index}: {index_count}")
        primitive_rows.append({
            "index": index,
            "first_index": first_index,
            "index_count": index_count,
            "triangle_count": index_count // 3,
            "material": str(primitive.get("material", "")).replace("\\", "/"),
        })

    index_count = sum(row["index_count"] for row in primitive_rows)
    declared_index_count = int(mesh.get("index_count", index_count) or index_count)
    if declared_index_count != index_count:
        raise ValueError("mesh index_count conflicts with primitive index ranges")
    return {
        "resource": resource,
        "resource_sha256": resource_sha,
        "vertex_count": vertex_count,
        "property_layouts": stride_parts,
        "vertex_stride": vertex_stride,
        "vertex_buffer_bytes": vertex_count * vertex_stride,
        "index_count": index_count,
        "index_buffer_bytes_uint16": index_count * 2,
        "primitives": primitive_rows,
    }

def parse_draw_evidence(text: str) -> list[dict[str, Any]]:
    stream_vb = None
    stream_stride = None
    index_buffer = None
    draws = []
    for line_number, line in enumerate(text.splitlines(), 1):
        stream_match = _STREAM_RE.search(line)
        if stream_match and int(stream_match.group("stream")) == 0:
            stream_vb = stream_match.group("vb").lower()
            stream_stride = int(stream_match.group("stride"))
            continue
        index_match = _INDEX_RE.search(line)
        if index_match:
            index_buffer = index_match.group("ib").lower()
            continue
        draw_match = _DRAW_RE.search(line)
        if not draw_match:
            continue
        draws.append({
            "draw_index": len(draws),
            "line": line_number,
            "call": int(draw_match.group("call")),
            "primitive_type": draw_match.group("ptype").strip(),
            "base_vertex_index": int(draw_match.group("base")),
            "min_vertex_index": int(draw_match.group("min")),
            "num_vertices": int(draw_match.group("num_vertices")),
            "start_index": int(draw_match.group("start_index")),
            "prim_count": int(draw_match.group("prim_count")),
            "vb": stream_vb,
            "stride": stream_stride,
            "ib": index_buffer,
        })
    return draws

def correlate(expected: Mapping[str, Any], draws: list[Mapping[str, Any]]) -> dict[str, Any]:
    blockers = []
    target_draws = [
        draw for draw in draws
        if draw.get("primitive_type") == "D3DPT_TRIANGLELIST"
        and draw.get("base_vertex_index") == 0
        and draw.get("start_index") == 0
        and draw.get("num_vertices") == expected["vertex_count"]
        and draw.get("stride") == expected["vertex_stride"]
        and draw.get("vb") and draw.get("ib")
    ]

    expected_counts = [int(row["triangle_count"]) for row in expected["primitives"]]
    observed = collections.defaultdict(list)
    for draw in target_draws:
        observed[int(draw["prim_count"])].append(draw)

    correlations = []
    for primitive in expected["primitives"]:
        candidates = observed.get(int(primitive["triangle_count"]), [])
        if not candidates:
            blockers.append(f"geometry:missing-primitive-triangle-count:{primitive['triangle_count']}")
            correlations.append({**primitive, "status": "missing", "runtime_draws": []})
            continue
        correlations.append({
            **primitive,
            "status": "match",
            "runtime_draws": [dict(x) for x in candidates[:8]],
            "representative_draw": dict(candidates[0]),
        })

    matched = [x for x in correlations if x["status"] == "match"]
    vb_values = {str(x["representative_draw"]["vb"]) for x in matched}
    if len(vb_values) != 1:
        blockers.append(f"geometry:vertex-buffer-binding-set:{sorted(vb_values)}")

    ib_values = [str(x["representative_draw"]["ib"]) for x in matched]
    if len(ib_values) != len(set(ib_values)):
        blockers.append("geometry:index-buffer-binding-not-unique-per-primitive")

    observed_histogram = collections.Counter(int(x["prim_count"]) for x in target_draws)
    if sum(expected_counts) != expected["index_count"] // 3:
        blockers.append("geometry:primitive-triangle-total-mismatch")
    if expected["resource"] != TARGET_RESOURCE:
        blockers.append("geometry:unexpected-target-resource")
    if expected["resource_sha256"].lower() != TARGET_SHA256:
        blockers.append("geometry:unexpected-target-sha256")

    return {
        "format": FORMAT,
        "status": "match" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "expected": dict(expected),
        "runtime_stream": {
            "vertex_buffer": next(iter(vb_values)) if len(vb_values) == 1 else sorted(vb_values),
            "stride": expected["vertex_stride"],
            "derived_vertex_buffer_bytes": expected["vertex_buffer_bytes"],
        },
        "primitive_correlations": correlations,
        "coverage": {
            "expected_primitive_triangle_counts": expected_counts,
            "observed_target_draw_count": len(target_draws),
            "observed_target_triangle_count_histogram": dict(sorted(observed_histogram.items())),
            "required_count_coverage": {
                str(count): int(observed_histogram.get(count, 0))
                for count in sorted(set(expected_counts))
            },
        },
    }

def validate_repacked_artifact(path: Path, expected_size: int, label: str, expected_sha256: str | None) -> dict[str, Any]:
    actual_size = path.stat().st_size
    actual_sha256 = sha256_file(path)
    blockers = []
    if actual_size != expected_size:
        blockers.append(f"{label}:size-mismatch:{actual_size}:{expected_size}")
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        blockers.append(f"{label}:sha256-mismatch:{actual_sha256}:{expected_sha256}")
    return {
        "path": str(path),
        "size": actual_size,
        "sha256": actual_sha256,
        "expected_size": expected_size,
        "status": "match" if not blockers else "blocked",
        "blocking_reasons": blockers,
    }

def build_report(summary_path: Path, geometry_path: Path, *, repacked_vb: Path | None = None,
                 repacked_ib16: Path | None = None, expected_vb_sha256: str | None = None,
                 expected_ib16_sha256: str | None = None) -> dict[str, Any]:
    expected = build_expectations(json.loads(summary_path.read_text(encoding="utf-8")))
    if expected["vertex_count"] <= 0:
        raise ValueError("vertex_count must be positive")
    report = correlate(expected, parse_draw_evidence(geometry_path.read_text(encoding="utf-8", errors="replace")))
    artifacts = {}
    for label, path, size, sha in (
        ("repacked_vertex_buffer", repacked_vb, expected["vertex_buffer_bytes"], expected_vb_sha256),
        ("repacked_index_buffer_uint16", repacked_ib16, expected["index_buffer_bytes_uint16"], expected_ib16_sha256),
    ):
        if path is not None:
            artifacts[label] = validate_repacked_artifact(path, size, label, sha)
            report["blocking_reasons"].extend(artifacts[label]["blocking_reasons"])
    report["blocking_reasons"] = list(dict.fromkeys(report["blocking_reasons"]))
    report["ready"] = not report["blocking_reasons"]
    report["status"] = "match" if report["ready"] else "blocked"
    report["source"] = {"summary": summary_path.name, "geometry_dump": geometry_path.name, "draw_count": len(parse_draw_evidence(geometry_path.read_text(encoding="utf-8", errors="replace")))}
    if artifacts:
        report["repacked_artifacts"] = artifacts
    return report

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("summary", type=Path)
    ap.add_argument("geometry", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--repacked-vb", type=Path)
    ap.add_argument("--repacked-ib16", type=Path)
    ap.add_argument("--expected-vb-sha256")
    ap.add_argument("--expected-ib16-sha256")
    args = ap.parse_args(argv)
    report = build_report(args.summary, args.geometry, repacked_vb=args.repacked_vb,
                          repacked_ib16=args.repacked_ib16, expected_vb_sha256=args.expected_vb_sha256,
                          expected_ib16_sha256=args.expected_ib16_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
