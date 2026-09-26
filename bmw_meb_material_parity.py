#!/usr/bin/env python3
"""Validate MEB primitive material references against a retail SHIFT BFF.

The gate proves only resource identity: each MEB .mtx reference must map to one
same-directory .bmt entry in the supplied archive. It does not infer material
parameters, shaders or textures from the binary BMT payload.
"""
from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWM3MEBPrimitiveMaterialParity/1"
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
REC_SIZE = 42
NAME_REC_SIZE = 16
HEADER_RECORDS_OFFSET = 0x130
NAME_BASE_OFFSET = 0x438


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def load_bff_entries(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    if len(data) < NAME_BASE_OFFSET or data[:4] not in (b" KAP", b"PAK "):
        raise ValueError(f"not a SHIFT BFF/PAK archive: {path}")

    file_count = struct.unpack_from("<I", data, 8)[0]
    x118 = struct.unpack_from("<I", data, 0x118)[0]
    x120 = struct.unpack_from("<I", data, 0x120)[0] - 0x308
    if x118 != file_count * REC_SIZE:
        raise ValueError("BFF record-table size mismatch")

    name_base = NAME_BASE_OFFSET + x118
    name_end = name_base + x120
    if name_end > len(data):
        raise ValueError("BFF name table exceeds archive")

    entries: list[dict[str, Any]] = []
    for index in range(file_count):
        record = HEADER_RECORDS_OFFSET + index * REC_SIZE
        offset = struct.unpack_from("<Q", data, record + 8)[0]
        compressed_size = struct.unpack_from("<I", data, record + 16)[0]
        uncompressed_size = struct.unpack_from("<I", data, record + 20)[0]
        entry_type = data[record + 32]
        name_offset = struct.unpack_from("<Q", data, name_base + index * NAME_REC_SIZE)[0]
        if not name_base <= name_offset < name_end:
            raise ValueError(f"BFF entry {index} has invalid name offset")
        name_length = data[name_offset]
        name = data[name_offset + 1:name_offset + 1 + name_length].decode(
            "utf-8", "replace"
        ).replace("\\", "/")
        if offset + compressed_size > len(data):
            raise ValueError(f"BFF entry {index} data range exceeds archive")
        entries.append({
            "index": index,
            "path": name,
            "normalized_path": _norm(name),
            "type": entry_type,
            "compressed_size": compressed_size,
            "uncompressed_size": uncompressed_size,
        })
    return entries


def load_meb_document(path: Path) -> tuple[str, str, list[dict[str, Any]]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    golden = doc.get("golden") if isinstance(doc.get("golden"), Mapping) else {}
    mesh = doc.get("mesh") if isinstance(doc.get("mesh"), Mapping) else doc

    resource = _norm(str(
        golden.get("resource") or doc.get("resource") or TARGET_RESOURCE
    ))
    resource_sha = str(
        golden.get("resource_sha256")
        or doc.get("resource_sha256")
        or doc.get("source_sha256")
        or TARGET_SHA256
    ).lower()

    primitives = list(mesh.get("primitives") or [])
    if not primitives:
        raise ValueError("MEB document has no primitives")

    rows = []
    for index, primitive in enumerate(primitives):
        material = str(primitive.get("material") or "").replace("\\", "/")
        if not material.lower().endswith(".mtx"):
            raise ValueError(
                f"primitive {index} material is not .mtx: {material}"
            )
        index_count = int(primitive.get("index_count", 0))
        if index_count <= 0 or index_count % 3:
            raise ValueError(
                f"primitive {index} has invalid index_count: {index_count}"
            )
        rows.append({
            "index": index,
            "material": material,
            "expected_bmt": material[:-4] + ".bmt",
            "triangle_count": index_count // 3,
            "index_count": index_count,
        })

    return resource, resource_sha, rows


def build_report(meb_path: Path, bff_path: Path) -> dict[str, Any]:
    resource, resource_sha, primitives = load_meb_document(meb_path)
    blockers = []

    if resource != _norm(TARGET_RESOURCE):
        blockers.append("material:unexpected-target-resource")
    if resource_sha != TARGET_SHA256:
        blockers.append("material:unexpected-target-sha256")

    entries = load_bff_entries(bff_path)
    by_path: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_path.setdefault(entry["normalized_path"], []).append(entry)

    correlations = []
    for primitive in primitives:
        matches = by_path.get(_norm(primitive["expected_bmt"]), [])
        if len(matches) != 1:
            blockers.append(
                f"material:bmt-entry-count:{primitive['index']}:{len(matches)}"
            )
            correlations.append({
                **primitive,
                "status": "missing" if not matches else "ambiguous",
                "bff_entries": matches[:4],
            })
            continue

        entry = matches[0]
        if entry["type"] != 2:
            blockers.append(
                f"material:bmt-entry-type:{primitive['index']}:{entry['type']}"
            )
        correlations.append({
            **primitive,
            "status": "match",
            "bff_entry": entry,
        })

    unique_refs = {_norm(row["expected_bmt"]) for row in primitives}
    unique_matches = {
        _norm(row["bff_entry"]["path"])
        for row in correlations
        if row.get("status") == "match"
    }
    if unique_refs != unique_matches:
        blockers.append("material:unique-bmt-reference-set-mismatch")

    counts = Counter(_norm(row["expected_bmt"]) for row in primitives)
    blockers = list(dict.fromkeys(blockers))

    return {
        "format": FORMAT,
        "status": "match" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": blockers,
        "resource": {
            "path": resource,
            "sha256": resource_sha,
        },
        "archive": bff_path.name,
        "primitive_count": len(primitives),
        "unique_material_reference_count": len(unique_refs),
        "material_reference_use_count": dict(sorted(counts.items())),
        "primitive_correlations": correlations,
        "boundary": {
            "identity_only": True,
            "bmt_payload_decoded": False,
            "shader_texture_semantics_proven": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("meb", type=Path, help="MEB/golden JSON")
    ap.add_argument("bff", type=Path, help="retail SHIFT BFF")
    ap.add_argument("output", type=Path)
    args = ap.parse_args(argv)

    report = build_report(args.meb, args.bff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
