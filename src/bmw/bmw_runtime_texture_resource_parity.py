"""Classify BMW M3 runtime texture objects against exact retail DDS metadata.

This phase intentionally does not use pointer equality as DDS provenance. It
correlates the pointer with its latest successful D3D9 Create* event before the
target draw, then compares the resulting runtime shape with the exact archive
DDS metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from resource_formats import parse_dds_metadata
from shift_importer import BFF

FORMAT = "SHIFT.BMWM3RuntimeTextureResourceParity/1"

CREATE_TEXTURE_RE = re.compile(
    r"^(?P<call>\d+)\s+IDirect3DDevice9::CreateTexture\("
    r".*?Width = (?P<width>\d+), Height = (?P<height>\d+), "
    r"Levels = (?P<levels>\d+), Usage = (?P<usage>.*?), "
    r"Format = (?P<format>D3DFMT_[A-Za-z0-9_]+), Pool = (?P<pool>D3DPOOL_[A-Za-z0-9_]+), "
    r"ppTexture = &(?P<ptr>0x[0-9A-Fa-f]+),"
)
CREATE_CUBE_RE = re.compile(
    r"^(?P<call>\d+)\s+IDirect3DDevice9::CreateCubeTexture\("
    r".*?EdgeLength = (?P<edge>\d+), Levels = (?P<levels>\d+), "
    r"Usage = (?P<usage>.*?), Format = (?P<format>D3DFMT_[A-Za-z0-9_]+), "
    r"Pool = (?P<pool>D3DPOOL_[A-Za-z0-9_]+), "
    r"ppCubeTexture = &(?P<ptr>0x[0-9A-Fa-f]+),"
)

D3D_TO_DDS = {
    "D3DFMT_DXT1": "DXT1",
    "D3DFMT_DXT3": "DXT3",
    "D3DFMT_DXT5": "DXT5",
    "D3DFMT_A8R8G8B8": "",
    "D3DFMT_X8R8G8B8": "",
}


def _norm_ptr(value: Any) -> str:
    return str(value).strip().lower()


def parse_resource_create_log(text: str) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = CREATE_TEXTURE_RE.match(line)
        if match:
            row = match.groupdict()
            rows.append({
                "call": int(row["call"]),
                "line": line_no,
                "texture_ptr": _norm_ptr(row["ptr"]),
                "resource_type": "texture2d",
                "width": int(row["width"]),
                "height": int(row["height"]),
                "levels": int(row["levels"]),
                "usage": row["usage"].strip(),
                "format": row["format"],
                "pool": row["pool"],
            })
            continue
        match = CREATE_CUBE_RE.match(line)
        if match:
            row = match.groupdict()
            rows.append({
                "call": int(row["call"]),
                "line": line_no,
                "texture_ptr": _norm_ptr(row["ptr"]),
                "resource_type": "cube_texture",
                "width": int(row["edge"]),
                "height": int(row["edge"]),
                "edge_length": int(row["edge"]),
                "levels": int(row["levels"]),
                "usage": row["usage"].strip(),
                "format": row["format"],
                "pool": row["pool"],
            })
    return rows


def latest_create_before(
    creates: list[Mapping[str, Any]],
    pointer: str,
    draw_call: int,
) -> Mapping[str, Any] | None:
    pointer = _norm_ptr(pointer)
    candidates = [
        row for row in creates
        if _norm_ptr(row.get("texture_ptr")) == pointer
        and int(row.get("call", -1)) < draw_call
    ]
    return max(candidates, key=lambda row: int(row["call"]), default=None)


def _static_dds(primary_bff: str | Path, path: str) -> dict[str, Any]:
    with BFF(primary_bff) as archive:
        hits = [entry for entry in archive.entries if entry.path.lower() == path.lower()]
        if len(hits) != 1:
            raise ValueError(f"expected exactly one DDS entry {path!r}, found {len(hits)}")
        entry = hits[0]
        payload = archive.extract_entry(entry)
    metadata = parse_dds_metadata(payload)
    return {
        "path": path,
        "archive": Path(primary_bff).name,
        "entry_index": entry.index,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_size": len(payload),
        "width": int(metadata["width"]),
        "height": int(metadata["height"]),
        "mipmaps": int(metadata["mipmaps"]),
        "fourcc": metadata["fourcc"],
    }


def _shape_status(runtime: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[str, list[str]]:
    reasons = []
    expected_fourcc = str(expected.get("fourcc") or "")
    expected_levels = int(expected["mipmaps"])
    expected_format = D3D_TO_DDS.get(str(runtime.get("format")))
    if int(runtime["width"]) != int(expected["width"]) or int(runtime["height"]) != int(expected["height"]):
        reasons.append("dimensions")
    if int(runtime["levels"]) != expected_levels:
        reasons.append("levels")
    if str(runtime.get("format")) not in D3D_TO_DDS:
        reasons.append("format-unsupported")
    elif expected_format != expected_fourcc:
        reasons.append(f"format:{runtime.get('format')}:{expected_fourcc or 'RGBA32'}")
    return ("match", []) if not reasons else ("mismatch", reasons)


def _material_texture_bindings(material_witness: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in material_witness.get("draws") or []:
        match = row.get("match") or {}
        if match.get("material") != "BMW_M3_E36_PAINT":
            continue
        for binding in match.get("sampler_bindings") or []:
            if isinstance(binding, Mapping) and binding.get("kind") == "material":
                rows.append({
                    "call": int(row["draw"]["call"]),
                    "parameter": binding.get("parameter"),
                    "register": int(binding["register"]),
                    "texture_ptr": binding.get("texture_ptr"),
                })
    return rows


def build_report(
    material_witness: Mapping[str, Any],
    resource_create_log: str,
    primary_bff: str | Path,
) -> dict[str, Any]:
    creates = parse_resource_create_log(resource_create_log)
    expected_by_parameter = {
        "diffuseTexture": "vehicles/textures/common_paint.dds",
        "specularTexture": "vehicles/textures/common_paint_specular.dds",
        "scratchControlTexture": "vehicles/textures/common_blank.dds",
    }
    expected = {
        parameter: _static_dds(primary_bff, path)
        for parameter, path in expected_by_parameter.items()
    }

    rows = []
    for binding in _material_texture_bindings(material_witness):
        parameter = str(binding["parameter"])
        pointer = binding.get("texture_ptr")
        expected_row = expected[parameter]
        runtime = latest_create_before(creates, pointer, int(binding["call"])) if pointer else None
        if runtime is None:
            row = {
                **binding,
                "status": "not-observed",
                "ready": False,
                "classification": "unknown",
                "expected": expected_row,
                "blocking_reasons": ["runtime:create-instance-not-observed-before-draw"],
            }
        else:
            shape_status, mismatches = _shape_status(runtime, expected_row)
            classification = (
                "direct-dds-compatible"
                if shape_status == "match"
                else "generated-or-transformed-candidate"
            )
            row = {
                **binding,
                "runtime_create": dict(runtime),
                "status": shape_status,
                "ready": shape_status == "match",
                "classification": classification,
                "shape_mismatches": mismatches,
                "expected": expected_row,
                "blocking_reasons": [],
            }
            if mismatches:
                row["blocking_reasons"] = [
                    "runtime:shape-does-not-match-static-dds:" + ",".join(mismatches)
                ]
        rows.append(row)

    unique = {}
    for row in rows:
        unique.setdefault((row["parameter"], row.get("texture_ptr")), row)
    return {
        "format": FORMAT,
        "status": "match" if rows and all(row["ready"] for row in rows) else (
            "partial" if rows else "not-found"
        ),
        "ready": bool(rows) and all(row["ready"] for row in rows),
        "material": "BMW_M3_E36_PAINT",
        "resource": {
            "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
        },
        "draw_binding_count": len(rows),
        "unique_binding_count": len(unique),
        "rows": rows,
        "summary": {
            "direct_dds_compatible_count": sum(
                1 for row in rows if row.get("classification") == "direct-dds-compatible"
            ),
            "generated_or_transformed_candidate_count": sum(
                1 for row in rows if row.get("classification") == "generated-or-transformed-candidate"
            ),
            "unobserved_count": sum(1 for row in rows if row.get("classification") == "unknown"),
        },
        "blocking_reasons": list(dict.fromkeys(
            reason
            for row in rows
            for reason in row.get("blocking_reasons") or []
        )),
        "boundary": {
            "pointer_to_creation_instance": "proven" if rows and all("runtime_create" in row for row in rows) else "partial",
            "creation_shape_to_static_dds": "proven" if rows and all(row["status"] == "match" for row in rows) else "partial",
            "runtime_pixel_content_identity": "not-observed",
            "dds_alpha_identity": "not-proven",
        },
    }


def validate_report(report: Mapping[str, Any]) -> list[str]:
    reasons = []
    if report.get("format") != FORMAT:
        reasons.append("format:invalid")
    if report.get("material") != "BMW_M3_E36_PAINT":
        reasons.append("material:unexpected")
    if report.get("draw_binding_count") != 12:
        reasons.append(f"draw-binding-count:expected-12:observed-{report.get('draw_binding_count')}")
    parameters = [row.get("parameter") for row in report.get("rows") or []]
    if set(parameters) != {"diffuseTexture", "specularTexture", "scratchControlTexture"}:
        reasons.append("material-parameters:incomplete")
    return list(dict.fromkeys(reasons))


def validate_files(material_witness_path: str | Path, resource_log_path: str | Path, primary_bff: str | Path) -> dict[str, Any]:
    material = json.loads(Path(material_witness_path).read_text(encoding="utf-8"))
    resource_log = Path(resource_log_path).read_text(encoding="utf-8")
    report = build_report(material, resource_log, primary_bff)
    report["source"] = {
        "material_witness": str(material_witness_path),
        "resource_create_log": str(resource_log_path),
        "resource_create_log_sha256": hashlib.sha256(resource_log.encode()).hexdigest(),
        "primary_bff": str(primary_bff),
    }
    reasons = validate_report(report)
    report["validation"] = {
        "status": "match" if not reasons else "blocked",
        "ready": not reasons,
        "blocking_reasons": reasons,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate BMW paint runtime texture objects with retail DDS metadata")
    parser.add_argument("material_witness")
    parser.add_argument("resource_create_log")
    parser.add_argument("primary_bff")
    parser.add_argument("output")
    args = parser.parse_args()
    report = validate_files(args.material_witness, args.resource_create_log, args.primary_bff)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "summary": report["summary"],
        "validation": report["validation"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
