#!/usr/bin/env python3
"""Read Xbox 360 SHIFT PAK/BFF indexes without extracting payload data."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path


HEADER_SIZE = 0x130
RECORDS_OFFSET = 0x130
RECORD_SIZE = 42
NAME_RECORD_SIZE = 16
NAME_BASE_ADJUSTMENT = 0x438
NAME_TABLE_ADJUSTMENT = 0x308


@dataclass(frozen=True)
class Entry:
    archive: str
    index: int
    path: str
    offset: int
    compressed_size: int
    uncompressed_size: int
    compression_type: int


def parse_archive(path: Path) -> list[Entry]:
    """Parse and range-check one Xbox big-endian PAK/BFF index."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(HEADER_SIZE)
        if len(header) != HEADER_SIZE or header[:4] not in (b"PAK ", b" KAP"):
            raise ValueError(f"{path}: invalid or truncated Xbox PAK header")
        endian = ">" if header[:4] == b"PAK " else "<"
        if header[0x12D] != 0:
            raise ValueError(f"{path}: unsupported encrypted-index flag {header[0x12D]}")

        count = struct.unpack_from(f"{endian}I", header, 8)[0]
        record_bytes = struct.unpack_from(f"{endian}I", header, 0x118)[0]
        name_bytes = struct.unpack_from(f"{endian}I", header, 0x120)[0] - NAME_TABLE_ADJUSTMENT
        if record_bytes != count * RECORD_SIZE or name_bytes < count * NAME_RECORD_SIZE:
            raise ValueError(f"{path}: inconsistent Xbox PAK index sizes")

        name_base = NAME_BASE_ADJUSTMENT + record_bytes
        name_end = name_base + name_bytes
        if name_end > size:
            raise ValueError(f"{path}: name table exceeds archive size")

        stream.seek(RECORDS_OFFSET)
        records = stream.read(record_bytes)
        stream.seek(name_base)
        names = stream.read(name_bytes)
        if len(records) != record_bytes or len(names) != name_bytes:
            raise ValueError(f"{path}: truncated Xbox PAK index")

    entries = []
    for index in range(count):
        record_at = index * RECORD_SIZE
        name_record_at = index * NAME_RECORD_SIZE
        offset = struct.unpack_from(f"{endian}Q", records, record_at + 8)[0]
        compressed_size = struct.unpack_from(f"{endian}I", records, record_at + 16)[0]
        uncompressed_size = struct.unpack_from(f"{endian}I", records, record_at + 20)[0]
        compression_type = records[record_at + 32]
        name_offset = struct.unpack_from(f"{endian}Q", names, name_record_at)[0]
        if not name_base <= name_offset < name_end:
            raise ValueError(f"{path}: entry {index} name offset is out of bounds")
        name_at = name_offset - name_base
        name_size = names[name_at]
        if name_at + 1 + name_size > len(names):
            raise ValueError(f"{path}: entry {index} name is truncated")
        if offset > size or compressed_size > size - offset:
            raise ValueError(f"{path}: entry {index} payload is out of bounds")

        entry_path = names[name_at + 1 : name_at + 1 + name_size].decode("utf-8", "replace")
        entries.append(
            Entry(
                archive=path.name,
                index=index,
                path=entry_path.replace("\\", "/"),
                offset=offset,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                compression_type=compression_type,
            )
        )
    return entries


def audit_root(root: Path, contains: list[str]) -> dict:
    archives = sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() == ".bff"
    )
    results = []
    failures = []
    for path in archives:
        try:
            entries = parse_archive(path)
        except (OSError, ValueError) as exc:
            failures.append({"archive": path.relative_to(root).as_posix(), "error": str(exc)})
            continue
        for entry in entries:
            normalized = entry.path.casefold()
            if any(needle.casefold() in normalized for needle in contains):
                item = asdict(entry)
                item["archive"] = path.relative_to(root).as_posix()
                results.append(item)
    return {
        "schema": "shift.xbox360.pak-index-audit.v1",
        "root": str(root),
        "archives_seen": len(archives),
        "archives_parsed": len(archives) - len(failures),
        "failures": failures,
        "contains": contains,
        "matches": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="directory containing Xbox retail PAK/BFF files")
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="case-insensitive logical member substring; may be repeated",
    )
    parser.add_argument("--output", type=Path, help="write JSON output to this path")
    args = parser.parse_args()
    result = audit_root(args.root, args.contains)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
