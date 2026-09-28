#!/usr/bin/env python3
"""Field-level analyzer for SHIFT live-memory snapshots.

This is a second pass over analyze.py's block candidates. It decodes aligned
2/4/8-byte values from changed blocks and ranks values that change coherently
across snapshots. It intentionally favors anonymous/heap memory and can
exclude known GPU/Wine mappings without pretending they are physics state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from pathlib import Path
from typing import BinaryIO


FORMAT = "SHIFT-LIVE-MEMORY-FIELD-ANALYSIS/1"
DEFAULT_BLOCK = 4096
DEFAULT_TOP = 20000
NOISE_TOKENS = (
    "/dev/nvidia",
    "nvidia",
    "tmpmap",
    ".wine-",
    "/usr/lib/wine",
    "/run/host/usr/lib32/libnvidia",
    "/run/host/usr/lib64/libnvidia",
)


def load_manifest(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("format") != "SHIFT-LIVE-MEMORY-SNAPSHOT/1":
        raise ValueError(f"{path}: unsupported snapshot format")
    return obj


def classify(path: str) -> str:
    if path == "[heap]":
        return "heap"
    if not path or path.startswith("["):
        return "anonymous"
    if path.startswith("/"):
        return "module"
    return "other"


def region_index(manifest: dict) -> dict[int, dict]:
    return {int(r["start"]): r for r in manifest.get("regions", [])}


def read_exact(f: BinaryIO, size: int) -> bytes:
    data = f.read(size)
    return data + b"\0" * (size - len(data))


def is_noise(path: str, perms: str) -> bool:
    p = path.lower()
    if "rw-s" in perms:
        return True
    return any(token in p for token in NOISE_TOKENS)


def finite_float(x: float) -> bool:
    return math.isfinite(x) and abs(x) < 1e30


def transitions(values: list[object]) -> int:
    return sum(a != b for a, b in zip(values, values[1:]))


def first_changes(values: list[object]) -> int:
    return sum(v != values[0] for v in values[1:])


def monotonic_steps(values: list[float]) -> int:
    if len(values) < 2:
        return 0
    return sum((b > a) - (b < a) != 0 for a, b in zip(values, values[1:]))


def direction_changes(values: list[float]) -> int:
    dirs = []
    for a, b in zip(values, values[1:]):
        if b > a:
            dirs.append(1)
        elif b < a:
            dirs.append(-1)
        else:
            dirs.append(0)
    dirs = [d for d in dirs if d]
    return sum(a != b for a, b in zip(dirs, dirs[1:]))


def decode_field(chunks: list[bytes], offset: int, kind: str):
    size = {"u16": 2, "i16": 2, "u32": 4, "i32": 4,
            "f32": 4, "u64": 8, "i64": 8, "f64": 8}[kind]
    fmt = {"u16": "<H", "i16": "<h", "u32": "<I", "i32": "<i",
           "f32": "<f", "u64": "<Q", "i64": "<q", "f64": "<d"}[kind]
    try:
        values = [struct.unpack_from(fmt, c, offset)[0] for c in chunks]
    except struct.error:
        return None
    if kind in ("f32", "f64") and not all(finite_float(v) for v in values):
        return None
    return values


def pointer_score(values: list[int], ranges: list[tuple[int, int]]) -> float:
    if not values or not ranges:
        return 0.0
    hits = 0
    for value in values:
        if value == 0:
            continue
        if any(start <= value < end for start, end in ranges):
            hits += 1
    return hits / len(values)


def analyze_block(
    chunks: list[bytes],
    base_address: int,
    block_offset: int,
    block_size: int,
    meta: dict,
    pointer_ranges: list[tuple[int, int]],
    min_transitions: int,
    fields: list[dict],
) -> None:
    max_offset = max(0, block_size - 8)
    # Aligned fields are much more useful for native C/C++ structures than a
    # byte-by-byte scan. Include 2-byte alignment because packed flags/halves
    # occur frequently in game state.
    for alignment in (2, 4, 8):
        for offset in range(0, max_offset + 1, alignment):
            absolute = base_address + block_offset + offset
            for kind in ("u16", "i16", "u32", "i32", "f32", "u64", "i64", "f64"):
                size = {"u16": 2, "i16": 2, "u32": 4, "i32": 4,
                        "f32": 4, "u64": 8, "i64": 8, "f64": 8}[kind]
                if offset + size > block_size:
                    continue
                values = decode_field(chunks, offset, kind)
                if values is None:
                    continue
                t = transitions(values)
                if t < min_transitions:
                    continue
                fc = first_changes(values)
                unique = len(set(values))
                ptr = 0.0
                if kind in ("u32", "u64"):
                    ptr = pointer_score(values, pointer_ranges)
                numeric = all(isinstance(v, (int, float)) for v in values)
                if not numeric:
                    continue
                if kind in ("f32", "f64"):
                    span = max(values) - min(values)
                    abs_mean = sum(abs(v) for v in values) / len(values)
                    if span == 0.0 or (abs_mean > 1e20 and ptr == 0.0):
                        continue
                    change_scale = span / max(abs_mean, 1e-12)
                else:
                    vmin, vmax = min(values), max(values)
                    span = vmax - vmin
                    change_scale = span / max(abs(abs_mean := sum(values) / len(values)), 1.0)
                score = (
                    t * 5
                    + min(unique, 10)
                    + fc * 1.5
                    + ptr * 8
                    + (2.0 if kind in ("f32", "f64") and change_scale < 100.0 else 0.0)
                )
                fields.append({
                    "score": round(score, 4),
                    "address": absolute,
                    "region_start": meta["start"],
                    "region_offset": block_offset + offset,
                    "field_offset": offset,
                    "size": size,
                    "type": kind,
                    "transitions": t,
                    "changed_from_first": fc,
                    "unique_states": unique,
                    "min": min(values),
                    "max": max(values),
                    "span": max(values) - min(values),
                    "pointer_hits": round(ptr, 4),
                    "category": meta["category"],
                    "path": meta["path"],
                    "perms": meta["perms"],
                    "region_size": meta["size"],
                    "snapshots": len(values),
                    "values": [float(v) if isinstance(v, float) else int(v) for v in values],
                })


def group_structures(fields: list[dict], gap: int, top: int) -> list[dict]:
    """Group high-signal fields that sit close together in one mapping."""
    ordered = sorted(fields, key=lambda x: (x["region_start"], x["address"]))
    groups = []
    current = []
    last = None
    for field in ordered:
        if last is None or (
            field["region_start"] == last["region_start"]
            and field["address"] - last["address"] <= gap
        ):
            current.append(field)
        else:
            if current:
                groups.append(current)
            current = [field]
        last = field["address"]
    if current:
        groups.append(current)

    rows = []
    for group in groups:
        if len(group) < 2:
            continue
        unique_addresses = sorted({f["address"] for f in group})
        score = sum(f["score"] for f in group)
        rows.append({
            "score": round(score, 4),
            "region_start": group[0]["region_start"],
            "start_address": unique_addresses[0],
            "end_address": unique_addresses[-1] + max(f["size"] for f in group),
            "span": unique_addresses[-1] - unique_addresses[0],
            "field_count": len(group),
            "max_transitions": max(f["transitions"] for f in group),
            "category": group[0]["category"],
            "path": group[0]["path"],
            "perms": group[0]["perms"],
            "field_addresses": ",".join(hex(a) for a in unique_addresses),
            "field_types": ",".join(f["type"] for f in group),
        })
    rows.sort(key=lambda x: (-x["score"], -x["max_transitions"], x["start_address"]))
    return rows[:top]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Decode changing 2/4/8-byte fields from SHIFT memory snapshots"
    )
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--block-size-kib", type=int, default=4)
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--min-transitions", type=int, default=2)
    ap.add_argument("--group-gap", type=int, default=128)
    ap.add_argument(
        "--scope", choices=("auto", "anonymous", "all"), default="auto",
        help="auto=anonymous+heap and private mappings; all=include module/device mappings"
    )
    ap.add_argument(
        "--include-noise", action="store_true",
        help="include mappings normally classified as GPU/Wine noise"
    )
    ap.add_argument(
        "--max-fields-per-block", type=int, default=96,
        help="keep only the strongest fields from each changed block"
    )
    args = ap.parse_args()

    if min(args.block_size_kib, args.top, args.min_transitions, args.group_gap,
           args.max_fields_per_block) <= 0:
        ap.error("numeric options must be positive")

    snapshots = sorted(
        p for p in args.root.glob("snapshot-*")
        if (p / "manifest.json").is_file()
    )
    if len(snapshots) < 2:
        raise SystemExit("need at least two snapshots")

    manifests = [load_manifest(p / "manifest.json") for p in snapshots]
    indexes = [region_index(m) for m in manifests]
    common = set(indexes[0])
    for idx in indexes[1:]:
        common &= set(idx)

    out = args.out or args.root / "field_analysis"
    out.mkdir(parents=True, exist_ok=True)
    block_size = args.block_size_kib * 1024

    pointer_ranges = [
        (int(r["start"]), int(r["end"]))
        for r in indexes[0].values()
        if int(r["end"]) > int(r["start"])
    ]

    fields: list[dict] = []
    region_stats: list[dict] = []
    skipped = {"scope": 0, "noise": 0, "size_mismatch": 0}
    analyzed_blocks = 0

    for start in sorted(common):
        rs = [idx[start] for idx in indexes]
        if any(int(r["size"]) != int(rs[0]["size"]) for r in rs):
            skipped["size_mismatch"] += 1
            continue
        base = rs[0]
        path = base.get("path", "")
        perms = base.get("perms", "")
        category = classify(path)

        if args.scope == "anonymous" and category not in ("anonymous", "heap"):
            skipped["scope"] += 1
            continue
        if args.scope == "auto" and category == "module" and not (
            "w-p" in perms or "wxp" in perms
        ):
            skipped["scope"] += 1
            continue
        if not args.include_noise and is_noise(path, perms):
            skipped["noise"] += 1
            continue

        meta = {
            "start": int(base["start"]),
            "end": int(base["end"]),
            "size": int(base["size"]),
            "perms": perms,
            "path": path,
            "category": category,
        }

        files = []
        changed_blocks = 0
        try:
            for snap, region in zip(snapshots, rs):
                files.append((snap / region["file"]).open("rb"))
            block_count = (meta["size"] + block_size - 1) // block_size

            for block_index in range(block_count):
                offset = block_index * block_size
                want = min(block_size, meta["size"] - offset)
                chunks = [read_exact(f, want) for f in files]
                if all(c == chunks[0] for c in chunks[1:]):
                    continue
                changed_blocks += 1
                analyzed_blocks += 1
                local_fields: list[dict] = []
                analyze_block(
                    chunks, meta["start"], offset, want, meta, pointer_ranges,
                    args.min_transitions, local_fields
                )
                local_fields.sort(
                    key=lambda x: (-x["score"], -x["transitions"], x["address"])
                )
                fields.extend(local_fields[:args.max_fields_per_block])
        finally:
            for f in files:
                f.close()

        region_stats.append({
            **meta,
            "blocks": (meta["size"] + block_size - 1) // block_size,
            "changed_blocks": changed_blocks,
            "changed_ratio": changed_blocks / max(1, (meta["size"] + block_size - 1) // block_size),
        })

    fields.sort(key=lambda x: (-x["score"], -x["transitions"], x["address"]))
    fields = fields[:args.top]
    structures = group_structures(fields, args.group_gap, args.top)

    field_columns = [
        "score", "address", "region_start", "region_offset", "field_offset",
        "size", "type", "transitions", "changed_from_first", "unique_states",
        "min", "max", "span", "pointer_hits", "category", "path", "perms",
        "region_size", "snapshots", "values",
    ]
    with (out / "field_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=field_columns)
        w.writeheader()
        for row in fields:
            row = dict(row)
            row["values"] = json.dumps(row["values"], separators=(",", ":"))
            w.writerow(row)

    structure_columns = [
        "score", "region_start", "start_address", "end_address", "span",
        "field_count", "max_transitions", "category", "path", "perms",
        "field_addresses", "field_types",
    ]
    with (out / "structure_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=structure_columns)
        w.writeheader()
        w.writerows(structures)

    report = {
        "format": FORMAT,
        "snapshot_count": len(snapshots),
        "snapshots": [p.name for p in snapshots],
        "block_size": block_size,
        "common_regions": len(common),
        "analyzed_blocks": analyzed_blocks,
        "field_candidates": len(fields),
        "structure_candidates": len(structures),
        "scope": args.scope,
        "include_noise": args.include_noise,
        "skipped": skipped,
        "region_count": len(region_stats),
        "field_types": {
            kind: sum(1 for f in fields if f["type"] == kind)
            for kind in ("u16", "i16", "u32", "i32", "f32", "u64", "i64", "f64")
        },
        "notes": [
            "Fields are candidates only; decoding bytes as a numeric type does not establish semantic meaning.",
            "Pointer hits only mean that an observed integer falls inside a mapped virtual address range.",
            "The default scope is intentionally biased toward private/anonymous memory to reduce GPU/Wine noise.",
            "A live snapshot is not atomic; values from one snapshot can originate from different moments during capture.",
        ],
    }
    (out / "field_analysis.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (out / "region_scope.csv").write_text(
        "start,end,size,perms,path,category,blocks,changed_blocks,changed_ratio\n"
        + "".join(
            f"{r['start']},{r['end']},{r['size']},{r['perms']},"
            f"{r['path']},{r['category']},{r['blocks']},{r['changed_blocks']},"
            f"{r['changed_ratio']:.8f}\n"
            for r in region_stats
        ),
        encoding="utf-8",
    )

    print(f"snapshots: {len(snapshots)}")
    print(f"common regions: {len(common)}")
    print(f"analyzed blocks: {analyzed_blocks}")
    print(f"field candidates: {len(fields)}")
    print(f"structure candidates: {len(structures)}")
    print(f"skipped: {skipped}")
    print(f"output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
