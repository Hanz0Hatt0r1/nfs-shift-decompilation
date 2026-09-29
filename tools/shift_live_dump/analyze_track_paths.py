#!/usr/bin/env python3
"""Find reverse-engineered track/path structures and heap pointer families."""
from __future__ import annotations

import argparse, csv, json, math, re, struct, sys, tempfile, zipfile
from bisect import bisect_right
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT-LIVE-MEMORY-TRACK-PATH-ANALYSIS/1"
VT_RANGE = (0x00400000, 0x00B81000)  # SHIFT.exe image in the supplied capture
KNOWN_VTABLES = {"AISegmentPath": 0x00AFCA70}

PATH = {
    "tx": (0x10, "f"), "ty": (0x14, "f"), "outside": (0x18, "f"),
    "centre": (0x1c, "f"), "start_node": (0x20, "I"), "side": (0x24, "B"),
    "end": (0x25, "B"), "spawn": (0x26, "B"), "edge": (0x27, "B"),
}
INCIDENT = {
    "area": (0xd4, "I"), "path": (0xd8, "I"), "cx": (0xdc, "f"),
    "cy": (0xe0, "f"), "cz": (0xe4, "f"), "radius": (0xe8, "f"),
    "active": (0xf0, "I"), "active_incident": (0xf4, "I"),
    "roaming": (0xf8, "I"),
}
SEGMENT = {
    "nodes": (0x10, "I"), "side": (0x14, "i"), "array": (0x18, "I"),
    "length": (0x1c, "f"), "cyclic": (0x20, "I"), "narrow": (0x24, "I"),
    "spacing": (0x28, "f"), "path_dist": (0x2c, "f"), "current": (0x30, "I"),
    "edge_step": (0x34, "f"),
}
POLY = {
    "nodes": (0x10, "I"), "array": (0x14, "I"), "length": (0x18, "f"),
    "width": (0x1c, "f"), "cyclic": (0x20, "I"), "spacing": (0x24, "f"),
    "default_width": (0x28, "f"),
}

SIZE = {"B": 1, "I": 4, "i": 4, "f": 4}


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
    if not all(finite(d[k], 1e7) for k in ("cx", "cy", "cz")) or not finite(d["radius"], 1e5):
        return None
    if not 0 <= d["radius"] <= 1e5:
        return None
    if d["active"] not in (0, 1) or d["active_incident"] not in (0, 1) or d["roaming"] not in (0, 1):
        return None
    return {"address": addr, "vtable": vt, "vtable_mapping": game_vtable(vt, mm, starts), **d, "path_mapping": pm}


def check_segment(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, SEGMENT)
    vt = read(blob, 0, "I")
    if vt != KNOWN_VTABLES["AISegmentPath"] or any(v is None for v in d.values()):
        return None
    if not game_vtable(vt, mm, starts):
        return None
    am = writable(d["array"], mm, starts)
    if not am or not 1 <= d["nodes"] <= 1000000:
        return None
    if d["side"] not in (-1, 0, 1, 2, 3) or d["cyclic"] not in (0, 1) or d["narrow"] not in (0, 1):
        return None
    if not all(finite(d[k]) for k in ("length", "spacing", "path_dist", "edge_step")):
        return None
    if not (0 < d["length"] <= 1e7 and 0 < d["spacing"] <= 1e5):
        return None
    if not 0 <= d["current"] < d["nodes"] + 1:
        return None
    return {"address": addr, "vtable": vt, "vtable_mapping": game_vtable(vt, mm, starts), **d, "array_mapping": am}


def check_poly(blob: bytes, addr: int, mm: list[dict], starts: list[int]):
    d = fields(blob, POLY)
    vt = read(blob, 0, "I")
    if vt is None or any(v is None for v in d.values()) or not game_vtable(vt, mm, starts):
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


def scan(blob: bytes, start: int, mm: list[dict], starts: list[int]) -> dict[str, list[dict]]:
    """Scan aligned object starts without copying the remaining blob per offset.

    The old implementation used blob[off:] for every 4-byte offset. That copies
    O(n) bytes for each iteration and turns a linear scan into O(n^2) work on
    large captures. Keep a single memoryview and reject non-game-image vtable
    words before running the more expensive structure validators.
    """
    found = {"Path": [], "Incident.PathOwner": [], "AISegmentPath": [], "AIPolylinePath": []}
    checks = (
        ("Path", check_path),
        ("Incident.PathOwner", check_incident),
        ("AISegmentPath", check_segment),
        ("AIPolylinePath", check_poly),
    )
    view = memoryview(blob)
    limit = max(0, len(view) - 0x38)
    known_segment_vtable = KNOWN_VTABLES["AISegmentPath"]
    for off in range(0, limit, 4):
        vtable = read(view, off, "I")
        if vtable is None:
            continue
        if vtable != known_segment_vtable:
            if not (VT_RANGE[0] <= vtable < VT_RANGE[1]):
                continue
            if not game_vtable(vtable, mm, starts):
                continue
        chunk = view[off:]
        addr = start + off
        for name, fn in checks:
            row = fn(chunk, addr, mm, starts)
            if row:
                found[name].append(row)
    return found


def stable_pointers(
    sns: list[Path],
    indexes: list[dict[int, dict]],
    mm: list[dict],
    starts: list[int],
    excluded_sources: list[tuple[int, int]] | None = None,
) -> list[dict]:
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
        bs = [(s / r["file"]).read_bytes() for s, r in zip(sns, rs)]
        n = min(map(len, bs))
        for off in range(0, n - 3, 4):
            source_address = start + off
            if in_ranges(source_address, excluded_sources):
                continue
            vals = [struct.unpack_from("<I", b, off)[0] for b in bs]
            if len(set(vals)) != 1:
                continue
            v = vals[0]
            if not v or any(a <= v < b for a, b in selected):
                continue
            m = mapping(v, mm, starts)
            if not m or "w" not in m["perms"] or v % 4:
                continue
            counts[v] += 1
            refs.setdefault(v, []).append(start + off)

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
        if line.startswith("\\\\") and line[2:].strip("-").isdigit():
            current = {"index": int(line[2:])}
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


def correlate_aiw_runtime(
    sns: list[Path],
    indexes: list[dict[int, dict]],
    aiw_docs: list[dict],
    scan_ranges: list[tuple[int, int]],
    tolerance: float,
    runtime_roots: list[int] | None = None,
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

    matches: list[dict] = []
    seen: set[tuple[str, int, int]] = set()
    for st in sorted(common):
        rec = indexes[0][st]
        size = int(rec["size"])
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

        delta_counts = Counter()
        for i, addresses in by_wp.items():
            for nxt in by_wp.get(i + 1, ()):
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
            while True:
                candidates = [
                    address for address in by_wp.get(current + 1, ())
                    if address - last_addr == stride
                ]
                if not candidates:
                    break
                last_addr = candidates[0]
                current += 1
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
    candidates = {k: [] for k in ("Path", "Incident.PathOwner", "AISegmentPath", "AIPolylinePath")}

    common_sorted = sorted(common)
    for index, st in enumerate(common_sorted, 1):
        print(f"[scan] region {index}/{len(common_sorted)} start=0x{st:x}", flush=True)
        rr = [x[st] for x in idx]
        if any(int(r["size"]) != int(rr[0]["size"]) for r in rr):
            continue
        blob0 = (sns[0] / rr[0]["file"]).read_bytes()
        found = scan(blob0, st, mm, starts)
        other_blobs = [(s / r["file"]).read_bytes() for s, r in zip(sns[1:], rr[1:])]
        for name, rows in found.items():
            for row in rows[:args.top]:
                off = row["address"] - st
                span = 0x28 if name == "Path" else 0x124 if name == "Incident.PathOwner" else 0x38 if name == "AISegmentPath" else 0x2C
                stable = 1 + sum(
                    1 for blob in other_blobs
                    if 0 <= off and off + span <= len(blob) and blob0[off:off + span] == blob[off:off + span]
                )
                row.update({
                    "region_start": st,
                    "region_offset": off,
                    "snapshot_count": len(sns),
                    "stable_snapshots": stable,
                })
                candidates[name].append(row)

    for k in candidates:
        candidates[k] = sorted(candidates[k], key=lambda r: r["address"])[:args.top]

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
        candidates["Path"], mm, starts, len(sns), args.path_root_top
    )
    path_root_windows = windows_for_path_roots(
        path_roots, args.path_root_radius_kib * 1024, args.path_root_top
    )

    aiw_docs: list[dict] = []
    aiw_matches: list[dict] = []
    aiw_sequences: list[dict] = []
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
            args.runtime_roots,
        )
        print(
            f"[aiw] matches={len(aiw_matches)} sequences={len(aiw_sequences)}",
            flush=True,
        )

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
        "known_vtables": {k: hex(v) for k, v in KNOWN_VTABLES.items()},
        "excluded_source_ranges": [{"start": a, "end": b} for a, b in excluded_sources],
        "notes": [
            "Reduced captures can show absence only from selected ranges, not from the live process.",
            "Pointer clusters are recommendations; target object identity must be confirmed after capturing their bytes from the original full series.",
        ],
    }
    (out / "track_path_analysis.json").write_text(json.dumps(summary, indent=2) + "
", encoding="utf-8")
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
    write_csv(out / "path_root_targets.csv", path_roots, [
        "target", "candidate_count", "candidate_addresses",
        "mapping_start", "mapping_end", "mapping_perms",
    ])
    write_csv(out / "path_root_windows.csv", path_root_windows, [
        "start", "size", "targets",
    ])
    (out / "path_root_ranges.txt").write_text(
        "
".join(
            f"0x{w['start']:x}:0x{w['size']:x}  # targets=" +
            ",".join(f"0x{x:x}" for x in w["targets"])
            for w in path_root_windows
        ) + "
",
        encoding="utf-8",
    )
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
        "
".join(
            f"0x{w['start']:x}:0x{w['size']:x}  # priority={w['priority']:.2f} clusters={','.join(map(str, w['clusters']))}"
            for w in windows
        ) + "
",
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
