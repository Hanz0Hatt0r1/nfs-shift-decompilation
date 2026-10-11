#!/usr/bin/env python3
"""Find exact live copies of the canonical render-manager outer-root pointer.

The analyzer consumes shift-live-dump snapshots. For each snapshot it reads the
current 32-bit value stored at DAT_00bc185c and then scans every captured
writable mapping for that exact value. This turns the open "unknown-origin
initialized memory" class into concrete runtime candidate addresses without
claiming process-wide or all-time absence from any finite capture set.
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374RuntimeExactRootAliasCapture/1"
SNAPSHOT_FORMAT = "SHIFT-LIVE-MEMORY-SNAPSHOT/1"
ROOT_SLOT = 0x00BC185C
POINTER_SIZE = 4
DEFAULT_CHUNK = 4 * 1024 * 1024


def load_manifest(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("format") != SNAPSHOT_FORMAT:
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


def region_for_address(manifest: dict, address: int) -> dict | None:
    for region in manifest.get("regions", []):
        start = int(region["start"])
        end = int(region["end"])
        if start <= address < end:
            return region
    return None


def read_u32(snapshot: Path, region: dict, address: int) -> int:
    start = int(region["start"])
    offset = address - start
    with (snapshot / region["file"]).open("rb") as f:
        f.seek(offset)
        data = f.read(POINTER_SIZE)
    if len(data) != POINTER_SIZE:
        raise ValueError(f"{snapshot}: root slot bytes are truncated")
    return struct.unpack("<I", data)[0]


def iter_exact_u32_matches(path: Path, value: int, *, alignment: int = 1, chunk_size: int = DEFAULT_CHUNK):
    if alignment <= 0:
        raise ValueError("alignment must be positive")
    needle = struct.pack("<I", value)
    overlap = POINTER_SIZE - 1
    absolute = 0
    carry = b""
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            data = carry + chunk
            data_base = absolute - len(carry)
            pos = data.find(needle)
            while pos >= 0:
                file_offset = data_base + pos
                if file_offset >= 0 and file_offset % alignment == 0:
                    yield file_offset
                pos = data.find(needle, pos + 1)
            carry = data[-overlap:] if len(data) >= overlap else data
            absolute += len(chunk)


def analyze(root: Path, *, alignment: int = 1) -> dict:
    snapshots = sorted(p for p in root.glob("snapshot-*") if (p / "manifest.json").is_file())
    if not snapshots:
        raise ValueError("no snapshots found")

    manifests = [load_manifest(s / "manifest.json") for s in snapshots]
    active = []
    zero_root_snapshots = []
    aggregate: dict[int, dict] = {}
    canonical_observations = 0
    scanned_regions = 0
    scanned_bytes = 0

    for snap_index, (snapshot, manifest) in enumerate(zip(snapshots, manifests)):
        root_region = region_for_address(manifest, ROOT_SLOT)
        if root_region is None:
            raise ValueError(f"{snapshot}: root slot 0x{ROOT_SLOT:08x} was not captured")
        root_value = read_u32(snapshot, root_region, ROOT_SLOT)
        if root_value == 0:
            zero_root_snapshots.append(snapshot.name)
            continue

        active.append({"snapshot": snapshot.name, "root_value": f"0x{root_value:08x}"})
        for region in manifest.get("regions", []):
            perms = str(region.get("perms", ""))
            if "w" not in perms:
                continue
            start = int(region["start"])
            size = int(region["size"])
            file_path = snapshot / region["file"]
            scanned_regions += 1
            scanned_bytes += size
            for file_offset in iter_exact_u32_matches(file_path, root_value, alignment=alignment):
                address = start + file_offset
                if address == ROOT_SLOT:
                    canonical_observations += 1
                    continue
                row = aggregate.setdefault(address, {
                    "address": f"0x{address:08x}",
                    "region_start": f"0x{start:08x}",
                    "offset": file_offset,
                    "perms": perms,
                    "path": region.get("path", ""),
                    "category": classify(str(region.get("path", ""))),
                    "snapshot_hits": [],
                    "root_values": set(),
                })
                row["snapshot_hits"].append(snapshot.name)
                row["root_values"].add(root_value)

    candidates = []
    for address in sorted(aggregate):
        row = aggregate[address]
        candidates.append({
            "address": row["address"],
            "region_start": row["region_start"],
            "offset": row["offset"],
            "perms": row["perms"],
            "path": row["path"],
            "category": row["category"],
            "snapshot_hit_count": len(row["snapshot_hits"]),
            "snapshot_hits": row["snapshot_hits"],
            "unique_root_value_count": len(row["root_values"]),
            "root_values": [f"0x{x:08x}" for x in sorted(row["root_values"])],
        })

    active_count = len(active)
    persistent = [row for row in candidates if active_count and row["snapshot_hit_count"] == active_count]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "source_format": SNAPSHOT_FORMAT,
            "canonical_root_slot": f"0x{ROOT_SLOT:08x}",
            "pointer_width_bits": 32,
            "little_endian": True,
        },
        "capture": {
            "snapshot_count": len(snapshots),
            "active_nonzero_root_snapshot_count": active_count,
            "zero_root_snapshot_count": len(zero_root_snapshots),
            "zero_root_snapshots": zero_root_snapshots,
            "active_root_values": active,
            "alignment_bytes": alignment,
            "scanned_writable_region_instances": scanned_regions,
            "scanned_writable_bytes": scanned_bytes,
            "canonical_slot_observation_count": canonical_observations,
        },
        "surface": {
            "exact_outer_root_alias_candidate_count": len(candidates),
            "exact_outer_root_alias_candidates": candidates,
            "persistent_exact_outer_root_alias_candidate_count": len(persistent),
            "persistent_exact_outer_root_alias_candidates": persistent,
        },
        "adjudication": {
            "live_exact_root_alias_capture_complete_for_supplied_snapshots": True,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This is observational evidence over the supplied non-atomic live snapshots, not a proof over all process states or all executions.",
            "Only mappings captured in each snapshot and marked writable are scanned; missing/unreadable mappings remain outside the claim.",
            "A numeric equality hit is only an exact pointer-value candidate and does not by itself prove ownership or semantic aliasing.",
            "The canonical DAT_00bc185c slot itself is excluded from candidate output and counted separately.",
        ],
        "next_step": "Classify each noncanonical live exact-root alias candidate by producer/owner and repeat controlled captures across lifecycle states before promoting any external/unknown-origin root-alias closure.",
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "address", "region_start", "offset", "perms", "path", "category",
        "snapshot_hit_count", "unique_root_value_count", "snapshot_hits", "root_values",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["snapshot_hits"] = ";".join(out["snapshot_hits"])
            out["root_values"] = ";".join(out["root_values"])
            writer.writerow(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Find exact live copies of DAT_00bc185c render-manager root")
    ap.add_argument("root", type=Path, help="shift-live-dump watch/snapshot directory")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--alignment", type=int, choices=(1, 4), default=1)
    args = ap.parse_args()

    result = analyze(args.root, alignment=args.alignment)
    out = args.out or args.root / "manager374_root_alias_analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_csv(out / "exact_root_alias_candidates.csv", result["surface"]["exact_outer_root_alias_candidates"])
    print(f"active snapshots: {result['capture']['active_nonzero_root_snapshot_count']}")
    print(f"alias candidates: {result['surface']['exact_outer_root_alias_candidate_count']}")
    print(f"persistent candidates: {result['surface']['persistent_exact_outer_root_alias_candidate_count']}")
    print(f"output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
