#!/usr/bin/env python3
"""Extract the last N bytes from a trace file without loading the whole file."""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_SIZE = 500 * 1024 * 1024


def extract_tail(source: Path, destination: Path, size: int = DEFAULT_SIZE) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination must be different files")

    file_size = source.stat().st_size
    tail_size = min(size, file_size)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("wb") as dst:
        src.seek(file_size - tail_size)
        remaining = tail_size
        while remaining:
            chunk = src.read(min(1024 * 1024, remaining))
            if not chunk:
                raise IOError("unexpected end of source file")
            dst.write(chunk)
            remaining -= len(chunk)

    return tail_size


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Save the last 500 MiB (or a custom number of bytes) of a .trace file."
    )
    parser.add_argument("source", type=Path, help="source .trace file")
    parser.add_argument("destination", type=Path, help="output file")
    parser.add_argument(
        "--size-mib",
        type=int,
        default=500,
        help="number of MiB to extract (default: 500)",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source file does not exist: {args.source}")

    size = args.size_mib * 1024 * 1024
    extracted = extract_tail(args.source, args.destination, size)
    print(f"source:     {args.source}")
    print(f"destination:{args.destination}")
    print(f"extracted:  {extracted} bytes ({extracted / 1024 / 1024:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
