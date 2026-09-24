#!/usr/bin/env python3
"""Collect the smallest useful evidence bundle for SHIFT MEB 460/461 research.

Usage:
    python3 tools/collect_meb_evidence.py "/path/to/Need for Speed Shift"

The collector scans .meb files directly and .meb entries inside .bff archives.
For every MEB it records structural metadata; for MEBs containing property
460/461 it additionally stores exact descriptor bytes and exact property-payload
bytes, SHA-256 hashes, color ABI candidates, and provenance.

If a recovered SHIFT.exe.c is supplied with --source, a source evidence report
and per-resource exact descriptor-triple proof are also generated.

Only standard-library modules are used by this script itself. Project parsers are
imported from the repository so the collector uses the same MEB/BFF decoders as
the project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from meb_format import MEBError, read_meb, mesh_summary
    from shift_importer import BFF
    from color_abi import build_color_abi_evidence
except ImportError as exc:
    raise SystemExit(
        "Project dependencies are missing. Run this from a checkout of "
        "nfs-shift-decompilation (no pip install is required)."
    ) from exc


FORMAT = "SHIFT.MEBEvidenceBundle/1"
COLLECTOR_VERSION = "112.1"
COLOR_PROPERTIES = ("460", "461")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(*parts: str) -> str:
    material = "\x00".join(parts).encode("utf-8", "replace")
    return hashlib.sha256(material).hexdigest()[:20]


def json_dump(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def discover_files(root: Path) -> tuple[list[Path], list[Path]]:
    direct_mebs: list[Path] = []
    bffs: list[Path] = []
    if root.is_file():
        suffix = root.suffix.lower()
        if suffix == ".meb":
            direct_mebs.append(root)
        elif suffix == ".bff":
            bffs.append(root)
        else:
            raise SystemExit(f"Input must be a directory, .bff or .meb: {root}")
        return sorted(direct_mebs), sorted(bffs)

    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix == ".meb":
                direct_mebs.append(path)
            elif suffix == ".bff":
                bffs.append(path)
        except OSError:
            continue

    return sorted(direct_mebs), sorted(bffs)


def relative_display(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace(os.sep, "/")
    except ValueError:
        return str(path)


def meb_resource_report(
    data: bytes,
    *,
    source_kind: str,
    source_path: str,
    archive_path: str | None = None,
    entry_index: int | None = None,
    entry_compressed_size: int | None = None,
    entry_uncompressed_size: int | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    mesh = read_meb(data)
    summary = mesh_summary(mesh)
    report_id = stable_id(
        source_kind,
        archive_path or "",
        source_path,
        sha256(data),
    )

    evidence: dict[str, bytes] = {}
    color_reports: dict[str, Any] = {}
    color_properties_found: list[str] = []

    descriptors = {
        str(row.get("id")): row
        for row in mesh.property_descriptors
        if isinstance(row, dict)
    }
    layouts = {
        str(row.get("id")): row
        for row in mesh.property_layouts
        if isinstance(row, dict)
    }

    for property_id in COLOR_PROPERTIES:
        descriptor = descriptors.get(property_id)
        layout = layouts.get(property_id)
        if descriptor is None and layout is None:
            continue

        color_properties_found.append(property_id)
        if descriptor is not None:
            raw_hex = descriptor.get("raw_hex")
            if isinstance(raw_hex, str) and len(raw_hex) == 24:
                evidence[f"{property_id}/descriptor.bin"] = bytes.fromhex(raw_hex)

        if layout is not None:
            payload_offset = layout.get("payload_offset")
            payload_length = layout.get("bytes")
            if (
                isinstance(payload_offset, int)
                and isinstance(payload_length, int)
                and payload_offset >= 0
                and payload_length >= 0
                and payload_offset + payload_length <= len(data)
            ):
                payload = data[payload_offset:payload_offset + payload_length]
                evidence[f"{property_id}/payload.bin"] = payload

                field = "colors" if property_id == "460" else "colors2"
                rows = getattr(mesh, field)
                decoded_stream = bytes(
                    component
                    for row in rows
                    for component in row
                )
                color_reports[property_id] = {
                    **build_color_abi_evidence(property_id, payload),
                    "source": {
                        "kind": source_kind,
                        "resource": source_path,
                        "archive": archive_path,
                        "entry_index": entry_index,
                        "resource_sha256": sha256(data),
                        "entry_compressed_size": entry_compressed_size,
                        "entry_uncompressed_size": entry_uncompressed_size,
                        "property_descriptor": descriptor,
                        "descriptor_range": (
                            {
                                "offset": descriptor.get("offset"),
                                "length": 12,
                                "end": int(descriptor.get("offset")) + 12,
                            }
                            if descriptor and isinstance(descriptor.get("offset"), int)
                            else None
                        ),
                        "descriptor_range_status": (
                            "observed"
                            if f"{property_id}/descriptor.bin" in evidence
                            else "not-proven"
                        ),
                        "payload_range": {
                            "offset": payload_offset,
                            "length": payload_length,
                            "end": payload_offset + payload_length,
                        },
                        "payload_range_status": "observed",
                        "payload_raw_bytes_sha256": sha256(payload),
                        "payload_raw_hex": payload.hex(),
                        "decoded_stream_matches_payload": decoded_stream == payload,
                        "decoded_stream_matches_payload_status": (
                            "observed" if decoded_stream == payload else "mismatch"
                        ),
                    },
                }

    report = {
        "format": "SHIFT.MEBEvidenceResource/1",
        "collector_version": COLLECTOR_VERSION,
        "id": report_id,
        "source": {
            "kind": source_kind,
            "root_relative_path": source_path,
            "archive": archive_path,
            "entry_index": entry_index,
            "resource_sha256": sha256(data),
            "resource_size": len(data),
            "entry_compressed_size": entry_compressed_size,
            "entry_uncompressed_size": entry_uncompressed_size,
        },
        "mesh": summary,
        "color_properties_found": color_properties_found,
        "color_reports": color_reports,
    }
    return report, evidence


def collect(args: argparse.Namespace) -> int:
    root = Path(args.input).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Input does not exist: {root}")

    out = Path(args.output).expanduser()
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)

    direct_mebs, bffs = discover_files(root)
    resources: list[dict[str, Any]] = []
    archive_reports: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    evidence_blobs: dict[str, bytes] = {}
    property_counts: Counter[str] = Counter()

    def add_meb(
        data: bytes,
        *,
        source_kind: str,
        source_path: str,
        archive_path: str | None = None,
        entry_index: int | None = None,
        entry_compressed_size: int | None = None,
        entry_uncompressed_size: int | None = None,
    ) -> None:
        try:
            report, evidence = meb_resource_report(
                data,
                source_kind=source_kind,
                source_path=source_path,
                archive_path=archive_path,
                entry_index=entry_index,
                entry_compressed_size=entry_compressed_size,
                entry_uncompressed_size=entry_uncompressed_size,
            )
            resources.append(report)
            for prop in report["mesh"]["vertex_properties"]:
                property_counts[str(prop["id"])] += 1
            if report["color_properties_found"]:
                rid = report["id"]
                for prop, value in report["color_reports"].items():
                    report_path = f"resources/{rid}/{prop}/color_abi.json"
                    evidence_blobs[report_path] = (
                        json.dumps(
                            value,
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        ).encode("utf-8") + b"\n"
                    )
                for name, blob in evidence.items():
                    evidence_blobs[f"resources/{rid}/{name}"] = blob
        except Exception as exc:
            errors.append({
                "source_kind": source_kind,
                "source_path": source_path,
                "archive": archive_path,
                "entry_index": entry_index,
                "error": f"{type(exc).__name__}: {exc}",
            })
            if args.fail_fast:
                raise

    for path in direct_mebs:
        try:
            data = path.read_bytes()
            add_meb(
                data,
                source_kind="direct-meb",
                source_path=relative_display(path, root),
            )
        except Exception as exc:
            errors.append({
                "source_kind": "direct-meb",
                "source_path": relative_display(path, root),
                "error": f"{type(exc).__name__}: {exc}",
            })
            if args.fail_fast:
                raise

    for bff_path in bffs:
        try:
            bff_digest = sha256(bff_path.read_bytes())
            with BFF(bff_path) as bff:
                archive_reports.append({
                    "path": relative_display(bff_path, root),
                    "sha256": bff_digest,
                    "size": bff_path.stat().st_size,
                    "version": bff.version,
                    "file_count": bff.file_count,
                })
                for entry in bff.entries:
                    if not entry.path.lower().endswith(".meb"):
                        continue
                    try:
                        data = bff.extract_entry(entry, type2="lzx")
                        add_meb(
                            data,
                            source_kind="bff-meb",
                            source_path=entry.path,
                            archive_path=relative_display(bff_path, root),
                            entry_index=entry.index,
                            entry_compressed_size=entry.compressed_size,
                            entry_uncompressed_size=entry.uncompressed_size,
                        )
                    except Exception as exc:
                        errors.append({
                            "source_kind": "bff-meb",
                            "source_path": entry.path,
                            "archive": relative_display(bff_path, root),
                            "entry_index": entry.index,
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                        if args.fail_fast:
                            raise
        except Exception as exc:
            errors.append({
                "source_kind": "bff",
                "source_path": relative_display(bff_path, root),
                "error": f"{type(exc).__name__}: {exc}",
            })
            if args.fail_fast:
                raise

    resources.sort(key=lambda row: (
        row["source"]["archive"] or "",
        row["source"]["root_relative_path"],
        row["source"]["entry_index"] if row["source"]["entry_index"] is not None else -1,
    ))

    source_report: dict[str, Any] | None = None
    descriptor_reports: list[dict[str, Any]] = []
    source_path = Path(args.source).expanduser() if args.source else None
    if source_path:
        if not source_path.exists():
            errors.append({
                "source_kind": "SHIFT.exe.c",
                "source_path": str(source_path),
                "error": "source file does not exist",
            })
        else:
            from d3d9_source_evidence import analyze_shift_exe_c_file
            from meb_d3d9_descriptor_triple_evidence import analyze_meb_d3d9_descriptor_triple

            source_report = analyze_shift_exe_c_file(source_path)
            for resource in resources:
                if not resource["color_properties_found"]:
                    continue
                resource_meb = resource["mesh"]
                meb_report = {
                    "format": "SHIFT.MEB",
                    "property_descriptors": resource_meb.get("property_descriptors", []),
                }
                descriptor_report = analyze_meb_d3d9_descriptor_triple(
                    meb_report,
                    source_report,
                )
                descriptor_reports.append({
                    "resource_id": resource["id"],
                    "source": resource["source"],
                    "proof": descriptor_report,
                })

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_metadata = {
        "format": FORMAT,
        "collector_version": COLLECTOR_VERSION,
        "created_utc": timestamp,
        "input_root": str(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "scan": {
            "direct_meb_files": len(direct_mebs),
            "bff_files": len(bffs),
            "meb_resources": len(resources),
            "meb_resources_with_color": sum(
                bool(row["color_properties_found"]) for row in resources
            ),
            "property_occurrences": dict(sorted(property_counts.items())),
            "errors": len(errors),
        },
        "source_evidence": {
            "supplied": source_report is not None,
            "path": str(source_path) if source_path else None,
            "format": source_report.get("format") if source_report else None,
        },
        "next_requested_evidence": [
            "A runtime declaration instance for the same mesh/resource",
            "The D3D9 Usage byte produced from the recovered Usage ordinal table",
            "Same-instance correlation between MEB resource and SetVertexDeclaration path",
        ],
        "privacy": {
            "full_game_files_included": False,
            "included_raw_data": (
                "Only exact 12-byte 460/461 descriptors and their exact color payloads "
                "from matching MEB resources are included."
            ),
        },
    }

    readme = f"""SHIFT MEB evidence bundle
=========================

Collector version: {COLLECTOR_VERSION}
Created (UTC): {timestamp}

Input: {root}

This bundle is intended for reverse-engineering analysis. It contains:
- archives.json: BFF inventory and SHA-256
- resources.jsonl: every parsed MEB resource and mesh/property metadata
- summary.json: scan totals and missing-evidence status
- source_d3d9.json: optional SHIFT.exe.c source evidence
- descriptor_triple_proofs.json: optional per-color-resource MEB [Type, Usage, Channel] proofs
- resources/<id>/460|461/: exact descriptor/payload bytes and color ABI JSON

The bundle does NOT include the original BFF/MEG game archives in full.
"""

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("README.txt", readme)
        zf.writestr("summary.json", json.dumps(bundle_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        zf.writestr(
            "archives.json",
            json.dumps(archive_reports, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        zf.writestr(
            "resources.jsonl",
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in resources
            ),
        )
        zf.writestr(
            "errors.json",
            json.dumps(errors, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        zf.writestr(
            "descriptor_triple_proofs.json",
            json.dumps(descriptor_reports, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        if source_report is not None:
            zf.writestr(
                "source_d3d9.json",
                json.dumps(source_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
        for name, blob in sorted(evidence_blobs.items()):
            zf.writestr(name, blob)

    bundle_sha256 = sha256(out.read_bytes())
    print(json.dumps({
        "bundle": str(out),
        "bundle_sha256": bundle_sha256,
        "format": FORMAT,
        "meb_resources": len(resources),
        "color_resources": bundle_metadata["scan"]["meb_resources_with_color"],
        "direct_meb_files": len(direct_mebs),
        "bff_files": len(bffs),
        "errors": len(errors),
        "source_evidence": source_report is not None,
    }, ensure_ascii=False, indent=2))
    return 1 if errors and args.fail_on_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect exact SHIFT MEB 460/461 evidence into one ZIP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Game directory, .bff archive, or .meb file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="shift_meb_evidence.zip",
        help="Output ZIP path",
    )
    parser.add_argument(
        "--source",
        help="Optional recovered SHIFT.exe.c; adds source-level D3D9 proof",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Return exit code 1 when any file/resource failed",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failed resource",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return collect(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
