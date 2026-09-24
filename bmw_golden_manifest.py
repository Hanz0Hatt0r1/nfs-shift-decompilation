"""Extract a compact, reproducible golden manifest from the supplied MEB corpus ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BMWGoldenAssetManifest/1"
DEFAULT_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
DEFAULT_ARCHIVE = "Pakfiles/Vehicles/BMW_M3_E36.bff"


def iter_resource_rows(bundle: str | Path) -> Iterable[dict[str, Any]]:
    with zipfile.ZipFile(bundle) as zf:
        with zf.open("resources.jsonl", "r") as stream:
            for raw in stream:
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if isinstance(row, dict):
                    yield row


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip("/").lower()


def select_bmw_resource(
    rows: Iterable[dict[str, Any]],
    *,
    resource_path: str = DEFAULT_RESOURCE,
) -> dict[str, Any]:
    wanted = _norm(resource_path)
    for row in rows:
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        resource = source.get("root_relative_path") or row.get("resource")
        if isinstance(resource, str) and _norm(resource) == wanted:
            return row
    raise KeyError(f"BMW resource not found in corpus: {resource_path}")


def build_golden_manifest(row: dict[str, Any], *, source_bundle: str | Path) -> dict[str, Any]:
    source = row.get("source") or {}
    mesh = row.get("mesh") or {}
    descriptors = mesh.get("property_descriptors") or []
    color460 = next((d for d in descriptors if str(d.get("id")) == "460"), None)
    properties = [str(p.get("id")) for p in mesh.get("property_layouts", []) if isinstance(p, dict)]
    if color460 is None or color460.get("words") != [4, 6, 0]:
        raise ValueError("selected BMW resource does not carry the proven COLOR0 descriptor [4,6,0]")
    return {
        "format": FORMAT,
        "golden": {
            "status": "selected",
            "reason": "explicit BMW M3 E36 1.02 corpus resource with deterministic identity and real primitive/material references",
            "archive": source.get("archive") or DEFAULT_ARCHIVE,
            "resource": source.get("root_relative_path"),
            "resource_sha256": source.get("resource_sha256"),
            "resource_size": source.get("resource_size"),
            "entry_index": source.get("entry_index"),
            "entry_compressed_size": source.get("entry_compressed_size"),
            "entry_uncompressed_size": source.get("entry_uncompressed_size"),
        },
        "mesh": {
            "name": mesh.get("name"),
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
            "bbox": mesh.get("bbox"),
            "property_ids": properties,
            "color460_descriptor": color460,
            "skinning": mesh.get("skinning"),
            "primitives": mesh.get("primitives"),
        },
        "provenance": {
            "bundle": Path(source_bundle).name,
            "bundle_resource_id": row.get("id"),
            "collector_version": row.get("collector_version"),
            "raw_row_sha256": hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        },
        "render_requirements": {
            "geometry": "real-MEB",
            "material_chain": "BMT -> FX -> FXO",
            "vertex_semantics": ["POSITION0", "COLOR0", "NORMAL0", "TANGENT0", "BINORMAL0", "TEXCOORD0", "TEXCOORD2", "TEXCOORD3"],
            "runtime_archive_access": False,
        },
    }


def write_manifest(bundle: str | Path, output: str | Path, *, resource_path: str = DEFAULT_RESOURCE) -> dict[str, Any]:
    row = select_bmw_resource(iter_resource_rows(bundle), resource_path=resource_path)
    manifest = build_golden_manifest(row, source_bundle=bundle)
    Path(output).write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract a BMW M3 golden manifest from shift_meb_evidence.zip")
    ap.add_argument("bundle")
    ap.add_argument("output")
    ap.add_argument("--resource", default=DEFAULT_RESOURCE)
    args = ap.parse_args()
    manifest = write_manifest(args.bundle, args.output, resource_path=args.resource)
    print(json.dumps({"format": manifest["format"], **manifest["golden"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
