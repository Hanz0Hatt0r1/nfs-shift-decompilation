#!/usr/bin/env python3
"""Build reproducible BMW M3 runtime-buffer candidates from the retail MEB.

The output is deliberately a candidate artifact, not a claim of raw D3D9
runtime byte identity. Vertex data is packed in the deterministic
MEB-property-order interleaved layout used by VertexLayout/1, while the source
property payload bytes are copied without float re-encoding or color conversion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

from meb_format import MEBMesh, read_meb
from shift_importer_v3_reference import BFF
from vertex_layout import build_layout_from_summary

FORMAT = "SHIFT.BMWM3RuntimeBufferArtifacts/1"
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_unique_entry(archive: BFF, logical_path: str):
    target = logical_path.replace("\\", "/").strip("/").lower()
    matches = [
        entry for entry in archive.entries
        if entry.path.replace("\\", "/").strip("/").lower() == target
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one BFF entry for {logical_path!r}, found {len(matches)}"
        )
    return matches[0]


def extract_meb_from_bff(
    bff_path: str | Path,
    logical_path: str = TARGET_RESOURCE,
) -> tuple[bytes, Mapping[str, Any]]:
    with BFF(bff_path) as archive:
        entry = find_unique_entry(archive, logical_path)
        data = archive.extract_entry(entry)
        if len(data) != entry.uncompressed_size:
            raise ValueError(
                f"{logical_path}: decoded size {len(data)} != {entry.uncompressed_size}"
            )
        digest = sha256_bytes(data)
        if logical_path.replace("\\", "/").strip("/").lower() == TARGET_RESOURCE and digest != TARGET_SHA256:
            raise ValueError(
                f"{logical_path}: SHA-256 mismatch {digest} != {TARGET_SHA256}"
            )
        provenance = {
            "archive": archive.path.name,
            "entry_index": entry.index,
            "path": entry.path,
            "offset": entry.offset,
            "compressed_size": entry.compressed_size,
            "uncompressed_size": entry.uncompressed_size,
            "type": entry.type,
            "sha256": digest,
        }
        return data, provenance


def _layout_rows(mesh: MEBMesh) -> list[dict[str, Any]]:
    rows = [dict(row) for row in mesh.property_layouts]
    if not rows:
        raise ValueError("MEB has no property_layouts")

    seen: set[str] = set()
    for row in rows:
        pid = str(row.get("id") or "")
        if not pid or pid in seen:
            raise ValueError(f"invalid or duplicate MEB property id: {row!r}")
        seen.add(pid)
        try:
            payload_offset = int(row["payload_offset"])
            stride = int(row["stride"])
            byte_count = int(row["bytes"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"incomplete MEB property layout: {row!r}") from exc
        expected = mesh.vertex_count * stride
        if payload_offset < 0 or stride <= 0 or byte_count != expected:
            raise ValueError(f"invalid MEB property byte range: {row!r}")
        row["payload_offset"] = payload_offset
        row["stride"] = stride
        row["bytes"] = byte_count
    return rows


def pack_interleaved_vertex_bytes(meb_bytes: bytes, mesh: MEBMesh) -> bytes:
    """Interleave raw MEB property payloads without changing any source byte."""
    rows = _layout_rows(mesh)
    stride = sum(int(row["stride"]) for row in rows)
    output = bytearray(mesh.vertex_count * stride)

    for vertex_index in range(mesh.vertex_count):
        dst = vertex_index * stride
        cursor = dst
        for row in rows:
            src = int(row["payload_offset"]) + vertex_index * int(row["stride"])
            end = src + int(row["stride"])
            if end > len(meb_bytes):
                raise ValueError(
                    f"MEB property {row['id']} exceeds resource at vertex {vertex_index}"
                )
            payload = meb_bytes[src:end]
            output[cursor:cursor + len(payload)] = payload
            cursor += len(payload)
        if cursor != dst + stride:
            raise AssertionError("vertex interleave cursor mismatch")
    return bytes(output)


def pack_uint16_index_buffers(mesh: MEBMesh) -> tuple[bytes, list[bytes]]:
    """Return the complete uint16 index stream and one exact buffer per primitive."""
    all_bytes = bytearray()
    per_primitive: list[bytes] = []
    for primitive in mesh.primitives:
        start = int(primitive.first_index)
        count = int(primitive.index_count)
        indices = mesh.indices[start:start + count]
        if len(indices) != count:
            raise ValueError(
                f"primitive {len(per_primitive)} index range is truncated: "
                f"start={start} count={count}"
            )
        if any(index < 0 or index > 0xFFFF for index in indices):
            raise ValueError("INDEX16 candidate contains an out-of-range vertex index")
        payload = struct.pack(f"<{count}H", *indices)
        per_primitive.append(payload)
        all_bytes.extend(payload)
    if len(all_bytes) != len(mesh.indices) * 2:
        raise AssertionError("full INDEX16 byte count mismatch")
    return bytes(all_bytes), per_primitive


def build_artifact_report(
    meb_bytes: bytes,
    *,
    source: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes, bytes, list[bytes]]:
    source = dict(source or {})
    mesh = read_meb(meb_bytes)
    summary = {
        "resource": source.get("path", TARGET_RESOURCE),
        "sha256": sha256_bytes(meb_bytes),
        "vertex_count": mesh.vertex_count,
        "property_ids": [str(row["id"]) for row in _layout_rows(mesh)],
        "vertex_stride": sum(int(row["stride"]) for row in _layout_rows(mesh)),
        "triangle_count": mesh.triangle_count,
        "primitive_count": len(mesh.primitives),
    }

    layout = build_layout_from_summary({
        "vertex_properties": _layout_rows(mesh),
    })
    if layout.get("buffer_mode") != "interleaved-repack":
        raise ValueError("VertexLayout did not select interleaved repack mode")
    if int(layout.get("buffer_stride", -1)) != summary["vertex_stride"]:
        raise ValueError(
            f"VertexLayout stride {layout.get('buffer_stride')} "
            f"!= raw property stride {summary['vertex_stride']}"
        )

    vertex_bytes = pack_interleaved_vertex_bytes(meb_bytes, mesh)
    index_bytes, primitive_bytes = pack_uint16_index_buffers(mesh)

    expected_vb_size = mesh.vertex_count * summary["vertex_stride"]
    expected_ib_size = len(mesh.indices) * 2
    if len(vertex_bytes) != expected_vb_size:
        raise AssertionError("vertex artifact size mismatch")
    if len(index_bytes) != expected_ib_size:
        raise AssertionError("index artifact size mismatch")

    primitive_rows = []
    for index, (primitive, payload) in enumerate(zip(mesh.primitives, primitive_bytes)):
        primitive_rows.append({
            "index": index,
            "material": primitive.material,
            "first_index": primitive.first_index,
            "index_count": primitive.index_count,
            "triangle_count": primitive.index_count // 3,
            "byte_size": len(payload),
            "sha256": sha256_bytes(payload),
            "path": f"index_buffer_{index:02d}.uint16.bin",
        })

    report = {
        "format": FORMAT,
        "status": "match",
        "ready": True,
        "claim_boundary": {
            "status": "candidate",
            "raw_d3d9_runtime_bytes": "not-proven",
            "reason": "MEB payloads are deterministically repacked; Phase 344 runtime capture must prove byte identity",
        },
        "source": {
            **source,
            "path": source.get("path", TARGET_RESOURCE),
            "sha256": sha256_bytes(meb_bytes),
        },
        "mesh": summary,
        "vertex": {
            "format": "MEB-property-order/interleaved",
            "byte_size": len(vertex_bytes),
            "sha256": sha256_bytes(vertex_bytes),
            "attributes": layout.get("attributes", []),
        },
        "index": {
            "format": "INDEX16/little-endian",
            "byte_size": len(index_bytes),
            "sha256": sha256_bytes(index_bytes),
            "primitives": primitive_rows,
        },
    }
    return report, vertex_bytes, index_bytes, primitive_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--resource", default=TARGET_RESOURCE)
    args = parser.parse_args(argv)

    meb_bytes, provenance = extract_meb_from_bff(args.bff, args.resource)
    report, vertex_bytes, index_bytes, primitive_bytes = build_artifact_report(
        meb_bytes,
        source=provenance,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    vertex_path = args.output_dir / "vertex_buffer.meb-order.bin"
    index_path = args.output_dir / "index_buffer.uint16.bin"
    report_path = args.output_dir / "manifest.json"

    vertex_path.write_bytes(vertex_bytes)
    index_path.write_bytes(index_bytes)
    for index, payload in enumerate(primitive_bytes):
        (args.output_dir / f"index_buffer_{index:02d}.uint16.bin").write_bytes(payload)

    report["outputs"] = {
        "vertex_buffer": vertex_path.name,
        "index_buffer": index_path.name,
        "manifest": report_path.name,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
