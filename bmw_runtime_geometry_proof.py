#!/usr/bin/env python3
"""Promote proven BMW M3 VB/IB byte parity into a strict geometry-proof contract.

The proof combines three independent artifacts:
  * Phase 332 runtime geometry correlation;
  * Phase 351 direct apitrace BLOB parity;
  * exact pointer/creation provenance carried by the BLOB evidence.

The contract deliberately fails closed when the parity report comes from an
older verifier that did not preserve runtime buffer pointer metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3RuntimeGeometryProof/1"
PARITY_FORMAT = "SHIFT.BMWM3DirectBlobParity/1"
GEOMETRY_FORMAT = "SHIFT.BMWM3MEBRuntimeGeometryParity/1"

TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
TARGET_VB = "0x27b39460"
TARGET_VB_SIZE = 269800
TARGET_VB_STRIDE = 76
TARGET_VERTEX_COUNT = 3550
TARGET_IB_BY_TRIANGLES = {
    50: "0x27b394e0",
    2098: "0x27b39560",
    2462: "0x27b395e0",
    204: "0x27b39660",
    192: "0x27b396e0",
    28: "0x27b39760",
}
TARGET_IB_SIZES = (300, 12588, 14772, 1224, 1152, 168)


def _json(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    data = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON object expected")
    return data


def _norm_ptr(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    try:
        return f"0x{int(text, 0):x}"
    except ValueError:
        return text


def _check_geometry(geometry: Mapping[str, Any]) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    if geometry.get("format") != GEOMETRY_FORMAT:
        reasons.append("geometry:invalid-format")
    if geometry.get("status") != "match" or geometry.get("ready") is not True:
        reasons.append("geometry:not-ready")

    resource = geometry.get("resource") or {}
    resource_path = str(resource.get("path") or resource.get("resource") or "")
    resource_sha = str(resource.get("sha256") or resource.get("resource_sha256") or "").lower()
    if resource_path != TARGET_MEB:
        reasons.append("geometry:resource-path-mismatch")
    if resource_sha != TARGET_SHA256:
        reasons.append("geometry:resource-sha256-mismatch")

    stream = geometry.get("runtime_stream") or {}
    if _norm_ptr(stream.get("vertex_buffer")) != TARGET_VB:
        reasons.append("geometry:vertex-buffer-pointer-mismatch")
    if int(stream.get("stride", -1)) != TARGET_VB_STRIDE:
        reasons.append("geometry:vertex-stride-mismatch")
    if int(stream.get("derived_vertex_buffer_bytes", -1)) != TARGET_VB_SIZE:
        reasons.append("geometry:vertex-buffer-size-mismatch")

    rows = geometry.get("primitive_correlations") or []
    observed: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        try:
            triangles = int(row.get("triangle_count"))
        except (TypeError, ValueError):
            continue
        observed[triangles] = dict(row)

    for triangles, expected_ptr in sorted(TARGET_IB_BY_TRIANGLES.items()):
        row = observed.get(triangles)
        if row is None:
            reasons.append(f"geometry:missing-primitive:{triangles}")
            continue
        if row.get("status") != "match":
            reasons.append(f"geometry:primitive-not-matched:{triangles}")
        if _norm_ptr(row.get("runtime_ib")) != expected_ptr:
            reasons.append(f"geometry:primitive-ib-pointer-mismatch:{triangles}")
    return reasons, {
        "resource": resource_path,
        "resource_sha256": resource_sha,
        "vertex_buffer": _norm_ptr(stream.get("vertex_buffer")),
        "vertex_stride": int(stream.get("stride", -1)),
        "vertex_buffer_bytes": int(stream.get("derived_vertex_buffer_bytes", -1)),
        "primitive_triangle_counts": sorted(observed),
    }


def _check_parity(parity: Mapping[str, Any]) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    if parity.get("format") != PARITY_FORMAT:
        reasons.append("parity:invalid-format")
    if parity.get("ready") is not True or parity.get("status") != "match":
        reasons.append("parity:not-ready")
    if int(parity.get("matches", -1)) != 7:
        reasons.append("parity:expected-seven-matches")
    boundary = parity.get("evidence_boundary") or {}
    for key in ("raw_runtime_vb_bytes", "raw_runtime_ib_bytes", "meb_byte_parity"):
        if boundary.get(key) != "proven":
            reasons.append(f"parity:boundary-not-proven:{key}")

    results = [row for row in parity.get("results") or [] if isinstance(row, Mapping)]
    if len(results) != 7:
        reasons.append(f"parity:expected-seven-results:{len(results)}")

    vb_rows = [row for row in results if str(row.get("label")) == "vertex-buffer"]
    if len(vb_rows) != 1:
        reasons.append(f"parity:expected-one-vb-result:{len(vb_rows)}")
    else:
        row = vb_rows[0]
        if _norm_ptr(row.get("runtime_buffer_pointer")) != TARGET_VB:
            reasons.append("parity:vertex-buffer-pointer-metadata-missing-or-mismatch")
        comparison = row.get("comparison") or {}
        if comparison.get("ready") is not True:
            reasons.append("parity:vertex-buffer-byte-comparison-not-ready")
        if int(comparison.get("observed_byte_size", -1)) != TARGET_VB_SIZE:
            reasons.append("parity:vertex-buffer-size-metadata-mismatch")

    ib_rows = [
        row for row in results
        if str(row.get("label", "")).startswith("index-buffer:")
    ]
    if len(ib_rows) != 6:
        reasons.append(f"parity:expected-six-ib-results:{len(ib_rows)}")

    expected_ptrs = set(TARGET_IB_BY_TRIANGLES.values())
    observed_ptrs: set[str] = set()
    observed_sizes: set[int] = set()
    for row in ib_rows:
        pointer = _norm_ptr(row.get("runtime_buffer_pointer"))
        if not pointer:
            reasons.append("parity:index-buffer-pointer-metadata-missing")
        observed_ptrs.add(pointer)
        comparison = row.get("comparison") or {}
        if comparison.get("ready") is not True:
            reasons.append(f"parity:index-byte-comparison-not-ready:{row.get('label')}")
        try:
            observed_sizes.add(int(comparison.get("observed_byte_size")))
        except (TypeError, ValueError):
            pass

    if observed_ptrs != expected_ptrs:
        reasons.append(
            "parity:index-buffer-pointer-set-mismatch:"
            + ",".join(sorted(observed_ptrs))
        )
    if observed_sizes != set(TARGET_IB_SIZES):
        reasons.append(
            "parity:index-buffer-size-set-mismatch:"
            + ",".join(str(x) for x in sorted(observed_sizes))
        )

    return reasons, {
        "matches": int(parity.get("matches", 0)),
        "result_count": len(results),
        "vertex_buffer_pointer": _norm_ptr(vb_rows[0].get("runtime_buffer_pointer")) if len(vb_rows) == 1 else None,
        "index_buffer_pointers": sorted(observed_ptrs),
        "index_buffer_sizes": sorted(observed_sizes),
    }


def build_report(
    geometry: Mapping[str, Any],
    parity: Mapping[str, Any],
) -> dict[str, Any]:
    geometry_reasons, geometry_summary = _check_geometry(geometry)
    parity_reasons, parity_summary = _check_parity(parity)
    reasons = list(dict.fromkeys(geometry_reasons + parity_reasons))
    ready = not reasons
    return {
        "format": FORMAT,
        "status": "proven" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": reasons,
        "resource": {
            "path": TARGET_MEB,
            "sha256": TARGET_SHA256,
        },
        "runtime_geometry": geometry_summary,
        "byte_parity": parity_summary,
        "evidence_boundary": {
            "raw_runtime_vb_bytes": "proven" if ready else "not-proven",
            "raw_runtime_ib_bytes": "proven" if ready else "not-proven",
            "meb_byte_parity": "proven" if ready else "not-proven",
            "creation_instance_identity": "proven" if ready else "not-proven",
        },
        "render_consumer_contract": {
            "vertex_buffer": {
                "pointer": TARGET_VB,
                "stride": TARGET_VB_STRIDE,
                "bytes": TARGET_VB_SIZE,
                "vertex_count": TARGET_VERTEX_COUNT,
                "status": "proven" if ready else "blocked",
            },
            "index_buffers": [
                {
                    "triangle_count": triangles,
                    "pointer": pointer,
                    "status": "proven" if ready else "blocked",
                }
                for triangles, pointer in sorted(TARGET_IB_BY_TRIANGLES.items())
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote BMW runtime geometry and direct byte parity into one proof contract")
    parser.add_argument("geometry")
    parser.add_argument("parity")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = build_report(_json(args.geometry), _json(args.parity))
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
