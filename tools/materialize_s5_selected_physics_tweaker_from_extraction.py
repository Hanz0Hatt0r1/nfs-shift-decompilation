#!/usr/bin/env python3
"""Materialize the selected-session PhysicsTweaker rate from an extracted BFF tree.

This adapter consumes the manifest schema emitted by the standalone BFF extractor
used for PHYSICSBOOTFLOW.bff and then delegates semantic/hash admission to the
canonical selected-session rate materializer. Manifest metadata can prove that
the expected entry was extracted, but it never substitutes for the pinned decoded
SHA-256: the decoded XML bytes still have to pass the canonical hash and unique
`tick rate` checks before a positive handoff can be emitted.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from materialize_s5_selected_physics_tweaker_rate import (  # noqa: E402
    _resource_identity,
    materialize,
    render_native_handoff_header,
)

# Exact values observed in the supplied successful PHYSICSBOOTFLOW extraction
# manifest for the already hash-locked entry 49. These are supporting extraction
# identity checks only; none of them replace the canonical decoded SHA-256 gate.
EXPECTED_OFFSET = 0x31800
EXPECTED_METHOD = "xmem/lzx:1frame(s)"
EXPECTED_CRC_FIELD = 0xA0F8C093


def _normalize_resource_path(value: str) -> str:
    return value.replace("\\", "/").strip().lower()


def _manifest_int(row: dict[str, str], field: str) -> int:
    raw = row.get(field)
    if raw is None or not raw.strip():
        raise ValueError(f"extraction manifest field missing: {field}")
    try:
        return int(raw.strip(), 0)
    except ValueError as exc:
        raise ValueError(
            f"extraction manifest field {field} is not an integer: {raw!r}"
        ) from exc


def _read_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("extraction manifest has no header")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("extraction manifest has no entries")
    return rows


def resolve_extracted_entry(
    extracted_root: Path,
    manifest_path: Path,
    identity: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Validate the extractor manifest row and resolve the exact decoded entry."""
    entry = identity.get("entry")
    if not isinstance(entry, dict):
        raise ValueError("selected-session resource identity entry missing")

    expected_index = int(entry["index"])
    expected_path = _normalize_resource_path(str(entry["path"]))
    expected_compressed_size = int(entry["compressed_size"])
    expected_uncompressed_size = int(entry["uncompressed_size"])
    expected_type = int(entry["compression_type"])

    matches: list[dict[str, str]] = []
    for row in _read_manifest_rows(manifest_path):
        try:
            row_index = _manifest_int(row, "index")
        except ValueError:
            continue
        row_name = _normalize_resource_path(row.get("name") or "")
        if row_index == expected_index and row_name == expected_path:
            matches.append(row)

    if len(matches) != 1:
        raise ValueError(
            "expected exactly one extraction manifest row for "
            f"entry {expected_index} {expected_path}; found {len(matches)}"
        )

    row = matches[0]
    actual = {
        "index": _manifest_int(row, "index"),
        "path": _normalize_resource_path(row.get("name") or ""),
        "compression_type": _manifest_int(row, "type"),
        "compressed_size": _manifest_int(row, "compressed_size"),
        "uncompressed_size": _manifest_int(row, "size"),
    }
    expected = {
        "index": expected_index,
        "path": expected_path,
        "compression_type": expected_type,
        "compressed_size": expected_compressed_size,
        "uncompressed_size": expected_uncompressed_size,
    }
    if actual != expected:
        raise ValueError(
            "PhysicsTweaker extraction manifest metadata mismatch: "
            f"expected {expected}, got {actual}"
        )

    status = (row.get("status") or "").strip().lower()
    if status != "ok":
        raise ValueError(
            f"PhysicsTweaker extraction manifest status is not ok: {status!r}"
        )

    offset = _manifest_int(row, "offset")
    if offset != EXPECTED_OFFSET:
        raise ValueError(
            "PhysicsTweaker extraction manifest offset drift: "
            f"expected 0x{EXPECTED_OFFSET:x}, got 0x{offset:x}"
        )

    method = (row.get("method") or "").strip().lower()
    if method != EXPECTED_METHOD:
        raise ValueError(
            "PhysicsTweaker extraction manifest method drift: "
            f"expected {EXPECTED_METHOD!r}, got {method!r}"
        )

    crc_field = _manifest_int(row, "crc_field")
    if crc_field != EXPECTED_CRC_FIELD:
        raise ValueError(
            "PhysicsTweaker extraction manifest CRC field drift: "
            f"expected 0x{EXPECTED_CRC_FIELD:08x}, got 0x{crc_field:08x}"
        )

    extension = (row.get("extension_field") or "").strip().lower()
    if extension and extension != "xml":
        raise ValueError(
            "PhysicsTweaker extraction manifest extension drift: "
            f"{extension!r}"
        )

    decoded_path = extracted_root.joinpath(*expected_path.split("/"))
    if not decoded_path.is_file():
        raise ValueError(
            "extracted PhysicsTweaker XML missing at manifest-resolved path: "
            f"{decoded_path}"
        )

    return decoded_path, {
        "entry_index": expected_index,
        "entry_path": expected_path,
        "offset": f"0x{offset:x}",
        "compression_type": expected_type,
        "compressed_size": expected_compressed_size,
        "uncompressed_size": expected_uncompressed_size,
        "method": method,
        "status": status,
        "crc_field": f"0x{crc_field:08x}",
    }


def materialize_from_extraction(
    geometry_path: Path,
    cadence_path: Path,
    extracted_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    identity = _resource_identity(geometry_path)
    decoded_path, manifest_entry = resolve_extracted_entry(
        extracted_root,
        manifest_path,
        identity,
    )

    # Canonical materialize() performs the cryptographic decoded-payload check,
    # XML parsing, unique-property check, uint16-domain admission and cadence join.
    report = materialize(
        geometry_path,
        cadence_path,
        decoded_entry_path=decoded_path,
    )
    verification = report.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("canonical selected-session report verification missing")
    verification["mode"] = "exact-extracted-entry-manifest"
    verification["extraction_manifest_verified_this_run"] = True
    verification["extraction_manifest"] = str(manifest_path)
    verification["extraction_manifest_entry"] = manifest_entry
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometry-contract",
        type=Path,
        default=ROOT / "evidence/bmw_offset33b_selector_geometry_inputs.json",
    )
    parser.add_argument(
        "--cadence-contract",
        type=Path,
        default=ROOT / "evidence/s5_retail_outer_update_cadence.json",
    )
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--native-handoff-out",
        type=Path,
        help="write the canonical typed C++ selected-rate handoff after validation",
    )
    args = parser.parse_args()

    report = materialize_from_extraction(
        args.geometry_contract,
        args.cadence_contract,
        args.extracted_root,
        args.manifest,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    elif not args.native_handoff_out:
        print(rendered, end="")

    if args.native_handoff_out:
        args.native_handoff_out.parent.mkdir(parents=True, exist_ok=True)
        args.native_handoff_out.write_text(
            render_native_handoff_header(report), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
