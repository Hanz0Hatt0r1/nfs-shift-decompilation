#!/usr/bin/env python3
"""Event-aware streaming analysis for SHIFT live-memory snapshots.

Ranks snapshot transitions and memory blocks by how abruptly their contents
change. It deliberately does not assign semantic labels such as "crash" or
"physics"; transition numbers are only capture-order indices.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import BinaryIO


FORMAT = "SHIFT-LIVE-MEMORY-EVENT-ANALYSIS/1"


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


def analyze_region(snapshots, regions, block_size, top, transition_totals,
                   candidates, meta):
    size = int(meta["size"])
    files = []
    try:
        for snap, region in zip(snapshots, regions):
            files.append((snap / region["file"]).open("rb"))

        block_count = (size + block_size - 1) // block_size
        for index in range(block_count):
            offset = index * block_size
            want = min(block_size, size - offset)
            blocks = [read_exact(f, want) for f in files]

            changed = []
            for t in range(len(blocks) - 1):
                a, b = blocks[t], blocks[t + 1]
                if a == b:
                    changed.append(0)
                else:
                    # Count changed bytes, not changed bits. This makes the
                    # metric interpretable and stable across architectures.
                    changed.append(sum(x != y for x, y in zip(a, b)))

            changed_transitions = sum(x > 0 for x in changed)
            if not changed_transitions:
                continue

            for t, n in enumerate(changed):
                if n:
                    total = transition_totals[t]
                    total["changed_blocks"] += 1
                    total["changed_bytes"] += n
                    total["regions_with_changes"].add(meta["start"])

            peak = max(changed)
            peak_transition = changed.index(peak)
            total_changed = sum(changed)
            concentration = peak / total_changed if total_changed else 0.0

            # Stronger signal for a one/few-transition burst, while retaining
            # the magnitude of the largest transition.
            event_score = peak * (1.0 + 1.0 / changed_transitions)
            row = {
                "event_score": event_score,
                "address": meta["start"] + offset,
                "start": meta["start"],
                "offset": offset,
                "block_size": want,
                "peak_transition": peak_transition,
                "peak_changed_bytes": peak,
                "total_changed_bytes": total_changed,
                "changed_transitions": changed_transitions,
                "transition_concentration": concentration,
                "category": meta["category"],
                "path": meta["path"],
                "region_size": size,
            }
            candidates.append(row)
            if len(candidates) > top * 4:
                candidates.sort(
                    key=lambda x: (-x["event_score"], x["address"])
                )
                del candidates[top * 2:]
    finally:
        for f in files:
            f.close()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Rank abrupt transition events in SHIFT live-memory snapshots"
    )
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--block-size-kib", type=int, default=4)
    ap.add_argument("--top", type=int, default=10000)
    ap.add_argument("--min-changed-transitions", type=int, default=1)
    ap.add_argument("--cluster-gap-kib", type=int, default=64)
    args = ap.parse_args()
    if min(args.block_size_kib, args.top, args.min_changed_transitions,
           args.cluster_gap_kib) <= 0:
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

    out = args.out or args.root / "event_analysis"
    out.mkdir(parents=True, exist_ok=True)
    block_size = args.block_size_kib * 1024
    transition_totals = [
        {"changed_blocks": 0, "changed_bytes": 0, "regions_with_changes": set()}
        for _ in range(len(snapshots) - 1)
    ]
    candidates = []

    for start in sorted(common):
        rs = [idx[start] for idx in indexes]
        if any(int(r["size"]) != int(rs[0]["size"]) for r in rs):
            continue
        base = rs[0]
        meta = {
            "start": int(base["start"]),
            "end": int(base["end"]),
            "size": int(base["size"]),
            "perms": base.get("perms", ""),
            "path": base.get("path", ""),
            "category": classify(base.get("path", "")),
        }
        analyze_region(
            snapshots, rs, block_size, args.top, transition_totals,
            candidates, meta
        )

    candidates = [
        c for c in candidates
        if c["changed_transitions"] >= args.min_changed_transitions
    ]
    candidates.sort(key=lambda x: (-x["event_score"], x["address"]))
    candidates = candidates[:args.top]

    transition_rows = []
    for i, row in enumerate(transition_totals):
        transition_rows.append({
            "transition": i,
            "from_snapshot": snapshots[i].name,
            "to_snapshot": snapshots[i + 1].name,
            "changed_blocks": row["changed_blocks"],
            "changed_bytes": row["changed_bytes"],
            "regions_with_changes": len(row["regions_with_changes"]),
        })

    with (out / "transition_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        fields = list(transition_rows[0])
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(transition_rows)

    with (out / "event_blocks.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        fields = [
            "event_score", "address", "start", "offset", "block_size",
            "peak_transition", "peak_changed_bytes", "total_changed_bytes",
            "changed_transitions", "transition_concentration", "category",
            "path", "region_size",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(candidates)

    # Cluster only retained high-signal candidates. A cluster is capture-local:
    # same peak transition and nearby virtual addresses.
    clusters = []
    gap = args.cluster_gap_kib * 1024
    for row in sorted(
        candidates, key=lambda x: (x["peak_transition"], x["address"])
    ):
        if (
            clusters
            and clusters[-1]["peak_transition"] == row["peak_transition"]
            and row["address"] - clusters[-1]["end"] <= gap
            and clusters[-1]["category"] == row["category"]
        ):
            c = clusters[-1]
            c["end"] = max(c["end"], row["address"] + row["block_size"])
            c["blocks"] += 1
            c["total_changed_bytes"] += row["total_changed_bytes"]
            c["peak_changed_bytes"] = max(
                c["peak_changed_bytes"], row["peak_changed_bytes"]
            )
            c["max_event_score"] = max(c["max_event_score"], row["event_score"])
        else:
            clusters.append({
                "peak_transition": row["peak_transition"],
                "start": row["address"],
                "end": row["address"] + row["block_size"],
                "blocks": 1,
                "total_changed_bytes": row["total_changed_bytes"],
                "peak_changed_bytes": row["peak_changed_bytes"],
                "max_event_score": row["event_score"],
                "category": row["category"],
                "path": row["path"],
            })

    clusters.sort(
        key=lambda x: (-x["max_event_score"], -x["blocks"], x["start"])
    )
    with (out / "event_clusters.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        fields = [
            "peak_transition", "start", "end", "blocks",
            "total_changed_bytes", "peak_changed_bytes", "max_event_score",
            "category", "path",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(clusters)

    report = {
        "format": FORMAT,
        "snapshot_count": len(snapshots),
        "snapshots": [p.name for p in snapshots],
        "transition_count": len(snapshots) - 1,
        "block_size": block_size,
        "common_regions": len(common),
        "candidate_blocks": len(candidates),
        "event_clusters": len(clusters),
        "cluster_gap": gap,
        "transitions": [
            {
                "transition": r["transition"],
                "from_snapshot": r["from_snapshot"],
                "to_snapshot": r["to_snapshot"],
                "changed_blocks": r["changed_blocks"],
                "changed_bytes": r["changed_bytes"],
                "regions_with_changes": r["regions_with_changes"],
            }
            for r in transition_rows
        ],
        "interpretation": {
            "peak_transition": "capture-order index; zero means snapshot-000000 -> snapshot-000001",
            "event_score": "peak changed bytes multiplied by (1 + 1/changed_transitions)",
            "limitation": "a transition is not identified as crash, physics, camera, input, or any other semantic event without controlled capture evidence",
        },
    }
    (out / "event_analysis.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print(f"snapshots: {len(snapshots)}")
    print(f"common regions: {len(common)}")
    print(f"transitions: {len(transition_rows)}")
    print(f"event candidates: {len(candidates)}")
    print(f"event clusters: {len(clusters)}")
    print(f"output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
