#!/usr/bin/env python3
"""Extract small address ranges from SHIFT live-memory snapshots.

The input is a normal shift-live-dump capture directory containing
snapshot-XXXXXX/manifest.json and regions/*.bin. The output keeps the same
snapshot layout, but rewrites each selected region so downstream analyzers
can work on the reduced capture without loading the original multi-gigabyte
capture.

Ranges are virtual-address half-open intervals: START:SIZE.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


FORMAT = "SHIFT-LIVE-MEMORY-SNAPSHOT/1"

# Highest-signal blocks from the current event analysis. Windows are deliberately
# small; users can add/replace them with --range or --address-file.
DEFAULT_ADDRESSES = (
    418914304,
    419000320,
    561590272,
    561598464,
    561602560,
    561606656,
    563290112,
    55742464,
    55754752,
    215445504,
)
DEFAULT_RADIUS = 64 * 1024


def load_manifest(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("format") != FORMAT:
        raise ValueError(f"{path}: unsupported snapshot format")
    return obj


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_range(value: str) -> tuple[int, int]:
    try:
        start_s, size_s = value.split(":", 1)
        start = parse_int(start_s)
        size = parse_int(size_s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid range {value!r}; use START:SIZE, e.g. 0x100000:0x20000"
        ) from exc
    if start < 0 or size <= 0:
        raise argparse.ArgumentTypeError("range start must be >= 0 and size > 0")
    return start, size


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    intervals = sorted((start, start + size) for start, size in ranges)
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end - start) for start, end in merged]


def regions_for(manifest: dict) -> list[dict]:
    return sorted(manifest.get("regions", []), key=lambda r: int(r["start"]))


def read_slice(source: Path, offset: int, size: int) -> bytes:
    with source.open("rb") as f:
        f.seek(offset)
        data = f.read(size)
    if len(data) != size:
        raise IOError(f"{source}: expected {size} bytes at offset {offset}, got {len(data)}")
    return data


def extract_snapshot(
    source_snapshot: Path,
    output_snapshot: Path,
    wanted: list[tuple[int, int]],
) -> tuple[int, int]:
    manifest = load_manifest(source_snapshot / "manifest.json")
    output_snapshot.mkdir(parents=True, exist_ok=True)
    (output_snapshot / "regions").mkdir(exist_ok=True)

    selected_regions: list[dict] = []
    bytes_written = 0
    fragments = 0

    for region in regions_for(manifest):
        rstart = int(region["start"])
        rend = int(region["end"])
        source_file = source_snapshot / region["file"]
        for wanted_start, wanted_size in wanted:
            wanted_end = wanted_start + wanted_size
            start = max(rstart, wanted_start)
            end = min(rend, wanted_end)
            if start >= end:
                continue

            data = read_slice(source_file, start - rstart, end - start)
            index = len(selected_regions)
            rel = Path("regions") / f"range-{index:04d}-{start:016x}.bin"
            (output_snapshot / rel).write_bytes(data)
            selected_regions.append({
                "start": start,
                "end": end,
                "size": end - start,
                "perms": region.get("perms", ""),
                "path": region.get("path", ""),
                "file": rel.as_posix(),
                "source_start": rstart,
                "source_end": rend,
                "source_file": region["file"],
            })
            bytes_written += len(data)
            fragments += 1

    out_manifest = {
        "format": FORMAT,
        "pid": manifest.get("pid"),
        "mode": "range-extract",
        "page_size": manifest.get("page_size"),
        "backend": manifest.get("backend"),
        "source_snapshot": str(source_snapshot),
        "source_bytes_selected": bytes_written,
        "source_region_count": len(manifest.get("regions", [])),
        "maps_count": manifest.get("maps_count"),
        "selected_count": len(selected_regions),
        "bytes_requested": bytes_written,
        "bytes_read": bytes_written,
        "bytes_failed": 0,
        "regions": selected_regions,
    }
    (output_snapshot / "manifest.json").write_text(
        json.dumps(out_manifest, indent=2) + "\n", encoding="utf-8"
    )
    if (source_snapshot / "maps.txt").is_file():
        shutil.copy2(source_snapshot / "maps.txt", output_snapshot / "maps.txt")
    return fragments, bytes_written


def find_snapshots(root: Path) -> list[Path]:
    snapshots = sorted(
        p for p in root.glob("snapshot-*")
        if (p / "manifest.json").is_file()
    )
    if len(snapshots) < 1:
        raise SystemExit(f"no snapshot-XXXXXX directories found in {root}")
    return snapshots


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract small virtual-address windows from SHIFT live snapshots"
    )
    ap.add_argument("root", type=Path, help="original capture directory")
    ap.add_argument("out", type=Path, help="reduced capture directory")
    ap.add_argument(
        "--range", dest="ranges", action="append", type=parse_range,
        help="address range START:SIZE; repeatable; accepts 0x notation",
    )
    ap.add_argument(
        "--address", dest="addresses", action="append", type=parse_int,
        help="single virtual address to extract around; repeatable",
    )
    ap.add_argument(
        "--address-file", type=Path,
        help="text file containing one address per line (decimal or 0x-prefixed)",
    )
    ap.add_argument(
        "--radius-kib", type=int, default=64,
        help="radius around --address/--address-file addresses (default: 64 KiB)",
    )
    ap.add_argument(
        "--preset", choices=("event-top", "none"), default="event-top",
        help="predefined address set from the current event analysis",
    )
    args = ap.parse_args()

    if args.radius_kib < 0:
        ap.error("--radius-kib must be >= 0")

    ranges = list(args.ranges or [])
    addresses = list(args.addresses or [])
    if args.address_file:
        for raw in args.address_file.read_text(encoding="utf-8").splitlines():
            raw = raw.split("#", 1)[0].strip()
            if raw:
                addresses.append(parse_int(raw))

    if args.preset == "event-top":
        addresses = list(DEFAULT_ADDRESSES) + addresses

    radius = args.radius_kib * 1024
    ranges.extend((address - radius, 2 * radius) for address in addresses)
    ranges = [(max(0, start), size if start >= 0 else size + start)
              for start, size in ranges]
    ranges = [(start, size) for start, size in ranges if size > 0]
    ranges = merge_ranges(ranges)

    if not ranges:
        ap.error("no ranges selected; use --range/--address or --preset event-top")

    snapshots = find_snapshots(args.root)
    args.out.mkdir(parents=True, exist_ok=True)

    total = 0
    for snapshot in snapshots:
        fragments, written = extract_snapshot(
            snapshot, args.out / snapshot.name, ranges
        )
        total += written
        print(f"{snapshot.name}: {fragments} fragments, {written} bytes")

    (args.out / "extract_ranges.json").write_text(
        json.dumps({
            "format": "SHIFT-LIVE-MEMORY-RANGE-EXTRACT/1",
            "source": str(args.root),
            "snapshots": [s.name for s in snapshots],
            "ranges": [{"start": s, "size": n} for s, n in ranges],
            "total_bytes": total,
            "radius_kib": args.radius_kib,
            "preset": args.preset,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"total selected bytes: {total}")
    print(f"output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
