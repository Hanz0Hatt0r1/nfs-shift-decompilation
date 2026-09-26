"""Compare captured D3D9 texture snapshots against exact retail DDS content.

PPM snapshots preserve RGB only. Therefore PPM-backed matches prove exact RGB8
content plus dimensions, while alpha is explicitly reported as unobserved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_material_from_bff import TARGET_MEB
from runtime_texture_reference import ppm_to_reference_texture
from shift_importer import BFF
from texture_reference import decode_dds, image_hash

FORMAT = "SHIFT.RuntimeTextureContentParity/1"
BMW_PAINT_MATERIAL = "BMW_M3_E36_PAINT"

PAINT_TEXTURES = (
    {
        "parameter": "diffuseTexture",
        "register": 1,
        "path": "vehicles/textures/common_paint.dds",
    },
    {
        "parameter": "specularTexture",
        "register": 2,
        "path": "vehicles/textures/common_paint_specular.dds",
    },
    {
        "parameter": "scratchControlTexture",
        "register": 4,
        "path": "vehicles/textures/common_blank.dds",
    },
)


def _rgb_bytes(image: Mapping[str, Any]) -> bytes:
    pixels = bytes(int(x) & 0xFF for x in image.get("pixels") or [])
    if len(pixels) % 4:
        raise ValueError("reference texture pixels must be RGBA8")
    return bytes(pixels[index] for index in range(len(pixels)) if index % 4 != 3)


def _rgb_sha256(image: Mapping[str, Any]) -> str:
    return hashlib.sha256(_rgb_bytes(image)).hexdigest()


def _find_draw_snapshot(runtime_report: Mapping[str, Any], frame: int, draw_index: int) -> Mapping[str, Any]:
    for current_frame in runtime_report.get("frames") or []:
        if not isinstance(current_frame, Mapping) or current_frame.get("frame") != frame:
            continue
        for snapshot in current_frame.get("draw_snapshots") or []:
            if isinstance(snapshot, Mapping) and snapshot.get("draw_index") == draw_index:
                return snapshot
    raise ValueError(f"draw snapshot {frame}:{draw_index} not found")


def _active_texture(snapshot: Mapping[str, Any], register: int) -> Mapping[str, Any] | None:
    for row in snapshot.get("active_texture_bindings") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            stage = int(row.get("stage"))
        except (TypeError, ValueError):
            continue
        if stage == register:
            return row
    return None


def _load_snapshot(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".ppm":
        return ppm_to_reference_texture(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"snapshot must be a JSON object: {path}")
    return value


def _extract_expected_textures(primary_bff: str | Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with BFF(primary_bff) as archive:
        for row in PAINT_TEXTURES:
            hits = [entry for entry in archive.entries if entry.path.lower() == row["path"].lower()]
            if len(hits) != 1:
                raise ValueError(
                    f"expected one DDS entry for {row['path']!r}, found {len(hits)}"
                )
            entry = hits[0]
            payload = archive.extract_entry(entry)
            image = decode_dds(payload)
            result[row["parameter"]] = {
                **row,
                "archive": archive.path.name,
                "entry_index": entry.index,
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "source_size": len(payload),
                "width": int(image["width"]),
                "height": int(image["height"]),
                "decoded_rgba_sha256": image_hash(image),
                "decoded_rgb_sha256": _rgb_sha256(image),
                "decoded_alpha_observable": True,
            }
    return result


def compare_snapshot_to_expected(snapshot_path: str | Path, expected: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(snapshot_path)
    if not path.is_file():
        return {
            "status": "missing",
            "ready": False,
            "path": str(path),
            "blocking_reasons": ["snapshot:file-not-found"],
        }
    observed = _load_snapshot(path)
    observed_width = int(observed.get("width", 0))
    observed_height = int(observed.get("height", 0))
    expected_width = int(expected["width"])
    expected_height = int(expected["height"])
    observed_rgb = _rgb_sha256(observed)
    size_match = observed_width == expected_width and observed_height == expected_height
    rgb_match = observed_rgb == expected["decoded_rgb_sha256"]
    source_format = str(observed.get("source_format") or "")
    alpha_status = (
        "not-observed"
        if source_format == "D3D9_CAPTURE_PPM"
        else "observed-in-reference-resource"
    )
    reasons = []
    if not size_match:
        reasons.append(
            f"snapshot:dimensions-mismatch:{observed_width}x{observed_height}:"
            f"{expected_width}x{expected_height}"
        )
    if not rgb_match:
        reasons.append(
            f"snapshot:rgb-content-mismatch:{observed_rgb}:{expected['decoded_rgb_sha256']}"
        )
    return {
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "path": str(path),
        "observed_width": observed_width,
        "observed_height": observed_height,
        "expected_width": expected_width,
        "expected_height": expected_height,
        "observed_rgb_sha256": observed_rgb,
        "expected_rgb_sha256": expected["decoded_rgb_sha256"],
        "observed_rgba_sha256": (
            image_hash(observed)
            if source_format != "D3D9_CAPTURE_PPM"
            else None
        ),
        "source_format": source_format,
        "alpha_status": alpha_status,
        "blocking_reasons": reasons,
    }


def build_bmw_paint_runtime_texture_parity(
    runtime_report: Mapping[str, Any],
    *,
    frame: int,
    draw_index: int,
    primary_bff: str | Path,
) -> dict[str, Any]:
    snapshot = _find_draw_snapshot(runtime_report, frame, draw_index)
    expected = _extract_expected_textures(primary_bff)
    rows = []
    blockers = []

    for row in PAINT_TEXTURES:
        expected_row = expected[row["parameter"]]
        binding = _active_texture(snapshot, int(row["register"]))
        if binding is None:
            result = {
                "parameter": row["parameter"],
                "register": row["register"],
                "status": "not-observed",
                "ready": False,
                "blocking_reasons": [f"runtime:sampler-stage-missing:s{row['register']}"],
                "expected": expected_row,
            }
        else:
            pointers = binding.get("texture_ptr")
            paths = list(binding.get("snapshot_paths") or [])
            if not pointers:
                result = {
                    "parameter": row["parameter"],
                    "register": row["register"],
                    "texture_ptr": pointers,
                    "status": "not-observed",
                    "ready": False,
                    "blocking_reasons": [f"runtime:texture-object-not-bound:s{row['register']}"],
                    "expected": expected_row,
                }
            elif not paths:
                result = {
                    "parameter": row["parameter"],
                    "register": row["register"],
                    "texture_ptr": pointers,
                    "resource_creation_status": binding.get("resource_creation_status"),
                    "status": "blocked",
                    "ready": False,
                    "blocking_reasons": [f"runtime:texture-snapshot-not-supplied:s{row['register']}"],
                    "expected": expected_row,
                }
            else:
                comparisons = [
                    compare_snapshot_to_expected(path, expected_row)
                    for path in paths
                ]
                ready = any(item["ready"] for item in comparisons)
                result = {
                    "parameter": row["parameter"],
                    "register": row["register"],
                    "texture_ptr": pointers,
                    "resource_creation_status": binding.get("resource_creation_status"),
                    "status": "match" if ready else "mismatch",
                    "ready": ready,
                    "comparisons": comparisons,
                    "expected": expected_row,
                }
        rows.append(result)
        blockers.extend(result.get("blocking_reasons") or [])

    return {
        "format": FORMAT,
        "status": "match" if not blockers else "blocked",
        "ready": not blockers,
        "material": BMW_PAINT_MATERIAL,
        "resource": {
            "path": TARGET_MEB,
        },
        "draw": {
            "frame": frame,
            "draw_index": draw_index,
        },
        "texture_count": len(rows),
        "matched_texture_count": sum(1 for row in rows if row.get("ready")),
        "textures": rows,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "boundary": {
            "runtime_pointer_to_creation_instance": "consumed-when-present",
            "runtime_to_retail_dds_rgb_content": "proven" if not blockers else "not-proven",
            "runtime_to_retail_dds_alpha": "not-observed-for-ppm",
        },
    }


def validate_report(report: Mapping[str, Any]) -> list[str]:
    reasons = []
    if report.get("format") != FORMAT:
        reasons.append("format:invalid")
    if report.get("material") != BMW_PAINT_MATERIAL:
        reasons.append("material:unexpected")
    if report.get("texture_count") != 3:
        reasons.append("texture-count:expected-3")
    if report.get("matched_texture_count") != 3:
        reasons.append("texture-content:all-three-not-proven")
    return list(dict.fromkeys(reasons))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare BMW M3 runtime texture snapshots against retail DDS")
    parser.add_argument("runtime_report")
    parser.add_argument("primary_bff")
    parser.add_argument("frame", type=int)
    parser.add_argument("draw_index", type=int)
    parser.add_argument("output")
    args = parser.parse_args()

    runtime = json.loads(Path(args.runtime_report).read_text(encoding="utf-8"))
    report = build_bmw_paint_runtime_texture_parity(
        runtime,
        frame=args.frame,
        draw_index=args.draw_index,
        primary_bff=args.primary_bff,
    )
    report["validation"] = {
        "status": "match" if not validate_report(report) else "blocked",
        "ready": not validate_report(report),
        "blocking_reasons": validate_report(report),
    }
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "validation": report["validation"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
