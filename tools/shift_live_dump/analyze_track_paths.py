#!/usr/bin/env python3
"""Find reverse-engineered track/path structures and heap pointer families."""
from __future__ import annotations

import argparse, csv, json, math, re, struct, sys, tempfile, zipfile
from bisect import bisect_right
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT-LIVE-MEMORY-TRACK-PATH-ANALYSIS/1"
VT_RANGE = (0x00400000, 0x00B81000)  # SHIFT.exe image in the supplied capture
# Exact vtables recovered from SHIFT.exe.c.
#
# AISegmentPath:
#   FUN_006d0fe0 writes PTR_FUN_00afca70 in the constructor.
# AIPolylinePath:
#   FUN_006cc900 is its constructor and writes PTR_FUN_00afc678;
#   its reflection metadata is emitted by FUN_006ccb20.
# AIPolyPathNode:
#   FUN_006cc730 allocates 0x24-byte node elements and assigns
#   PTR_FUN_00afbfa8 to each element.
KNOWN_VTABLES = {
    "AISegmentPath": 0x00AFCA70,
    "AIPolylinePath": 0x00AFC678,
    "AIPolyPathNode": 0x00AFBFA8,
}

PATH = {
    "tx": (0x10, "f"), "ty": (0x14, "f"), "outside": (0x18, "f"),
    "centre": (0x1c, "f"), "start_node": (0x20, "I"), "side": (0x24, "B"),
    "end": (0x25, "B"), "spawn": (0x26, "B"), "edge": (0x27, "B"),
}
INCIDENT = {
    # FUN_006c67e0 reflection metadata.
    "area": (0xd4, "I"),
    "path": (0xd8, "I"),
    "incident_x": (0x30, "f"),
    "incident_y": (0x34, "f"),
    "incident_z": (0x38, "f"),
    "cx": (0xdc, "f"),
    "cy": (0xe0, "f"),
    "cz": (0xe4, "f"),
    "radius": (0xe8, "f"),
    "active": (0xf0, "I"),
    "active_incident": (0xf4, "I"),
    "roaming": (0xf8, "I"),
    "incident_path_dist": (0x100, "f"),
    "incident_timer": (0x104, "f"),
    "interest_level": (0x108, "f"),
    "min_spacing": (0x10c, "f"),
    "track_dist": (0x110, "f"),
    "race_flag": (0x114, "I"),
    "area_index": (0x118, "I"),
    "n_marshals": (0x11c, "I"),
    "n_flag_marshals": (0x120, "I"),
}
SEGMENT = {
    # FUN_006d0690 is the reflection builder for AISegmentPath and explicitly
    # names these fields. Type 3 is a 32-bit integer/bool, type 1 is float,
    # and type 6 is the reflected array pointer.
    "nodes": (0x10, "I"),
    "side": (0x14, "I"),
    "array": (0x18, "I"),
    "length": (0x1c, "f"),
    "cyclic": (0x20, "I"),
    "narrow": (0x24, "I"),
    "spacing": (0x28, "f"),
    "path_dist": (0x2c, "f"),
    "current": (0x30, "I"),
    "edge_step": (0x34, "f"),
}
POLY = {
    "nodes": (0x10, "I"), "array": (0x14, "I"), "length": (0x18, "f"),
    "width": (0x1c, "f"), "cyclic": (0x20, "I"), "spacing": (0x24, "f"),
    "default_width": (0x28, "f"),
}
# AIPolyPathNode is allocated as a 0x24-byte element by FUN_006cc730.
# FUN_006cc600 consumes its two-dimensional position/tangent payload and
# cumulative path distance at +0x20.
POLY_NODE = {
    "x": (0x10, "f"),
    "y": (0x14, "f"),
    "dx": (0x18, "f"),
    "dy": (0x1c, "f"),
    "distance": (0x20, "f"),
}

SIZE = {"B": 1, "I": 4, "i": 4, "f": 4}

# The largest recovered structure currently decoded by this analyzer.
# Keep chunk overlap large enough to validate candidates that straddle a
# streaming boundary without keeping an entire capture region in RAM.
MAX_STRUCTURE_SIZE = max(
    max(offset + SIZE[typ] for offset, typ in spec.values())
    for spec in (PATH, INCIDENT, SEGMENT, POLY)
)
SCAN_CHUNK_SIZE = 4 * 1024 * 1024
POINTER_CHUNK_SIZE = 4 * 1024 * 1024
SCAN_OVERLAP = MAX_STRUCTURE_SIZE - 4


def load_manifest(p: Path) -> dict:
    obj = json.loads(p.read_text(encoding="utf-8"))
    if obj.get("format") != "SHIFT-LIVE-MEMORY-SNAPSHOT/1":
        raise ValueError(f"{p}: unsupported snapshot")
    return obj


def snapshots(root: Path) -> list[Path]:
    out = sorted(p for p in root.glob("snapshot-*") if (p / "manifest.json").is_file())
    if len(out) < 1:
        raise SystemExit("no snapshot-XXXXXX directories found")
    return out


def maps(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split(None, 5)
        if len(parts) < 2 or "-" not in parts[0]:
            continue
        try:
            a, b = (int(x, 16) for x in parts[0].split("-", 1))
        except ValueError:
            continue
        out.append({
            "start": a,
            "end": b,
            "perms": parts[1],
            "tail": parts[5] if len(parts) > 5 else "",
        })
    return sorted(out, key=lambda x: (x["start"], x["end"]))


def mapping(value: int, mm: list[dict], starts: list[int]) -> dict | None:
    i = bisect_right(starts, value) - 1
    while i >= 0 and mm[i]["start"] <= value:
        if value < mm[i]["end"]:
            return mm[i]
        i -= 1
    return None


def parse_range(value: str) -> tuple[int, int]:
    try:
        start_s, size_s = value.split(":", 1)
        start = int(start_s, 0)
        size = int(size_s, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid range {value!r}; use START:SIZE"
        ) from exc
    if start < 0 or size <= 0:
        raise argparse.ArgumentTypeError("range start must be >= 0 and size > 0")
    return start, start + size


def in_ranges(value: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= value < end for start, end in ranges)


def read(blob: bytes, off: int, typ: str):
    try:
        return struct.unpack_from("<" + typ, blob, off)[0]
    except struct.error:
        return None


def finite(x: float, limit: float = 1e8) -> bool:
    return isinstance(x, float) and math.isfinite(x) and abs(x) <= limit


def game_vtable(v: int, mm: list[dict], starts: list[int]) -> dict | None:
    r = mapping(v, mm, starts)
    return r if r and VT_RANGE[0] <= v < VT_RANGE[1] and r["perms"].startswith("r-x") else None


def writable(v: int, mm: list[dict], starts: list[int]) -> dict | None:
    r = mapping(v, mm, starts)
    return r if r and "w" in r["perms"] else None


def fields(blob: bytes, spec: dict) -> dict:
    return {k: read(blob, o, t) for k, (o, t) in spec.items()}


def check_path(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    vtable, rc, rs = read(blob, 0, "I"), read(blob, 4, "I"), read(blob, 8, "I")
    d = fields(blob, PATH)
    if None in (vtable, rc, rs) or any(v is None for v in d.values()):
        return None
    if not game_vtable(vtable, mm, starts):
        return None
    if not all(finite(d[k], 1e7) for k in ("tx", "ty", "outside", "centre")):
        return None
    norm = math.hypot(d["tx"], d["ty"])
    if not 0.80 <= norm <= 1.20:
        return None
    if not (
        d["side"] in (0, 1)
        and d["end"] in (0, 1, 0xFF)
        and d["spawn"] in (0, 1, 0xFF)
        and d["edge"] in (0, 1, 2, 0xFF)
    ):
        return None
    target = None if d["start_node"] == 0 else writable(d["start_node"], mm, starts)
    if d["start_node"] and target is None:
        return None
    return {
        "address": addr,
        "vtable": vtable,
        "refcount": rc,
        "refstate": rs,
        **d,
        "tangent_norm": norm,
        "start_node_mapping": target,
    }


def check_incident(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, INCIDENT)
    vt = read(blob, 0, "I")
    if vt is None or any(v is None for v in d.values()) or not game_vtable(vt, mm, starts):
        return None
    pm = writable(d["path"], mm, starts)
    if not pm or not 0 <= d["area"] <= 64:
        return None
    if not all(
        finite(d[k], 1e7)
        for k in ("incident_x", "incident_y", "incident_z", "cx", "cy", "cz")
    ):
        return None
    if not finite(d["radius"], 1e5) or not 0 <= d["radius"] <= 1e5:
        return None
    if not d["active"] in (0, 1) or not d["active_incident"] in (0, 1) or not d["roaming"] in (0, 1):
        return None
    if not all(
        finite(d[k], 1e7)
        for k in (
            "incident_path_dist",
            "incident_timer",
            "interest_level",
            "min_spacing",
            "track_dist",
        )
    ):
        return None
    if any(d[k] > 0x1000000 for k in ("race_flag", "area_index", "n_marshals", "n_flag_marshals")):
        return None
    return {
        "address": addr,
        "vtable": vt,
        "vtable_mapping": game_vtable(vt, mm, starts),
        **d,
        "path_mapping": pm,
    }


def check_segment(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, SEGMENT)
    vt = read(blob, 0, "I")
    if vt != KNOWN_VTABLES["AISegmentPath"] or any(v is None for v in d.values()):
        return None
    if not game_vtable(vt, mm, starts):
        return None
    if not 1 <= d["nodes"] <= 1000000:
        return None
    if d["side"] > 3:
        return None
    if d["cyclic"] not in (0, 1) or d["narrow"] not in (0, 1):
        return None
    array_mapping = writable(d["array"], mm, starts)
    if not array_mapping:
        return None
    if not all(finite(d[k]) for k in ("length", "spacing", "path_dist", "edge_step")):
        return None
    if not (0 < d["length"] <= 1e7 and 0 < d["spacing"] <= 1e5):
        return None
    if not 0 <= d["current"] <= d["nodes"]:
        return None
    return {
        "address": addr,
        "vtable": vt,
        "vtable_mapping": game_vtable(vt, mm, starts),
        **d,
        "array_mapping": array_mapping,
    }


def check_poly_node(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, POLY_NODE)
    vt = read(blob, 0, "I")
    if (
        vt != KNOWN_VTABLES["AIPolyPathNode"]
        or any(v is None for v in d.values())
        or not game_vtable(vt, mm, starts)
    ):
        return None
    if not all(finite(d[k], 1e7) for k in ("x", "y", "dx", "dy", "distance")):
        return None
    if d["distance"] < 0:
        return None
    return {
        "address": addr,
        "vtable": vt,
        "vtable_mapping": game_vtable(vt, mm, starts),
        **d,
    }


def check_poly(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, POLY)
    vt = read(blob, 0, "I")
    # AIPolylinePath has a recovered concrete vtable. Accepting any executable
    # SHIFT.exe vtable here produced large false-positive families from
    # unrelated classes that happened to expose compatible float/integer
    # payloads.
    if (
        vt != KNOWN_VTABLES["AIPolylinePath"]
        or any(v is None for v in d.values())
        or not game_vtable(vt, mm, starts)
    ):
        return None
    am = writable(d["array"], mm, starts)
    if not am or not 2 <= d["nodes"] <= 1000000 or d["cyclic"] not in (0, 1):
        return None
    if not all(finite(d[k]) for k in ("length", "width", "spacing", "default_width")):
        return None
    if not (0 < d["length"] <= 1e7 and 0 < d["spacing"] <= 1e5):
        return None
    if not (0 < d["width"] <= 1e5 and 0 < d["default_width"] <= 1e5):
        return None
    return {"address": addr, "vtable": vt, "vtable_mapping": game_vtable(vt, mm, starts), **d, "array_mapping": am}


def scan(blob: bytes | memoryview, start: int, mm: list[dict], starts: list[int]) -> dict[str, list[dict]]:
    """Scan aligned object starts in one in-memory chunk.

    The caller may pass a small streaming chunk. Only a fixed-size view around
    each candidate is exposed to the structure validators, so scan cost and
    memory use stay proportional to the chunk instead of the full capture.
    """
    found = {
        "Path": [],
        "Incident.PathOwner": [],
        "AISegmentPath": [],
        "AIPolylinePath": [],
        "AIPolyPathNode": [],
    }
    checks = (
        ("Path", check_path),
        ("Incident.PathOwner", check_incident),
        ("AISegmentPath", check_segment),
        ("AIPolylinePath", check_poly),
        ("AIPolyPathNode", check_poly_node),
    )
    view = memoryview(blob)
    limit = max(0, len(view) - 3)
    known_segment_vtable = KNOWN_VTABLES["AISegmentPath"]
    known_poly_vtable = KNOWN_VTABLES["AIPolylinePath"]
    known_poly_node_vtable = KNOWN_VTABLES["AIPolyPathNode"]
    for off in range(0, limit, 4):
        vtable = read(view, off, "I")
        if vtable is None:
            continue
        if vtable not in (known_segment_vtable, known_poly_vtable, known_poly_node_vtable):
            if not (VT_RANGE[0] <= vtable < VT_RANGE[1]):
                continue
            if not game_vtable(vtable, mm, starts):
                continue
        chunk = view[off:off + MAX_STRUCTURE_SIZE]
        addr = start + off
        for name, fn in checks:
            row = fn(chunk, addr, mm, starts)
            if row:
                found[name].append(row)
    return found


def scan_file(path: Path, start: int, mm: list[dict], starts: list[int]) -> dict[str, list[dict]]:
    """Scan a region file incrementally, preserving candidates across boundaries."""
    merged: dict[str, dict[int, dict]] = {
        "Path": {},
        "Incident.PathOwner": {},
        "AISegmentPath": {},
        "AIPolylinePath": {},
        "AIPolyPathNode": {},
    }
    carry = b""
    base = 0

    with path.open("rb") as f:
        while True:
            raw = f.read(SCAN_CHUNK_SIZE)
            if not raw:
                break

            data = carry + raw
            chunk_start = start + base - len(carry)
            found = scan(data, chunk_start, mm, starts)
            for name, rows in found.items():
                for row in rows:
                    merged[name][int(row["address"])] = row

            carry = data[-SCAN_OVERLAP:]
            base += len(raw)

    return {
        name: sorted(rows.values(), key=lambda r: r["address"])
        for name, rows in merged.items()
    }


def stable_pointers(
    sns: list[Path],
    indexes: list[dict[int, dict]],
    mm: list[dict],
    starts: list[int],
    excluded_sources: list[tuple[int, int]] | None = None,
) -> list[dict]:
    """Find stable 32-bit pointers without loading every region into RAM."""
    excluded_sources = excluded_sources or []
    common = set(indexes[0])
    for idx in indexes[1:]:
        common &= set(idx)
    selected = [(int(r["start"]), int(r["end"])) for r in indexes[0].values()]
    counts = Counter()
    refs: dict[int, list[int]] = {}

    for start in sorted(common):
        rs = [idx[start] for idx in indexes]
        if any(int(x["size"]) != int(rs[0]["size"]) for x in rs):
            continue

        paths = [(s / r["file"]) for s, r in zip(sns, rs)]
        n = min(int(r["size"]) for r in rs)
        handles = [p.open("rb") for p in paths]
        try:
            for block_base in range(0, n, POINTER_CHUNK_SIZE):
                block_size = min(POINTER_CHUNK_SIZE, n - block_base)
                blocks = [h.read(block_size) for h in handles]
                if any(len(block) != block_size for block in blocks):
                    break

                for off in range(0, block_size - 3, 4):
                    source_address = start + block_base + off
                    if in_ranges(source_address, excluded_sources):
                        continue

                    first = struct.unpack_from("<I", blocks[0], off)[0]
                    if not first:
                        continue
                    if any(struct.unpack_from("<I", block, off)[0] != first for block in blocks[1:]):
                        continue
                    v = first
                    if any(a <= v < b for a, b in selected):
                        continue
                    m = mapping(v, mm, starts)
                    if not m or "w" not in m["perms"] or v % 4:
                        continue
                    counts[v] += 1
                    refs.setdefault(v, []).append(source_address)
        finally:
            for handle in handles:
                handle.close()

    rows = []
    for v, c in counts.items():
        src = sorted(set(refs[v]))
        deltas = [b - a for a, b in zip(src, src[1:]) if 4 <= b - a <= 0x10000]
        stride, stride_count = Counter(deltas).most_common(1)[0] if deltas else (0, 0)
        m = mapping(v, mm, starts)
        rows.append({
            "target": v,
            "count": c,
            "mapping_start": m["start"],
            "mapping_end": m["end"],
            "mapping_perms": m["perms"],
            "sources": src[:128],
            "source_stride": stride,
            "source_stride_count": stride_count,
            "score": float(c),
        })
    return rows


def path_root_targets(
    candidates: list[dict],
    maps_list: list[dict],
    starts: list[int],
    snapshot_count: int,
    top: int,
) -> list[dict]:
    grouped: dict[int, dict] = {}
    for row in candidates:
        if row.get("stable_snapshots") != snapshot_count:
            continue
        target = int(row.get("start_node", 0))
        if target == 0:
            continue
        target_mapping = mapping(target, maps_list, starts)
        if not target_mapping or "w" not in target_mapping.get("perms", ""):
            continue
        entry = grouped.setdefault(
            target,
            {
                "target": target,
                "candidate_addresses": [],
                "candidate_count": 0,
                "mapping_start": target_mapping["start"],
                "mapping_end": target_mapping["end"],
                "mapping_perms": target_mapping["perms"],
            },
        )
        entry["candidate_count"] += 1
        entry["candidate_addresses"].append(int(row["address"]))

    rows = list(grouped.values())
    rows.sort(key=lambda r: (-r["candidate_count"], r["target"]))
    for row in rows:
        row["candidate_addresses"] = json.dumps(
            [f"0x{x:x}" for x in sorted(set(row["candidate_addresses"]))],
            separators=(",", ":"),
        )
    return rows[:top]


def windows_for_path_roots(rows: list[dict], radius: int, top: int) -> list[dict]:
    intervals = []
    for row in rows[:top]:
        target = int(row["target"])
        intervals.append((max(0, target - radius), target + radius, target))
    intervals.sort()
    merged: list[list[int]] = []
    refs: list[list[int]] = []
    for start, end, target in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
            refs.append([target])
        else:
            merged[-1][1] = max(merged[-1][1], end)
            refs[-1].append(target)

    out = []
    for (start, end), targets in zip(merged, refs):
        out.append({
            "start": start,
            "size": end - start,
            "targets": sorted(set(targets)),
        })
    return out


def _region_record_for_address(
    address: int,
    region_index: dict[int, dict],
    starts: list[int],
) -> tuple[int, dict] | None:
    i = bisect_right(starts, address) - 1
    if i < 0:
        return None
    st = starts[i]
    rec = region_index.get(st)
    if rec is None:
        return None
    if st <= address < st + int(rec["size"]):
        return st, rec
    return None


def _read_virtual(
    snapshot: Path,
    region_index: dict[int, dict],
    starts: list[int],
    address: int,
    size: int,
) -> bytes | None:
    if address < 0 or size <= 0:
        return None
    loc = _region_record_for_address(address, region_index, starts)
    if loc is None:
        return None
    st, rec = loc
    within = address - st
    if within + size > int(rec["size"]):
        return None
    path = snapshot / rec["file"]
    try:
        with path.open("rb") as fh:
            fh.seek(within)
            data = fh.read(size)
    except OSError:
        return None
    return data if len(data) == size else None


def validate_prefixed_array_link(
    candidates: list[dict],
    snapshots: list[Path],
    indexes: list[dict[int, dict]],
    vtable: int,
    stride: int,
    count_field: str,
    sequence_field: str,
) -> None:
    """Validate count-prefixed, fixed-stride arrays referenced by containers."""
    if not candidates or not snapshots:
        return
    region_starts = [sorted(idx.keys()) for idx in indexes]
    for row in candidates:
        array = int(row.get("array", 0))
        expected = int(row.get("nodes", 0))
        if array < 4 or expected < 1:
            row.update({
                count_field: None,
                f"{count_field}_stable": False,
                sequence_field: 0,
                f"{sequence_field}_complete": False,
                "array_link_available": False,
            })
            continue
        counts: list[int] = []
        sequences: list[int] = []
        for snap, idx, starts in zip(snapshots, indexes, region_starts):
            count_blob = _read_virtual(snap, idx, starts, array - 4, 4)
            if count_blob is None:
                continue
            count = struct.unpack_from("<I", count_blob)[0]
            counts.append(count)

            check_count = min(count, 256)
            seq = 0
            loc = _region_record_for_address(array, idx, starts)
            if loc and check_count > 0:
                st, rec = loc
                wanted = check_count * stride
                within = array - st
                if within + wanted <= int(rec["size"]):
                    blob = _read_virtual(snap, idx, starts, array, wanted)
                    if blob is not None:
                        for n in range(check_count):
                            off = n * stride
                            if off + 4 > len(blob):
                                break
                            if struct.unpack_from("<I", blob, off)[0] != vtable:
                                break
                            seq += 1
            sequences.append(seq)
        count = Counter(counts).most_common(1)[0][0] if counts else None
        seq = max(sequences) if sequences else 0
        row.update({
            count_field: count,
            f"{count_field}_stable": bool(counts and len(set(counts)) == 1),
            sequence_field: seq,
            f"{sequence_field}_complete": bool(
                counts and sequences and len(sequences) == len(counts)
                and all(s == c for s, c in zip(sequences, counts))
            ),
            "array_link_available": bool(counts),
            "array_element_vtable": vtable if seq else None,
            "array_element_stride": stride,
            "array_expected_count": expected,
            "array_expected_count_match": bool(count is not None and count == expected),
        })

def extract_polyline_nodes(
    candidates: list[dict],
    snapshot: Path,
    region_index: dict[int, dict],
    max_nodes: int = 100000,
) -> list[dict]:
    """Decode validated AIPolyPathNode arrays from the reference snapshot.

    Only candidates with a matching count prefix and the concrete node vtable
    are exported. Nodes are read in compact chunks so a malformed count cannot
    force an unbounded allocation.
    """
    rows: list[dict] = []
    starts = sorted(region_index)
    for owner in candidates:
        if not owner.get("array_link_available"):
            continue
        if not owner.get("array_count_match") or not owner.get("array_node_vtable_match"):
            continue
        array = int(owner.get("array", 0))
        count = int(owner.get("array_count", 0))
        count = min(count, max_nodes)
        if array <= 0 or count <= 0:
            continue
        loc = _region_record_for_address(array, region_index, starts)
        if loc is None:
            continue
        st, rec = loc
        within = array - st
        total = count * 0x24
        if within + total > int(rec["size"]):
            count = max(0, (int(rec["size"]) - within) // 0x24)
        if count <= 0:
            continue
        path = snapshot / rec["file"]
        try:
            with path.open("rb") as fh:
                fh.seek(within)
                remaining = count
                index = 0
                while remaining:
                    batch_count = min(remaining, 4096)
                    data = fh.read(batch_count * 0x24)
                    full = len(data) // 0x24
                    if full == 0:
                        break
                    for n in range(full):
                        off = n * 0x24
                        vt = struct.unpack_from("<I", data, off)[0]
                        if vt != KNOWN_VTABLES["AIPolyPathNode"]:
                            remaining = 0
                            break
                        x, y, dx, dy, distance = struct.unpack_from("<fffff", data, off + 0x10)
                        if not all(finite(v, 1e7) for v in (x, y, dx, dy, distance)) or distance < 0:
                            remaining = 0
                            break
                        rows.append({
                            "path_address": int(owner["address"]),
                            "array_address": array,
                            "index": index + n,
                            "address": array + (index + n) * 0x24,
                            "vtable": vt,
                            "x": x,
                            "y": y,
                            "dx": dx,
                            "dy": dy,
                            "distance": distance,
                        })
                    index += full
                    remaining -= full
                    if full < batch_count:
                        break
        except OSError:
            continue
    return rows

def resolve_path_start_nodes(
    candidates: list[dict],
    snapshots: list[Path],
    indexes: list[dict[int, dict]],
    maps_list: list[dict],
) -> list[dict]:
    """Resolve Path.StartNode targets and classify concrete runtime node arrays.

    Path.StartNode is a direct pointer field recovered from SHIFT.exe.c. When
    it points at an AIPolyPathNode, array[-4] carries the node count and the
    following elements use the fixed 0x24-byte stride. This pass records that
    relation independently of generic stable-pointer clustering.
    """
    out: list[dict] = []
    if not candidates or not snapshots:
        return out
    starts_by_snapshot = [sorted(idx.keys()) for idx in indexes]
    for path_row in candidates:
        target = int(path_row.get("start_node", 0))
        if not target:
            continue
        first_vtables: list[int] = []
        counts: list[int] = []
        sequences: list[int] = []
        for snap, idx, starts in zip(snapshots, indexes, starts_by_snapshot):
            blob = _read_virtual(snap, idx, starts, target, 4)
            if blob is None:
                continue
            first_vtables.append(struct.unpack_from("<I", blob)[0])

            count_blob = _read_virtual(snap, idx, starts, target - 4, 4)
            if count_blob is None:
                continue
            count = struct.unpack_from("<I", count_blob)[0]
            counts.append(count)

            check_count = min(count, 256)
            seq = 0
            loc = _region_record_for_address(target, idx, starts)
            if loc and check_count > 0:
                st, rec = loc
                wanted = check_count * 0x24
                within = target - st
                if within + wanted <= int(rec["size"]):
                    nodes_blob = _read_virtual(
                        snap, idx, starts, target, wanted
                    )
                    if nodes_blob is not None:
                        for n in range(check_count):
                            off = n * 0x24
                            if off + 4 > len(nodes_blob):
                                break
                            vt = struct.unpack_from("<I", nodes_blob, off)[0]
                            if vt != KNOWN_VTABLES["AIPolyPathNode"]:
                                break
                            seq += 1
            sequences.append(seq)
        row = {
            "path_address": int(path_row["address"]),
            "start_node": target,
            "target_vtable": first_vtables[0] if first_vtables else None,
            "target_vtable_match": bool(
                first_vtables and
                all(v == KNOWN_VTABLES["AIPolyPathNode"] for v in first_vtables)
            ),
            "link_type": (
                "AIPolyPathNodeArray"
                if first_vtables and
                all(v == KNOWN_VTABLES["AIPolyPathNode"] for v in first_vtables)
                else "unknown"
            ),
            "array_count": Counter(counts).most_common(1)[0][0] if counts else None,
            "array_count_stable": bool(counts and len(set(counts)) == 1),
            "node_sequence": max(sequences) if sequences else 0,
            "node_sequence_complete": bool(
                counts and sequences and
                len(sequences) == len(counts) and
                all(seq == count for seq, count in zip(sequences, counts))
            ),
            "stable_snapshots": len(first_vtables),
            "target_mapping_start": None,
            "target_mapping_end": None,
            "target_mapping_perms": None,
        }
        target_mapping = mapping(target, maps_list, [r["start"] for r in maps_list])
        if target_mapping:
            row["target_mapping_start"] = target_mapping["start"]
            row["target_mapping_end"] = target_mapping["end"]
            row["target_mapping_perms"] = target_mapping["perms"]
        out.append(row)
    out.sort(key=lambda r: (not r["target_vtable_match"], -int(r["node_sequence"]), r["start_node"]))
    return out

def clusters(rows: list[dict], gap: int = 0x10000) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["target"])
    out: list[dict] = []
    cur = None
    for r in rows:
        if (
            cur is None
            or r["mapping_start"] != cur["mapping_start"]
            or r["target"] - cur["end"] > gap
        ):
            if cur:
                out.append(cur)
            cur = {
                "start": r["target"],
                "end": r["target"],
                "targets": [],
                "sources": [],
                "mapping_start": r["mapping_start"],
                "mapping_end": r["mapping_end"],
                "mapping_perms": r["mapping_perms"],
            }
        cur["end"] = r["target"]
        cur["targets"].append(r)
        cur["sources"].extend(r["sources"])
    if cur:
        out.append(cur)

    result = []
    for c in out:
        ts = c["targets"]
        src = sorted(set(c["sources"]))
        deltas = [b - a for a, b in zip(src, src[1:]) if 4 <= b - a <= 0x10000]
        stride, stride_count = Counter(deltas).most_common(1)[0] if deltas else (0, 0)
        score = 2 * len(ts) + (1.5 * min(stride_count, 64) if stride_count >= 8 else 0)
        result.append({
            "score": round(score, 4),
            "start": c["start"],
            "end": c["end"] + 1,
            "span": c["end"] - c["start"] + 1,
            "target_count": len(ts),
            "source_count": len(src),
            "source_stride": stride,
            "source_stride_count": stride_count,
            "mapping_start": c["mapping_start"],
            "mapping_end": c["mapping_end"],
            "mapping_perms": c["mapping_perms"],
            "target_samples": [t["target"] for t in ts[:64]],
        })
    return sorted(result, key=lambda r: (-r["score"], -r["target_count"], r["start"]))


# ---------------------------------------------------------------------------
# Static AIW correlation
# ---------------------------------------------------------------------------

_VEC_RE = re.compile(r"^\(([^)]*)\)$")
_INT_RE = re.compile(r"-?\d+")


def _parse_vector(value: str, size: int) -> tuple[float, ...] | None:
    m = _VEC_RE.match(value.strip())
    if not m:
        return None
    try:
        items = tuple(float(x.strip()) for x in m.group(1).split(","))
    except ValueError:
        return None
    return items if len(items) == size else None


def _parse_int_tuple(value: str, size: int) -> tuple[int, ...] | None:
    m = _VEC_RE.match(value.strip())
    if not m:
        return None
    values = _INT_RE.findall(m.group(1))
    if len(values) != size:
        return None
    return tuple(int(x) for x in values)


def parse_aiw(text: str, source: str) -> dict:
    """Parse the text-based [Waypoint] section from an AIW track resource."""
    in_waypoints = False
    meta: dict[str, object] = {}
    waypoints: list[dict] = []
    current: dict | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "[Waypoint]":
            in_waypoints = True
            current = None
            continue
        if in_waypoints and line.startswith("[") and line.endswith("]"):
            break
        if not in_waypoints or not line:
            continue
        # Real SHIFT/Madness AIW archives use both one and two leading
        # backslashes before waypoint indices. Normalize the marker first.
        marker = line.lstrip("\\")
        if marker and marker.strip("-").isdigit() and line.startswith("\\"):
            current = {"index": int(marker)}
            waypoints.append(current)
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split("//", 1)[0].strip()

        if current is None:
            if key in ("number_waypoints", "trackstate"):
                try:
                    meta[key] = int(value, 0)
                except ValueError:
                    pass
            elif key in ("lap_length", "sector_1_length", "sector_2_length"):
                try:
                    meta[key] = float(value)
                except ValueError:
                    pass
            continue

        if key in ("wp_pos", "wp_perp", "wp_width", "wp_dwidth", "wp_path", "wp_event"):
            size = {
                "wp_pos": 3, "wp_perp": 3, "wp_width": 4,
                "wp_dwidth": 4, "wp_path": 2, "wp_event": 3,
            }[key]
            parsed = _parse_vector(value, size)
            if parsed is not None:
                current[key] = parsed
        elif key == "WP_PTRS":
            parsed = _parse_int_tuple(value, 4)
            if parsed is not None:
                current[key] = parsed
        elif key == "wp_score":
            parsed = _parse_vector(value, 2)
            if parsed is not None:
                current[key] = parsed
        elif key in ("wp_branchID", "wp_bitfields", "wpd_CornerType", "wpd_CornerState"):
            try:
                current[key] = int(value.strip("()"), 0)
            except ValueError:
                pass

    declared = int(meta.get("number_waypoints", len(waypoints)))
    if len(waypoints) != declared:
        raise ValueError(
            f"{source}: AIW declares {declared} waypoints but parsed {len(waypoints)}"
        )

    normalized = []
    for row in waypoints:
        pos = row.get("wp_pos")
        ptrs = row.get("WP_PTRS")
        score = row.get("wp_score", (0.0, 0.0))
        event = row.get("wp_event", (0.0, 0.0, 0.0))
        normalized.append({
            "source": source,
            "index": int(row["index"]),
            "x": float(pos[0]) if pos else None,
            "y": float(pos[1]) if pos else None,
            "z": float(pos[2]) if pos else None,
            "branch_id": int(row.get("wp_branchID", 0)),
            "bitfields": int(row.get("wp_bitfields", 0)),
            "prev": int(ptrs[0]) if ptrs else -1,
            "next": int(ptrs[1]) if ptrs else -1,
            "alt": int(ptrs[2]) if ptrs else -1,
            "link_flags": int(ptrs[3]) if ptrs else 0,
            "sector": int(score[0]) if score else 0,
            "lap_distance": float(score[1]) if score else 0.0,
            "corner_speed": float(event[0]) if event else 0.0,
            "special_event": int(event[1]) if event else 0,
            "special_data": float(event[2]) if event else 0.0,
        })

    return {
        "source": source,
        "number_waypoints": declared,
        "lap_length": float(meta.get("lap_length", 0.0)),
        "sector_1_length": float(meta.get("sector_1_length", 0.0)),
        "sector_2_length": float(meta.get("sector_2_length", 0.0)),
        "waypoints": normalized,
    }


def _load_bff_aiws(path: Path, entry_pattern: str | None) -> list[dict]:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from shift_importer import BFF

    docs = []
    with BFF(path) as bff:
        for entry in bff.entries:
            name = entry.path.replace("\\", "/")
            if not name.lower().endswith(".aiw"):
                continue
            if entry_pattern and not re.search(entry_pattern, name, re.IGNORECASE):
                continue
            payload = bff.extract_entry(entry)
            docs.append(parse_aiw(payload.decode("utf-8", "replace"), f"{path.name}:{name}"))
    return docs


def load_aiw_sources(path: Path, entry_pattern: str | None = None) -> list[dict]:
    """Load AIW resources from .aiw, .bff, .zip, or a directory."""
    suffix = path.suffix.lower()
    if suffix == ".aiw":
        return [parse_aiw(path.read_text(encoding="utf-8", errors="replace"), path.name)]
    if suffix == ".bff":
        return _load_bff_aiws(path, entry_pattern)
    if suffix == ".zip":
        docs = []
        with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory(prefix="shift-aiw-") as td:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                lower = name.lower()
                if lower.endswith(".aiw"):
                    if entry_pattern and not re.search(entry_pattern, name, re.IGNORECASE):
                        continue
                    docs.append(parse_aiw(zf.read(info).decode("utf-8", "replace"), f"{path.name}:{name}"))
                elif lower.endswith(".bff"):
                    temp = Path(td) / Path(name).name
                    temp.write_bytes(zf.read(info))
                    docs.extend(_load_bff_aiws(temp, entry_pattern))
        return docs
    if path.is_dir():
        docs = []
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() in (".aiw", ".bff", ".zip"):
                docs.extend(load_aiw_sources(child, entry_pattern))
        return docs
    raise ValueError(f"{path}: expected .aiw, .bff, .zip, or directory")


def _quantize(value: float, tolerance: float) -> int:
    return int(math.floor(value / tolerance + 0.5))


def _position_key(x: float, y: float, z: float, tolerance: float) -> tuple[int, int, int]:
    return (_quantize(x, tolerance), _quantize(y, tolerance), _quantize(z, tolerance))


def _position_key2(x: float, y: float, tolerance: float) -> tuple[int, int]:
    return (_quantize(x, tolerance), _quantize(y, tolerance))


def correlate_aiw_runtime(
    sns: list[Path],
    indexes: list[dict[int, dict]],
    aiw_docs: list[dict],
    scan_ranges: list[tuple[int, int]],
    tolerance: float,
    runtime_roots: list[int] | None = None,
    runtime_nodes: list[dict] | None = None,
    node_plane: str = "xz",
) -> tuple[list[dict], list[dict]]:
    """Find AIW waypoint positions in the selected runtime capture ranges."""
    if not aiw_docs:
        return [], []

    pos_index: dict[tuple[int, int, int], list[tuple[int, int, dict]]] = {}
    for doc_id, doc in enumerate(aiw_docs):
        for wp in doc["waypoints"]:
            if None in (wp["x"], wp["y"], wp["z"]):
                continue
            pos_index.setdefault(
                _position_key(wp["x"], wp["y"], wp["z"], tolerance),
                [],
            ).append((doc_id, wp["index"], wp))

    common = set(indexes[0])
    for idx in indexes[1:]:
        common &= set(idx)

    # A small neighborhood avoids missing a float that rounds on the other
    # side of a tolerance bucket while keeping the scan linear in capture size.
    candidate_keys = {}
    for key in pos_index:
        candidate_keys[key] = [
            (key[0] + dx, key[1] + dy, key[2] + dz)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
        ]

    node_pos_index: dict[tuple[int, int], list[tuple[int, int, dict]]] = {}
    for doc_id, doc in enumerate(aiw_docs):
        for wp in doc["waypoints"]:
            if None in (wp["x"], wp["y"], wp["z"]):
                continue
            if node_plane == "xz":
                coords = (wp["x"], wp["z"])
            elif node_plane == "xy":
                coords = (wp["x"], wp["y"])
            else:
                coords = (wp["y"], wp["z"])
            node_pos_index.setdefault(
                _position_key2(coords[0], coords[1], tolerance),
                [],
            ).append((doc_id, wp["index"], wp))

    node_candidate_keys = {}
    for key in node_pos_index:
        node_candidate_keys[key] = [
            (key[0] + dx, key[1] + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        ]

    matches: list[dict] = []
    seen: set[tuple[str, int, int]] = set()

    node_matches = False
    for row in runtime_nodes or []:
        if row.get("stable_snapshots") is not None and int(row["stable_snapshots"]) != len(sns):
            continue
        address = int(row["address"])
        if scan_ranges and not any(a <= address < b for a, b in scan_ranges):
            continue
        nx, ny = row.get("x"), row.get("y")
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in (nx, ny)):
            continue
        key = _position_key2(float(nx), float(ny), tolerance)
        for nearby in node_candidate_keys.get(key, ()):
            for doc_id, wp_index, wp in node_pos_index.get(nearby, ()):
                if node_plane == "xz":
                    wx, wz = wp["x"], wp["z"]
                    rx, rz = float(nx), float(ny)
                    runtime_xyz = (rx, None, rz)
                elif node_plane == "xy":
                    wx, wz = wp["x"], wp["y"]
                    rx, rz = float(nx), float(ny)
                    runtime_xyz = (rx, rz, None)
                else:
                    wx, wz = wp["y"], wp["z"]
                    rx, rz = float(nx), float(ny)
                    runtime_xyz = (None, rx, rz)
                plane_distance = math.hypot(rx - wx, rz - wz)
                if plane_distance > tolerance:
                    continue
                ident = (wp["source"], wp_index, address)
                if ident in seen:
                    continue
                seen.add(ident)
                node_matches = True
                node_distance = row.get("distance")
                distance_delta = None
                if isinstance(node_distance, (int, float)) and math.isfinite(float(node_distance)):
                    distance_delta = float(node_distance) - float(wp.get("lap_distance", 0.0))
                matches.append({
                    "aiw_source": wp["source"],
                    "waypoint_index": wp_index,
                    "branch_id": wp["branch_id"],
                    "runtime_address": address,
                    "region_start": int(row.get("region_start", address)),
                    "region_offset": address - int(row.get("region_start", address)),
                    "distance": plane_distance,
                    "x": runtime_xyz[0],
                    "y": runtime_xyz[1],
                    "z": runtime_xyz[2],
                    "runtime_source": "AIPolyPathNode",
                    "position_plane": node_plane,
                    "lap_distance": node_distance,
                    "lap_distance_delta": distance_delta,
                })

    for st in sorted(common):
        rec = indexes[0][st]
        size = int(rec["size"])
        if node_matches:
            continue
        if scan_ranges and not any(max(st, a) < min(st + size, b) for a, b in scan_ranges):
            continue
        blob = (sns[0] / rec["file"]).read_bytes()
        local_ranges = [
            (max(0, a - st), min(len(blob), b - st))
            for a, b in scan_ranges
            if max(st, a) < min(st + len(blob), b)
        ] if scan_ranges else [(0, len(blob))]

        for lo, hi in local_ranges:
            lo = max(0, lo - lo % 4)
            hi = min(len(blob), hi)
            for off in range(lo, max(lo, hi - 11), 4):
                try:
                    x, y, z = struct.unpack_from("<fff", blob, off)
                except struct.error:
                    break
                if not all(finite(v, 1e7) for v in (x, y, z)):
                    continue
                key = _position_key(x, y, z, tolerance)
                for nearby in candidate_keys.get(key, ()):
                    for doc_id, wp_index, wp in pos_index.get(nearby, ()):
                        dx, dy, dz = x - wp["x"], y - wp["y"], z - wp["z"]
                        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                        if distance > tolerance:
                            continue
                        ident = (wp["source"], wp_index, st + off)
                        if ident in seen:
                            continue
                        seen.add(ident)
                        matches.append({
                            "aiw_source": wp["source"],
                            "waypoint_index": wp_index,
                            "branch_id": wp["branch_id"],
                            "runtime_address": st + off,
                            "region_start": st,
                            "region_offset": off,
                            "distance": distance,
                            "x": x, "y": y, "z": z,
                            "runtime_source": "float3",
                            "position_plane": "xyz",
                            "lap_distance": None,
                            "lap_distance_delta": None,
                        })

    sequences: list[dict] = []
    by_source: dict[str, list[dict]] = {}
    for row in matches:
        if row["branch_id"] == 0:
            by_source.setdefault(row["aiw_source"], []).append(row)

    for source, rows in by_source.items():
        by_wp: dict[int, list[int]] = {}
        for row in rows:
            by_wp.setdefault(row["waypoint_index"], []).append(row["runtime_address"])

        source_doc = next(d for d in aiw_docs if d["source"] == source)
        waypoint_next = {
            int(wp["index"]): int(wp.get("next", -1))
            for wp in source_doc["waypoints"]
        }

        # Follow the explicit AIW graph edge. Numeric waypoint ids are not
        # guaranteed to be contiguous, especially around branches/cuts.
        delta_counts = Counter()
        for i, addresses in by_wp.items():
            next_index = waypoint_next.get(i, -1)
            if next_index not in by_wp:
                continue
            for nxt in by_wp[next_index]:
                for address in addresses:
                    delta = nxt - address
                    if 4 <= abs(delta) <= 0x10000:
                        delta_counts[delta] += 1
        if not delta_counts:
            continue

        stride, stride_count = delta_counts.most_common(1)[0]
        chains = []
        for start_wp in sorted(by_wp):
            current = start_wp
            first_addr = by_wp[start_wp][0]
            last_addr = first_addr
            count = 1
            visited = set()
            while current not in visited:
                visited.add(current)
                next_index = waypoint_next.get(current, -1)
                if next_index in visited:
                    break
                candidates = [
                    address for address in by_wp.get(next_index, ())
                    if address - last_addr == stride
                ]
                if not candidates:
                    break
                last_addr = candidates[0]
                current = next_index
                count += 1
            if count >= 4:
                chains.append((count, start_wp, current, first_addr, last_addr))

        if chains:
            count, first_wp, last_wp, first_addr, last_addr = max(chains)
            root = None
            position_offset = None
            if runtime_roots:
                nearest = min(runtime_roots, key=lambda r: abs(first_addr - r))
                if abs(first_addr - nearest) <= 0x1000:
                    root = nearest
                    position_offset = first_addr - nearest
            sequences.append({
                "aiw_source": source,
                "first_waypoint": first_wp,
                "last_waypoint": last_wp,
                "matched_waypoints": count,
                "runtime_start": first_addr,
                "runtime_end": last_addr,
                "runtime_root": root,
                "position_offset": position_offset,
                "stride": stride,
                "stride_count": stride_count,
                "coverage": count / max(1, len(by_wp)),
            })

    sequences.sort(key=lambda r: (-r["matched_waypoints"], -r["stride_count"], r["aiw_source"]))
    return matches, sequences


def build_aiw_runtime_edges(aiw_docs: list[dict], matches: list[dict]) -> list[dict]:
    """Map explicit AIW next edges onto matched runtime waypoint addresses."""
    by_source_wp: dict[tuple[str, int], list[dict]] = {}
    for row in matches:
        by_source_wp.setdefault(
            (row["aiw_source"], int(row["waypoint_index"])), []
        ).append(row)

    edges: list[dict] = []
    for doc in aiw_docs:
        by_index = {int(wp["index"]): wp for wp in doc["waypoints"]}
        for wp in doc["waypoints"]:
            source_index = int(wp["index"])
            target_index = int(wp.get("next", -1))
            if target_index not in by_index:
                continue
            src_rows = by_source_wp.get((doc["source"], source_index), [])
            dst_rows = by_source_wp.get((doc["source"], target_index), [])
            for src in src_rows:
                for dst in dst_rows:
                    edges.append({
                        "aiw_source": doc["source"],
                        "from_waypoint": source_index,
                        "to_waypoint": target_index,
                        "from_runtime_address": int(src["runtime_address"]),
                        "to_runtime_address": int(dst["runtime_address"]),
                        "runtime_delta": (
                            int(dst["runtime_address"])
                            - int(src["runtime_address"])
                        ),
                        "branch_id": int(wp.get("branch_id", 0)),
                        "link_flags": int(wp.get("link_flags", 0)),
                        "position_match_error": (
                            float(src.get("distance", 0.0))
                            + float(dst.get("distance", 0.0))
                        ),
                    })
    edges.sort(key=lambda r: (
        r["aiw_source"], r["from_waypoint"], r["to_waypoint"],
        r["from_runtime_address"], r["to_runtime_address"],
    ))
    return edges


def build_aiw_next_edges(aiw_docs: list[dict]) -> list[dict]:
    """Normalize explicit AIW WP_PTRS next links into an edge list."""
    edges: list[dict] = []
    for doc in aiw_docs:
        by_index = {int(wp["index"]): wp for wp in doc["waypoints"]}
        for wp in doc["waypoints"]:
            source_index = int(wp["index"])
            target_index = int(wp.get("next", -1))
            if target_index not in by_index:
                continue
            target = by_index[target_index]
            edges.append({
                "aiw_source": doc["source"],
                "from_waypoint": source_index,
                "to_waypoint": target_index,
                "branch_id": int(wp.get("branch_id", 0)),
                "link_flags": int(wp.get("link_flags", 0)),
                "from_lap_distance": float(wp.get("lap_distance", 0.0)),
                "to_lap_distance": float(target.get("lap_distance", 0.0)),
                "lap_distance_delta": (
                    float(target.get("lap_distance", 0.0))
                    - float(wp.get("lap_distance", 0.0))
                ),
            })
    return edges


def write_csv(path: Path, rows: list[dict], keys: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            q = dict(r)
            for k, v in q.items():
                if isinstance(v, (dict, list)):
                    q[k] = json.dumps(v, separators=(",", ":"))
            w.writerow(q)


def main() -> int:
    ap = argparse.ArgumentParser(description="Find SHIFT track/path runtime structure candidates")
    ap.add_argument("root", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--target-top", type=int, default=20)
    ap.add_argument("--radius-kib", type=int, default=128)
    ap.add_argument("--path-root-top", type=int, default=16)
    ap.add_argument("--path-root-radius-kib", type=int, default=128)
    ap.add_argument(
        "--exclude-source-range", dest="exclude_source_ranges", action="append",
        type=parse_range,
        help="exclude stable-pointer source addresses in START:SIZE intervals; repeatable",
    )
    ap.add_argument(
        "--skip-pointer-analysis", action="store_true",
        help="skip the full-capture stable-pointer scan; useful for Path/StartNode-only analysis",
    )
    ap.add_argument(
        "--aiw", dest="aiw_sources", action="append", type=Path,
        help="correlate runtime memory with AIW waypoint positions; accepts .aiw, .bff, .zip, or directory",
    )
    ap.add_argument(
        "--aiw-entry",
        help="optional case-insensitive regex selecting AIW entries inside BFF/ZIP sources",
    )
    ap.add_argument(
        "--aiw-range", dest="aiw_ranges", action="append", type=parse_range,
        help="restrict AIW position correlation to START:SIZE ranges; repeatable",
    )
    ap.add_argument(
        "--runtime-root", dest="runtime_roots", action="append", type=lambda v: int(v, 0),
        help="heap root to scan for AIW positions; repeatable",
    )
    ap.add_argument(
        "--aiw-root-radius-kib", type=int, default=128,
        help="scan radius around --runtime-root (default 128 KiB)",
    )
    ap.add_argument(
        "--aiw-position-tolerance", type=float, default=0.05,
        help="maximum position difference in world units (default 0.05)",
    )
    ap.add_argument(
        "--aiw-node-plane", choices=("xz", "xy", "yz"), default="xz",
        help="2D plane used when correlating AIPolyPathNode candidates with AIW positions (default: xz)",
    )
    args = ap.parse_args()
    if min(args.top, args.target_top, args.path_root_top) <= 0 or min(
        args.radius_kib, args.path_root_radius_kib, args.aiw_root_radius_kib
    ) < 0:
        ap.error("invalid numeric option")
    if args.aiw_position_tolerance <= 0:
        ap.error("--aiw-position-tolerance must be > 0")

    sns = snapshots(args.root)
    mans = [load_manifest(s / "manifest.json") for s in sns]
    idx = [{int(r["start"]): r for r in m.get("regions", [])} for m in mans]
    mm = maps(sns[0] / "maps.txt") if (sns[0] / "maps.txt").is_file() else []
    starts = [r["start"] for r in mm]
    common = set(idx[0])
    for x in idx[1:]:
        common &= set(x)

    out = args.out or args.root / "track_path_analysis"
    out.mkdir(parents=True, exist_ok=True)
    candidates = {
        k: [] for k in (
            "Path",
            "Incident.PathOwner",
            "AISegmentPath",
            "AIPolylinePath",
            "AIPolyPathNode",
        )
    }

    common_sorted = sorted(common)
    for index, st in enumerate(common_sorted, 1):
        print(f"[scan] region {index}/{len(common_sorted)} start=0x{st:x}", flush=True)
        rr = [x[st] for x in idx]
        if any(int(r["size"]) != int(rr[0]["size"]) for r in rr):
            continue
        region_path = sns[0] / rr[0]["file"]
        found = scan_file(region_path, st, mm, starts)

        other_paths = [s / r["file"] for s, r in zip(sns[1:], rr[1:])]
        handles = [region_path.open("rb")] + [p.open("rb") for p in other_paths]
        try:
            for name, rows in found.items():
                for row in rows:
                    off = row["address"] - st
                    span = (
                        0x28 if name == "Path"
                        else 0x124 if name == "Incident.PathOwner"
                        else 0x38 if name == "AISegmentPath"
                        else 0x2C if name == "AIPolylinePath"
                        else 0x24
                    )
                    reference_handle = handles[0]
                    reference_handle.seek(off)
                    reference = reference_handle.read(span)
                    stable = 1 if len(reference) == span else 0

                    for handle in handles[1:]:
                        handle.seek(off)
                        other = handle.read(span)
                        if len(other) == span and other == reference:
                            stable += 1

                    row.update({
                        "region_start": st,
                        "region_offset": off,
                        "snapshot_count": len(sns),
                        "stable_snapshots": stable,
                    })
                    candidates[name].append(row)
        finally:
            for handle in handles:
                handle.close()

    path_root_candidates = list(candidates["Path"])
    aiw_node_candidates = list(candidates["AIPolyPathNode"])

    # Resolve exact AIPolylinePath -> count-prefixed AIPolyPathNode arrays
    # after the global scan because the target array can live in another
    # selected memory region.
    validate_prefixed_array_link(
        candidates["AIPolylinePath"], sns, idx,
        KNOWN_VTABLES["AIPolyPathNode"], 0x24,
        count_field="array_count", sequence_field="array_node_sequence",
    )
    for row in candidates["AIPolylinePath"]:
        row["array_count_match"] = bool(row.get("array_expected_count_match"))
        row["array_node_vtable"] = row.get("array_element_vtable")
        row["array_node_vtable_match"] = bool(
            row.get("array_element_vtable") == KNOWN_VTABLES["AIPolyPathNode"]
        )
    path_start_node_links = resolve_path_start_nodes(
        candidates["Path"], sns, idx, mm
    )
    polyline_nodes = extract_polyline_nodes(
        candidates["AIPolylinePath"], sns[0], idx[0]
    )
    for k in candidates:
        candidates[k] = sorted(
            candidates[k],
            key=lambda r: (-int(r.get("stable_snapshots", 0)), r["address"]),
        )[:args.top]

    print(
        "[scan] candidates: " + ", ".join(f"{k}={len(v)}" for k, v in candidates.items()),
        flush=True,
    )
    excluded_sources = args.exclude_source_ranges or []
    if args.skip_pointer_analysis:
        print("[pointers] skipped", flush=True)
        ptr = []
    else:
        print("[pointers] scanning stable external pointers", flush=True)
        ptr = stable_pointers(sns, idx, mm, starts, excluded_sources)
    path_roots = path_root_targets(
        path_root_candidates, mm, starts, len(sns), args.path_root_top
    )
    path_root_windows = windows_for_path_roots(
        path_roots, args.path_root_radius_kib * 1024, args.path_root_top
    )

    aiw_docs: list[dict] = []
    aiw_matches: list[dict] = []
    aiw_sequences: list[dict] = []
    aiw_next_edges: list[dict] = []
    aiw_runtime_edges: list[dict] = []
    if args.aiw_sources:
        for source in args.aiw_sources:
            loaded = load_aiw_sources(source, args.aiw_entry)
            if not loaded:
                raise SystemExit(f"no AIW resources found in {source}")
            aiw_docs.extend(loaded)

        corr_ranges = list(args.aiw_ranges or [])
        if not corr_ranges and args.runtime_roots:
            radius = args.aiw_root_radius_kib * 1024
            corr_ranges = [
                (max(0, root - radius), root + radius)
                for root in args.runtime_roots
            ]
        if not corr_ranges:
            total = sum(
                int(idx0[st]["size"])
                for st in common
                for idx0 in [idx[0]]
            )
            if total > 64 * 1024 * 1024:
                raise SystemExit(
                    "AIW correlation requires --aiw-range or --runtime-root "
                    "on captures larger than 64 MiB"
                )

        print(f"[aiw] sources={len(aiw_docs)} ranges={len(corr_ranges)}", flush=True)
        aiw_matches, aiw_sequences = correlate_aiw_runtime(
            sns, idx, aiw_docs, corr_ranges, args.aiw_position_tolerance,
            args.runtime_roots, aiw_node_candidates, args.aiw_node_plane,
        )
        print(
            f"[aiw] matches={len(aiw_matches)} sequences={len(aiw_sequences)}",
            flush=True,
        )
        aiw_next_edges = build_aiw_next_edges(aiw_docs)
        aiw_runtime_edges = build_aiw_runtime_edges(aiw_docs, aiw_matches)

    cl = clusters(ptr)[:args.target_top]
    radius = args.radius_kib * 1024
    raw = [{
        "start": max(0, c["start"] - radius),
        "end": c["end"] + radius,
        "clusters": [i],
        "priority": c["score"],
    } for i, c in enumerate(cl)]

    merged = []
    for w in sorted(raw, key=lambda x: x["start"]):
        if not merged or w["start"] > merged[-1]["end"]:
            merged.append(w)
        else:
            merged[-1]["end"] = max(merged[-1]["end"], w["end"])
            merged[-1]["clusters"] += w["clusters"]
            merged[-1]["priority"] = max(merged[-1]["priority"], w["priority"])

    windows = [{
        "start": w["start"],
        "size": w["end"] - w["start"],
        "clusters": sorted(set(w["clusters"])),
        "priority": w["priority"],
    } for w in merged]
    windows.sort(key=lambda x: (-x["priority"], x["start"]))

    summary = {
        "format": FORMAT,
        "snapshots": len(sns),
        "common_regions": len(common),
        "candidate_counts": {k: len(v) for k, v in candidates.items()},
        "stable_external_pointer_count": len(ptr),
        "pointer_target_clusters": cl,
        "path_root_targets": path_roots,
        "path_root_windows": path_root_windows,
        "next_capture_windows": windows,
        "aiw_sources": [
            {
                "source": d["source"],
                "number_waypoints": d["number_waypoints"],
                "lap_length": d["lap_length"],
            }
            for d in aiw_docs
        ],
        "aiw_match_count": len(aiw_matches),
        "aiw_runtime_sequences": aiw_sequences,
        "aiw_next_edge_count": len(aiw_next_edges),
        "aiw_runtime_edge_count": len(aiw_runtime_edges),
        "polyline_node_count": len(polyline_nodes),
        "path_start_node_link_count": len(path_start_node_links),
        "known_vtables": {k: hex(v) for k, v in KNOWN_VTABLES.items()},
        "excluded_source_ranges": [{"start": a, "end": b} for a, b in excluded_sources],
        "notes": [
            "Reduced captures can show absence only from selected ranges, not from the live process.",
            "Pointer clusters are recommendations; target object identity must be confirmed after capturing their bytes from the original full series.",
        ],
    }
    (out / "track_path_analysis.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for k, v in candidates.items():
        write_csv(out / (k.lower().replace(".", "_") + ".csv"), v, sorted({x for row in v for x in row}))
    write_csv(out / "stable_external_pointers.csv", ptr, [
        "target", "count", "mapping_start", "mapping_end", "mapping_perms",
        "sources", "source_stride", "source_stride_count", "score",
    ])
    write_csv(out / "pointer_target_clusters.csv", cl, [
        "score", "start", "end", "span", "target_count", "source_count",
        "source_stride", "source_stride_count", "mapping_start",
        "mapping_end", "mapping_perms", "target_samples",
    ])
    write_csv(out / "path_start_node_links.csv", path_start_node_links, [
        "path_address", "start_node", "target_vtable", "target_vtable_match",
        "link_type", "array_count", "array_count_stable", "node_sequence",
        "node_sequence_complete", "stable_snapshots", "target_mapping_start",
        "target_mapping_end", "target_mapping_perms",
    ])
    write_csv(out / "aipolylinepath_nodes.csv", polyline_nodes, [
        "path_address", "array_address", "index", "address", "vtable",
        "x", "y", "dx", "dy", "distance",
    ])
    write_csv(out / "path_root_targets.csv", path_roots, [
        "target", "candidate_count", "candidate_addresses",
        "mapping_start", "mapping_end", "mapping_perms",
    ])
    write_csv(out / "path_root_windows.csv", path_root_windows, [
        "start", "size", "targets",
    ])
    (out / "path_root_ranges.txt").write_text(
        "\n".join(
            f"0x{w['start']:x}:0x{w['size']:x}  # targets=" +
            ",".join(f"0x{x:x}" for x in w["targets"])
            for w in path_root_windows
        ) + "\n",
        encoding="utf-8",
    )
    write_csv(out / "aiw_runtime_edges.csv", aiw_runtime_edges, [
        "aiw_source", "from_waypoint", "to_waypoint",
        "from_runtime_address", "to_runtime_address", "runtime_delta",
        "branch_id", "link_flags", "position_match_error",
    ])

    write_csv(out / "aiw_next_edges.csv", aiw_next_edges, [
        "aiw_source", "from_waypoint", "to_waypoint", "branch_id",
        "link_flags", "from_lap_distance", "to_lap_distance", "lap_distance_delta",
    ])

    write_csv(out / "aiw_waypoints.csv", [
        wp for d in aiw_docs for wp in d["waypoints"]
    ], [
        "source", "index", "x", "y", "z", "branch_id", "bitfields",
        "prev", "next", "alt", "link_flags", "sector", "lap_distance",
        "corner_speed", "special_event", "special_data",
    ])
    write_csv(out / "aiw_runtime_matches.csv", aiw_matches, [
        "aiw_source", "waypoint_index", "branch_id", "runtime_address",
        "region_start", "region_offset", "distance", "x", "y", "z",
    ])
    write_csv(out / "aiw_runtime_sequences.csv", aiw_sequences, [
        "aiw_source", "first_waypoint", "last_waypoint", "matched_waypoints",
        "runtime_start", "runtime_end", "stride", "stride_count", "coverage",
    ])
    write_csv(out / "next_capture_windows.csv", windows, ["start", "size", "clusters", "priority"])
    (out / "next_capture_ranges.txt").write_text(
        "\n".join(
            f"0x{w['start']:x}:0x{w['size']:x}  # priority={w['priority']:.2f} clusters={','.join(map(str, w['clusters']))}"
            for w in windows
        ) + "\n",
        encoding="utf-8",
    )

    print(f"snapshots: {len(sns)}")
    print(f"common regions: {len(common)}")
    print("candidates:", ", ".join(f"{k}={len(v)}" for k, v in candidates.items()))
    print(f"stable external pointers: {len(ptr)}")
    print(f"pointer clusters: {len(cl)}")
    print(f"next capture windows: {len(windows)}")
    if aiw_docs:
        print(f"aiw sources: {len(aiw_docs)}")
        print(f"aiw runtime matches: {len(aiw_matches)}")
        print(f"aiw runtime sequences: {len(aiw_sequences)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
