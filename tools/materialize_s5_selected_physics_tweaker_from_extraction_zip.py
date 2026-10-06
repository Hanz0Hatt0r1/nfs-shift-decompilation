#!/usr/bin/env python3
"""Materialize the selected-session PhysicsTweaker rate from an extracted-tree ZIP.

This adapter accepts the exact kind of ZIP produced after a successful
PHYSICSBOOTFLOW.bff extraction: one `_bff_manifest.csv` plus the decoded tree.
It does not trust ZIP filenames or manifest metadata as proof of the selected
session rate. The ZIP is reduced to the already-supported extracted-tree input
and final admission remains owned by the canonical decoded SHA-256 + unique
`tick rate` materializer.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from materialize_s5_selected_physics_tweaker_from_extraction import (  # noqa: E402
    materialize_from_extraction,
)
from materialize_s5_selected_physics_tweaker_rate import (  # noqa: E402
    _resource_identity,
    render_native_handoff_header,
)

MANIFEST_BASENAME = "_bff_manifest.csv"


def _normalize_zip_member(name: str) -> str:
    """Return a safe portable ZIP member path or reject traversal/absolute paths."""
    raw = name.replace("\\", "/")
    if raw.startswith("/"):
        raise ValueError(f"absolute ZIP member path is not allowed: {name!r}")
    parts: list[str] = []
    for part in PurePosixPath(raw).parts:
        if part in ("", ".", "/"):
            continue
        if part == ".." or ":" in part:
            raise ValueError(f"unsafe ZIP member path: {name!r}")
        parts.append(part)
    if not parts:
        raise ValueError(f"empty ZIP member path: {name!r}")
    return "/".join(parts)


def _candidate_members(
    archive: zipfile.ZipFile,
) -> list[tuple[zipfile.ZipInfo, str]]:
    rows: list[tuple[zipfile.ZipInfo, str]] = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        rows.append((info, _normalize_zip_member(info.filename)))
    if not rows:
        raise ValueError("extraction ZIP contains no files")
    return rows


def _select_bound_members(
    archive: zipfile.ZipFile,
    identity: dict[str, Any],
) -> tuple[zipfile.ZipInfo, str, zipfile.ZipInfo, str]:
    entry = identity.get("entry")
    if not isinstance(entry, dict):
        raise ValueError("selected-session resource identity entry missing")
    expected_rel = str(entry.get("path") or "").replace("\\", "/").strip("/").lower()
    if not expected_rel:
        raise ValueError("selected-session resource identity path missing")

    members = _candidate_members(archive)
    manifests = [
        (info, normalized)
        for info, normalized in members
        if normalized.rsplit("/", 1)[-1].lower() == MANIFEST_BASENAME
    ]
    if len(manifests) != 1:
        raise ValueError(
            "expected exactly one extraction ZIP manifest; "
            f"found {len(manifests)}"
        )

    manifest_info, manifest_normalized = manifests[0]
    if "/" in manifest_normalized:
        prefix = manifest_normalized.rsplit("/", 1)[0] + "/"
    else:
        prefix = ""
    expected_member = prefix + expected_rel

    decoded = [
        (info, normalized)
        for info, normalized in members
        if normalized.lower() == expected_member
    ]
    if len(decoded) != 1:
        raise ValueError(
            "expected exactly one PhysicsTweaker XML in the manifest root; "
            f"found {len(decoded)}"
        )
    decoded_info, decoded_normalized = decoded[0]
    return manifest_info, manifest_normalized, decoded_info, decoded_normalized


def materialize_from_extraction_zip(
    geometry_path: Path,
    cadence_path: Path,
    extraction_zip: Path,
) -> dict[str, Any]:
    identity = _resource_identity(geometry_path)
    with zipfile.ZipFile(extraction_zip, "r") as archive:
        (
            manifest_info,
            manifest_member,
            decoded_info,
            decoded_member,
        ) = _select_bound_members(archive, identity)
        manifest_bytes = archive.read(manifest_info)
        decoded_bytes = archive.read(decoded_info)

    entry = identity["entry"]
    expected_size = int(entry["uncompressed_size"])
    if len(decoded_bytes) != expected_size:
        raise ValueError(
            "PhysicsTweaker ZIP member size mismatch: "
            f"expected {expected_size}, got {len(decoded_bytes)}"
        )

    with tempfile.TemporaryDirectory(prefix="shift-physics-tweaker-") as temp_dir:
        temp = Path(temp_dir)
        extracted_root = temp / "extracted"
        expected_rel = str(entry["path"]).replace("\\", "/").strip("/")
        decoded_path = extracted_root.joinpath(*expected_rel.split("/"))
        decoded_path.parent.mkdir(parents=True, exist_ok=True)
        decoded_path.write_bytes(decoded_bytes)

        manifest_path = temp / MANIFEST_BASENAME
        manifest_path.write_bytes(manifest_bytes)

        # Existing extracted-tree adapter verifies exact manifest metadata and then
        # delegates decoded SHA-256/XML/rate admission to the canonical materializer.
        report = materialize_from_extraction(
            geometry_path,
            cadence_path,
            extracted_root,
            manifest_path,
        )

    verification = report.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("selected-session report verification missing")
    verification["mode"] = "exact-extracted-zip-manifest"
    verification["extraction_manifest"] = manifest_member
    verification["extraction_zip_member_layout_verified_this_run"] = True
    verification["extraction_zip"] = str(extraction_zip)
    verification["extraction_zip_manifest_member"] = manifest_member
    verification["extraction_zip_decoded_member"] = decoded_member
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
    parser.add_argument("--extracted-zip", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--native-handoff-out",
        type=Path,
        help="write the canonical typed C++ selected-rate handoff after validation",
    )
    args = parser.parse_args()

    report = materialize_from_extraction_zip(
        args.geometry_contract,
        args.cadence_contract,
        args.extracted_zip,
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
