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





def _dds_base_level_payload(dds_bytes: bytes) -> tuple[bytes, str]:
    if len(dds_bytes) < 128 or dds_bytes[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    width = int.from_bytes(dds_bytes[16:20], "little")
    height = int.from_bytes(dds_bytes[12:16], "little")
    fourcc = int.from_bytes(dds_bytes[84:88], "little").to_bytes(4, "little").decode("ascii", "replace").rstrip("\x00")
    rgb_bits = int.from_bytes(dds_bytes[88:92], "little")
    if fourcc in {"DXT1", "DXT3", "DXT5"}:
        block_bytes = {"DXT1": 8, "DXT3": 16, "DXT5": 16}[fourcc]
        blocks_x = max(1, (width + 3) // 4)
        blocks_y = max(1, (height + 3) // 4)
        size = blocks_x * blocks_y * block_bytes
        return dds_bytes[128:128 + size], fourcc
    pf_flags = int.from_bytes(dds_bytes[80:84], "little")
    if not fourcc and (pf_flags & 0x40) and rgb_bits == 32:
        size = width * height * 4
        return dds_bytes[128:128 + size], "RGBA32"
    raise ValueError(f"unsupported DDS base level format: {fourcc or 'RGBA32'}")


def _dds_mip_level_payloads(dds_bytes: bytes) -> tuple[list[bytes], str]:
    if len(dds_bytes) < 128 or dds_bytes[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    width = int.from_bytes(dds_bytes[16:20], "little")
    height = int.from_bytes(dds_bytes[12:16], "little")
    mipmaps = int.from_bytes(dds_bytes[28:32], "little") or 1
    fourcc = (
        int.from_bytes(dds_bytes[84:88], "little")
        .to_bytes(4, "little")
        .decode("ascii", "replace")
        .rstrip("\x00")
    )
    rgb_bits = int.from_bytes(dds_bytes[88:92], "little")
    pf_flags = int.from_bytes(dds_bytes[80:84], "little")
    payload = dds_bytes[128:]
    levels: list[bytes] = []
    offset = 0
    level_width = width
    level_height = height
    for _level in range(mipmaps):
        if fourcc in {"DXT1", "DXT3", "DXT5"}:
            block_bytes = {"DXT1": 8, "DXT3": 16, "DXT5": 16}[fourcc]
            blocks_x = max(1, (level_width + 3) // 4)
            blocks_y = max(1, (level_height + 3) // 4)
            size = blocks_x * blocks_y * block_bytes
        elif not fourcc and (pf_flags & 0x40) and rgb_bits == 32:
            size = level_width * level_height * 4
        else:
            raise ValueError(
                f"unsupported DDS mip format: {fourcc or 'RGBA32'}"
            )
        end = offset + size
        if end > len(payload):
            raise ValueError("DDS mip payload is truncated")
        levels.append(payload[offset:end])
        offset = end
        level_width = max(1, level_width // 2)
        level_height = max(1, level_height // 2)
    return levels, fourcc or "RGBA32"


def compare_raw_payload_chain_to_dds(
    payload_rows: list[Mapping[str, Any]],
    dds_bytes: bytes,
) -> dict[str, Any]:
    expected_levels, source_format = _dds_mip_level_payloads(dds_bytes)
    observed: dict[int, Mapping[str, Any]] = {}
    for row in payload_rows:
        try:
            level = int(row.get("level"))
        except (TypeError, ValueError):
            continue
        if level < 0 or level >= len(expected_levels):
            continue
        existing = observed.get(level)
        if existing is None or int(row.get("event_index", -1)) > int(existing.get("event_index", -1)):
            observed[level] = row

    level_rows = []
    blockers: list[str] = []
    for level in sorted(observed):
        row = observed[level]
        path = Path(str(row.get("payload_path") or ""))
        if not path.is_file():
            item = {
                "level": level,
                "status": "missing",
                "ready": False,
                "payload_path": str(path),
                "blocking_reasons": ["raw-payload:file-not-found"],
            }
        else:
            raw = path.read_bytes()
            expected = expected_levels[level]
            observed_sha = hashlib.sha256(raw).hexdigest()
            expected_sha = hashlib.sha256(expected).hexdigest()
            length_match = len(raw) == len(expected)
            byte_match = raw == expected
            reasons = []
            if not length_match:
                reasons.append(
                    f"raw-payload:length-mismatch:l{level}:{len(raw)}:{len(expected)}"
                )
            if not byte_match:
                reasons.append(
                    f"raw-payload:sha256-mismatch:l{level}:{observed_sha}:{expected_sha}"
                )
            item = {
                "level": level,
                "status": "match" if not reasons else "mismatch",
                "ready": not reasons,
                "payload_path": str(path),
                "observed_byte_size": len(raw),
                "expected_byte_size": len(expected),
                "observed_sha256": observed_sha,
                "expected_sha256": expected_sha,
                "dds_source_format": source_format,
                "blocking_reasons": reasons,
            }
        level_rows.append(item)
        blockers.extend(item.get("blocking_reasons") or [])

    expected_count = len(expected_levels)
    observed_levels = sorted(observed)
    complete = observed_levels == list(range(expected_count))
    ready = bool(level_rows) and not blockers
    return {
        "status": "match" if ready else ("mismatch" if level_rows else "not-observed"),
        "ready": ready,
        "coverage_status": "complete" if complete else ("partial" if level_rows else "none"),
        "expected_level_count": expected_count,
        "observed_level_count": len(observed_levels),
        "observed_levels": observed_levels,
        "missing_levels": [level for level in range(expected_count) if level not in observed],
        "levels": level_rows,
        "blocking_reasons": list(dict.fromkeys(blockers)),
    }


def compare_raw_payload_to_dds(
    payload_path: str | Path,
    dds_bytes: bytes,
) -> dict[str, Any]:
    path = Path(payload_path)
    if not path.is_file():
        return {
            "status": "missing",
            "ready": False,
            "path": str(path),
            "blocking_reasons": ["raw-payload:file-not-found"],
        }
    observed = path.read_bytes()
    expected, source_format = _dds_base_level_payload(dds_bytes)
    observed_sha = hashlib.sha256(observed).hexdigest()
    expected_sha = hashlib.sha256(expected).hexdigest()
    length_match = len(observed) == len(expected)
    byte_match = observed == expected
    reasons = []
    if not length_match:
        reasons.append(f"raw-payload:length-mismatch:{len(observed)}:{len(expected)}")
    if not byte_match:
        reasons.append(f"raw-payload:sha256-mismatch:{observed_sha}:{expected_sha}")
    return {
        "status": "match" if not reasons else "mismatch",
        "ready": not reasons,
        "path": str(path),
        "observed_byte_size": len(observed),
        "expected_byte_size": len(expected),
        "observed_sha256": observed_sha,
        "expected_sha256": expected_sha,
        "dds_source_format": source_format,
        "blocking_reasons": reasons,
    }


def _texture_payload_candidates(
    snapshot: Mapping[str, Any],
    texture_ptr: str,
    creation_event_index: int | None = None,
) -> list[Mapping[str, Any]]:
    rows = []
    for row in snapshot.get("texture_payloads") or []:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("texture_ptr") or "").lower() != str(texture_ptr).lower():
            continue
        if int(row.get("level", -1)) != 0:
            continue
        if row.get("snapshot_status") != "captured":
            continue
        if not row.get("payload_path"):
            continue
        if creation_event_index is not None:
            try:
                if int(row.get("event_index", -1)) <= int(creation_event_index):
                    continue
            except (TypeError, ValueError):
                continue
        rows.append(row)
    return sorted(rows, key=lambda row: int(row.get("event_index", -1)))


def _extract_expected_texture_payloads(primary_bff: str | Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    with BFF(primary_bff) as archive:
        for row in PAINT_TEXTURES:
            hits = [entry for entry in archive.entries if entry.path.lower() == row["path"].lower()]
            if len(hits) != 1:
                raise ValueError(
                    f"expected one DDS entry for {row['path']!r}, found {len(hits)}"
                )
            result[row["parameter"]] = archive.extract_entry(hits[0])
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
    expected_payloads = _extract_expected_texture_payloads(primary_bff)
    rows = []
    blockers = []

    for row in PAINT_TEXTURES:
        expected_row = expected[row["parameter"]]
        binding = _active_texture(snapshot, int(row["register"]))
        pointers = binding.get("texture_ptr") if isinstance(binding, Mapping) else None
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
            elif len(paths) != 1:
                result = {
                    "parameter": row["parameter"],
                    "register": row["register"],
                    "texture_ptr": pointers,
                    "resource_creation_status": binding.get("resource_creation_status"),
                    "status": "ambiguous",
                    "ready": False,
                    "blocking_reasons": [f"runtime:texture-snapshot-ambiguous:s{row['register']}"],
                    "snapshot_paths": paths,
                    "expected": expected_row,
                }
            else:
                comparisons = [compare_snapshot_to_expected(paths[0], expected_row)]
                ready = comparisons[0]["ready"]
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

            creation_event_index = None
            if isinstance(binding.get("resource_creation"), Mapping):
                try:
                    creation_event_index = int(binding["resource_creation"].get("event_index"))
                except (TypeError, ValueError):
                    creation_event_index = None
            payload_candidates = (
                _texture_payload_candidates(snapshot, str(pointers), creation_event_index)
                if pointers
                else []
            )
            if payload_candidates:
                raw_chain = compare_raw_payload_chain_to_dds(
                    payload_candidates,
                    expected_payloads[row["parameter"]],
                )
                result["raw_payload_comparison"] = raw_chain
                result["raw_payload_path"] = raw_chain.get("levels", [{}])[-1].get("payload_path") if raw_chain.get("levels") else None
                if raw_chain["ready"]:
                    result["ready"] = True
                    result["status"] = "match"
                    result["blocking_reasons"] = []
                    result["content_identity_method"] = (
                        "raw-dds-mip-chain-complete"
                        if raw_chain["coverage_status"] == "complete"
                        else "raw-dds-mip-chain-partial"
                    )
                    if raw_chain["coverage_status"] == "partial":
                        result["coverage_status"] = "partial"
                else:
                    result["ready"] = False
                    result["status"] = "mismatch"
                    blockers.extend(raw_chain.get("blocking_reasons") or [])
            elif "comparisons" in result:
                result["content_identity_method"] = "ppm-rgb"
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
            "runtime_to_retail_dds_content": (
                "proven-by-raw-mip-chain-complete"
                if rows
                and all(
                    (row.get("raw_payload_comparison") or {}).get("ready")
                    and (row.get("raw_payload_comparison") or {}).get("coverage_status") == "complete"
                    for row in rows
                    if row.get("raw_payload_comparison") is not None
                )
                and all(row.get("raw_payload_comparison") is not None for row in rows)
                else (
                    "proven-by-raw-mip-chain-partial"
                    if rows
                    and all(
                        (row.get("raw_payload_comparison") or {}).get("ready")
                        for row in rows
                        if row.get("raw_payload_comparison") is not None
                    )
                    and any(row.get("raw_payload_comparison") is not None for row in rows)
                    else ("proven-by-ppm-rgb" if not blockers else "not-proven")
                )
            ),
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
