#!/usr/bin/env python3
"""Audit SHIFT BFF archives without discarding any entry.

The audit is deliberately separate from extraction: the default mode reads only
the BFF index/name tables, while --decode optionally decodes selected resources
and records decoded signatures/formats. This makes large retail archives cheap
to inventory before expensive XMem/LZX work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from resource_formats import analyze_decoded_resource
from shift_importer import BFF, EXT_CATEGORY, MAGIC_CATEGORY

FORMAT = "SHIFT.BFFArchiveAudit/1"


def _norm_path(value: str) -> str:
    return value.replace("\", "/").strip("/")


def _extension(path: str) -> str:
    return Path(path.lower()).suffix


def _extension_category(path: str) -> str:
    return EXT_CATEGORY.get(_extension(path), "UNKNOWN")


def _magic_category(data: bytes) -> str:
    head = data[:64].lstrip()
    for signature, category in MAGIC_CATEGORY:
        if data.startswith(signature) or head.startswith(signature):
            return category
    return "UNKNOWN"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_archives(source: str | Path) -> list[Path]:
    root = Path(source)
    if root.is_file():
        if root.suffix.lower() != ".bff":
            raise ValueError(f"input is not a .bff archive: {root}")
        return [root]
    if not root.is_dir():
        raise FileNotFoundError(root)
    return sorted(path for path in root.rglob("*.bff") if path.is_file())


def _selected_for_decode(
    entry: Any,
    *,
    decode: bool,
    decode_extensions: set[str] | None,
    remaining: list[int] | None,
) -> bool:
    if not decode:
        return False
    if remaining is not None and not remaining:
        return False
    if decode_extensions:
        return _extension(entry.path) in decode_extensions
    return True


def audit_archive(
    path: str | Path,
    *,
    decode: bool = False,
    decode_extensions: Iterable[str] | None = None,
    max_decode: int | None = None,
    include_entry_hashes: bool = False,
) -> dict[str, Any]:
    source = Path(path)
    decode_exts = {
        value.lower() if value.startswith(".") else "." + value.lower()
        for value in (decode_extensions or [])
    }
    remaining = [int(max_decode)] if max_decode is not None else None
    with BFF(source) as archive:
        entries: list[dict[str, Any]] = []
        compression = Counter()
        extensions = Counter()
        categories = Counter()
        decoded_formats = Counter()
        decode_failures: list[dict[str, Any]] = []

        for entry in archive.entries:
            ext = _extension(entry.path)
            category = _extension_category(entry.path)
            compression[str(entry.type)] += 1
            extensions[ext or "<none>"] += 1
            categories[category] += 1

            row: dict[str, Any] = {
                "index": int(entry.index),
                "path": _norm_path(entry.path),
                "offset": int(entry.offset),
                "compressed_size": int(entry.compressed_size),
                "uncompressed_size": int(entry.uncompressed_size),
                "type": int(entry.type),
                "crc": int(getattr(entry, "crc32_field", getattr(entry, "crc", 0))),
                "fileext": int(entry.fileext),
                "extension": ext,
                "category": category,
                "compression_ratio": (
                    round(entry.compressed_size / entry.uncompressed_size, 6)
                    if entry.uncompressed_size
                    else None
                ),
            }

            should_decode = _selected_for_decode(
                entry,
                decode=decode,
                decode_extensions=decode_exts,
                remaining=remaining,
            )
            if should_decode:
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                    analysis = analyze_decoded_resource(entry.path, payload)
                    decoded_format = str(
                        (analysis.get("analysis") or {}).get("format")
                        or analysis.get("format")
                        or "unknown"
                    )
                    decoded_formats[decoded_format] += 1
                    row["decode"] = {
                        "status": "ok",
                        "size": len(payload),
                        "sha256": _sha256(payload),
                        "magic_category": _magic_category(payload),
                        "format": decoded_format,
                        "analysis": analysis.get("analysis"),
                    }
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    decode_failures.append({
                        "index": int(entry.index),
                        "path": _norm_path(entry.path),
                        "error": error,
                    })
                    row["decode"] = {
                        "status": "error",
                        "error": error,
                    }
                if remaining is not None:
                    remaining[0] -= 1

            if include_entry_hashes and row.get("decode", {}).get("status") == "ok":
                # The decoded hash is already present under decode; this flag
                # is retained for CLI symmetry and future raw-payload hashing.
                row["hash_scope"] = "decoded"

            entries.append(row)

        return {
            "format": FORMAT,
            "version": 1,
            "status": "ok" if not decode_failures else "decoded-with-errors",
            "ready": not decode_failures,
            "archive": {
                "path": str(source),
                "filename": source.name,
                "size": source.stat().st_size,
                "magic": archive.magic.decode("latin-1", "replace"),
                "version": int(archive.version),
                "file_count": len(archive.entries),
                "record_size": 42,
                "records_offset": int(archive.records_offset),
                "x118": int(archive.x118),
                "x120": int(archive.x120),
                "x12d": int(archive.x12d),
                "name_base": int(archive.name_base),
                "name_end": int(archive.name_end),
            },
            "summary": {
                "entries": len(entries),
                "compression_types": dict(sorted(compression.items(), key=lambda item: int(item[0]))),
                "extensions": dict(extensions.most_common()),
                "categories": dict(categories.most_common()),
                "decoded_formats": dict(decoded_formats.most_common()),
                "decode_attempted": sum(
                    1 for row in entries if "decode" in row
                ),
                "decode_failures": len(decode_failures),
                "unknown_extensions": sorted(
                    ext for ext, count in extensions.items()
                    if ext != "<none>" and EXT_CATEGORY.get(ext) is None
                ),
            },
            "decode_failures": decode_failures,
            "entries": entries,
        }


def audit_source(
    source: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    archives = iter_archives(source)
    reports = [audit_archive(path, **kwargs) for path in archives]
    merged_compression = Counter()
    merged_extensions = Counter()
    merged_categories = Counter()
    failures = []
    for report in reports:
        merged_compression.update(report["summary"]["compression_types"])
        merged_extensions.update(report["summary"]["extensions"])
        merged_categories.update(report["summary"]["categories"])
        failures.extend(report["decode_failures"])

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ok" if not failures else "decoded-with-errors",
        "ready": not failures,
        "source": str(Path(source)),
        "archive_count": len(reports),
        "summary": {
            "entries": sum(r["summary"]["entries"] for r in reports),
            "compression_types": dict(sorted(merged_compression.items(), key=lambda item: int(item[0]))),
            "extensions": dict(merged_extensions.most_common()),
            "categories": dict(merged_categories.most_common()),
            "decode_failures": len(failures),
        },
        "archives": reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="a .bff file or directory tree")
    parser.add_argument("output", type=Path, help="JSON audit report")
    parser.add_argument("--decode", action="store_true", help="decode entries while auditing")
    parser.add_argument(
        "--decode-extension",
        action="append",
        default=[],
        metavar="EXT",
        help="limit decoding to one extension; repeat for multiple extensions",
    )
    parser.add_argument(
        "--max-decode",
        type=int,
        default=None,
        help="maximum number of resources to decode per archive",
    )
    parser.add_argument(
        "--include-entry-hashes",
        action="store_true",
        help="retain decoded SHA-256 fields in entry rows",
    )
    args = parser.parse_args(argv)

    if args.max_decode is not None and args.max_decode < 0:
        parser.error("--max-decode must be non-negative")

    report = audit_source(
        args.input,
        decode=args.decode,
        decode_extensions=args.decode_extension,
        max_decode=args.max_decode,
        include_entry_hashes=args.include_entry_hashes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "archive_count": report["archive_count"],
        "entries": report["summary"]["entries"],
        "compression_types": report["summary"]["compression_types"],
        "categories": report["summary"]["categories"],
        "decode_failures": report["summary"]["decode_failures"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
