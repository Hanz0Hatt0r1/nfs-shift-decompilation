#!/usr/bin/env python3
"""Streaming analyzer for SHIFT live-memory snapshots."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
from typing import BinaryIO

FORMAT = "SHIFT-LIVE-MEMORY-ANALYSIS/1"

def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if obj.get("format") != "SHIFT-LIVE-MEMORY-SNAPSHOT/1":
        raise ValueError(f"{path}: unsupported snapshot format")
    return obj

def classify(path: str) -> str:
    if path == "[heap]": return "heap"
    if not path or path.startswith("["): return "anonymous"
    if path.startswith("/"): return "module"
    return "other"

def region_index(manifest: dict) -> dict[int, dict]:
    return {int(r["start"]): r for r in manifest.get("regions", [])}

def read_exact(f: BinaryIO, size: int) -> bytes:
    data = f.read(size)
    return data + b"\0" * (size - len(data))

def analyze_region(snapshots, regions, block_size, candidate_limit, meta):
    size = int(meta["size"])
    files = []
    try:
        for snap, region in zip(snapshots, regions):
            files.append((snap / region["file"]).open("rb"))
        block_count = (size + block_size - 1) // block_size
        changed_blocks = transition_blocks = changed_events = 0
        candidates = []
        for index in range(block_count):
            offset = index * block_size
            want = min(block_size, size - offset)
            blocks = [read_exact(f, want) for f in files]
            hashes = [hashlib.blake2b(x, digest_size=8).digest() for x in blocks]
            unique = len(set(hashes))
            transitions = sum(a != b for a, b in zip(hashes, hashes[1:]))
            first_changes = sum(h != hashes[0] for h in hashes[1:])
            if unique > 1: changed_blocks += 1
            if transitions:
                transition_blocks += 1
                changed_events += transitions
                score = transitions * 4 + first_changes * 2 + min(unique, 8)
                candidates.append({
                    "score": score, "start": meta["start"], "offset": offset,
                    "address": meta["start"] + offset, "block_size": want,
                    "transitions": transitions, "changed_from_first": first_changes,
                    "unique_states": unique, "category": meta["category"],
                    "path": meta["path"], "region_size": size
                })
                if len(candidates) > candidate_limit * 3:
                    candidates.sort(key=lambda x: (-x["score"], x["address"]))
                    del candidates[candidate_limit * 2:]
    finally:
        for f in files: f.close()
    return {
        **meta, "snapshots": len(snapshots), "blocks": block_count,
        "changed_blocks": changed_blocks,
        "changed_ratio": changed_blocks / block_count if block_count else 0.0,
        "transition_blocks": transition_blocks, "changed_events": changed_events
    }, candidates

def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze SHIFT live-memory snapshots without loading them into RAM")
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--block-size-kib", type=int, default=4)
    ap.add_argument("--top", type=int, default=10000)
    ap.add_argument("--min-transitions", type=int, default=1)
    args = ap.parse_args()
    if min(args.block_size_kib, args.top, args.min_transitions) <= 0:
        ap.error("numeric options must be positive")

    snapshots = sorted(p for p in args.root.glob("snapshot-*") if (p / "manifest.json").is_file())
    if len(snapshots) < 2: raise SystemExit("need at least two snapshots")
    manifests = [load_manifest(p / "manifest.json") for p in snapshots]
    indexes = [region_index(m) for m in manifests]
    common = set(indexes[0])
    for idx in indexes[1:]: common &= set(idx)
    out = args.out or args.root / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    block_size = args.block_size_kib * 1024
    region_rows, candidates = [], []

    for start in sorted(common):
        rs = [idx[start] for idx in indexes]
        if any(int(r["size"]) != int(rs[0]["size"]) for r in rs): continue
        base = rs[0]
        meta = {
            "start": int(base["start"]), "end": int(base["end"]),
            "size": int(base["size"]), "perms": base.get("perms", ""),
            "path": base.get("path", ""), "category": classify(base.get("path", ""))
        }
        row, found = analyze_region(snapshots, rs, block_size, args.top, meta)
        region_rows.append(row)
        candidates.extend(c for c in found if c["transitions"] >= args.min_transitions)

    candidates.sort(key=lambda x: (-x["score"], -x["transitions"], x["address"]))
    candidates = candidates[:args.top]

    fields = ["start","end","size","perms","path","category","snapshots","blocks",
              "changed_blocks","changed_ratio","transition_blocks","changed_events"]
    with (out / "region_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(region_rows)
    fields = ["score","address","start","offset","block_size","transitions",
              "changed_from_first","unique_states","category","path","region_size"]
    with (out / "block_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(candidates)

    categories = {}
    for r in region_rows:
        c = categories.setdefault(r["category"], {"regions":0,"bytes":0,"changed_blocks":0,"blocks":0,"changed_events":0})
        c["regions"] += 1; c["bytes"] += r["size"]
        c["changed_blocks"] += r["changed_blocks"]; c["blocks"] += r["blocks"]
        c["changed_events"] += r["changed_events"]
    for c in categories.values():
        c["changed_ratio"] = c["changed_blocks"] / c["blocks"] if c["blocks"] else 0.0

    report = {
        "format": FORMAT, "snapshot_count": len(snapshots),
        "snapshots": [p.name for p in snapshots], "block_size": block_size,
        "regions_per_snapshot": [len(i) for i in indexes],
        "common_regions": len(common), "analyzed_regions": len(region_rows),
        "candidate_blocks": len(candidates),
        "total_common_bytes": sum(r["size"] for r in region_rows),
        "categories": categories
    }
    (out / "analysis.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"snapshots: {len(snapshots)}")
    print(f"common regions: {len(common)}")
    print(f"analyzed regions: {len(region_rows)}")
    print(f"common bytes: {report['total_common_bytes']}")
    print(f"candidates: {len(candidates)}")
    print(f"output: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
