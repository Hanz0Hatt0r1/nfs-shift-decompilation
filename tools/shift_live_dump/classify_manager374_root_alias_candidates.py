#!/usr/bin/env python3
"""Classify noncanonical live exact-root aliases by storage and capture lifetime.

Consumes SHIFT.P1B.Manager374RuntimeExactRootAliasCapture/1 output plus the pinned
Ghidra binary/globals export. This turns observed runtime equality hits into a
concrete investigation worklist without promoting finite captures into a global
absence/identity proof.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374RuntimeRootAliasCandidateClassification/1"
CAPTURE_FORMAT = "SHIFT.P1B.Manager374RuntimeExactRootAliasCapture/1"
BINARY_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
EXPECTED_PROGRAM = "SHIFT.exe"
EXPECTED_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
EXPECTED_LANGUAGE = "x86:LE:32:default"
EXPECTED_IMAGE_BASE = "0x00400000"
EXPECTED_POINTER_SIZE = 4
ROOT_SLOT = "0x00bc185c"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_hex(value: object, *, field: str) -> int:
    text = str(value or "").strip().lower()
    if not text.startswith("0x"):
        raise ValueError(f"invalid {field}: {value!r}")
    try:
        return int(text, 16)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _norm_hex(value: object, *, field: str) -> str:
    return f"0x{_parse_hex(value, field=field):08x}"


def _validate_binary(path: Path) -> dict:
    data = _load_json(path)
    if data.get("format") != BINARY_FORMAT:
        raise ValueError(f"unexpected binary format {data.get('format')!r}")
    if data.get("program_name") != EXPECTED_PROGRAM:
        raise ValueError(f"unexpected program {data.get('program_name')!r}")
    if str(data.get("executable_md5", "")).lower() != EXPECTED_MD5:
        raise ValueError(f"unexpected executable MD5 {data.get('executable_md5')!r}")
    if data.get("language_id") != EXPECTED_LANGUAGE:
        raise ValueError(f"unexpected language {data.get('language_id')!r}")
    if str(data.get("image_base", "")).lower() != EXPECTED_IMAGE_BASE:
        raise ValueError(f"unexpected image base {data.get('image_base')!r}")
    if data.get("pointer_size") != EXPECTED_POINTER_SIZE:
        raise ValueError(f"unexpected pointer size {data.get('pointer_size')!r}")
    return data


def _load_capture(path: Path) -> dict:
    data = _load_json(path)
    if data.get("format") != CAPTURE_FORMAT:
        raise ValueError(f"unexpected capture format {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError("capture is not ready")
    authority = data.get("authority", {})
    if str(authority.get("canonical_root_slot", "")).lower() != ROOT_SLOT:
        raise ValueError("canonical root slot drift")
    if authority.get("pointer_width_bits") != 32 or authority.get("little_endian") is not True:
        raise ValueError("capture pointer ABI drift")
    return data


def _load_globals(path: Path) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            address = row.get("address")
            if not address:
                continue
            try:
                addr = _parse_hex(address, field=f"global address at line {line_no}")
            except ValueError:
                continue
            out[addr].append({
                "address": f"0x{addr:08x}",
                "name": row.get("name"),
                "data_type": row.get("data_type"),
                "xref_count": row.get("xref_count"),
            })
    for addr in out:
        out[addr].sort(key=lambda row: (str(row.get("name") or ""), str(row.get("data_type") or "")))
    return dict(out)


def _memory_blocks(binary: dict) -> list[dict]:
    blocks: list[dict] = []
    for row in binary.get("memory_blocks", []):
        start = _parse_hex(row.get("start"), field=f"{row.get('name')} start")
        end = _parse_hex(row.get("end"), field=f"{row.get('name')} end")
        if end < start:
            raise ValueError(f"invalid memory block range {row.get('name')!r}")
        blocks.append({
            "name": row.get("name"),
            "start": start,
            "end": end,
            "initialized": row.get("initialized"),
            "read": row.get("read"),
            "write": row.get("write"),
            "execute": row.get("execute"),
        })
    return blocks


def _find_block(blocks: list[dict], address: int) -> dict | None:
    for block in blocks:
        if block["start"] <= address <= block["end"]:
            return block
    return None


def _storage_class(candidate: dict, block: dict | None) -> str:
    if block is not None:
        return "retail-image-writable" if block.get("write") is True else "retail-image-nonwritable"
    category = str(candidate.get("category") or "").lower()
    if category == "heap":
        return "heap"
    if category == "anonymous":
        return "anonymous"
    if category == "module":
        return "other-module"
    return "other"


def _validate_candidate(candidate: dict, *, active_snapshots: set[str]) -> tuple[str, set[str], set[str]]:
    address = _norm_hex(candidate.get("address"), field="candidate address")
    hits = [str(x) for x in candidate.get("snapshot_hits", [])]
    if len(hits) != len(set(hits)):
        raise ValueError(f"candidate {address}: duplicate snapshot hits")
    if candidate.get("snapshot_hit_count") != len(hits):
        raise ValueError(f"candidate {address}: snapshot hit count drift")
    if not set(hits) <= active_snapshots:
        raise ValueError(f"candidate {address}: hit outside active snapshot set")
    roots = [str(x).lower() for x in candidate.get("root_values", [])]
    if len(roots) != len(set(roots)):
        raise ValueError(f"candidate {address}: duplicate root values")
    if candidate.get("unique_root_value_count") != len(roots):
        raise ValueError(f"candidate {address}: root value count drift")
    for value in roots:
        _parse_hex(value, field=f"candidate {address} root value")
    return address, set(hits), set(roots)


def build_payload(capture: dict, binary: dict, globals_by_address: dict[int, list[dict]]) -> dict:
    active_rows = capture.get("capture", {}).get("active_root_values", [])
    active_by_snapshot: dict[str, str] = {}
    for row in active_rows:
        snapshot = str(row.get("snapshot") or "")
        if not snapshot:
            raise ValueError("active root observation without snapshot")
        if snapshot in active_by_snapshot:
            raise ValueError(f"duplicate active root snapshot {snapshot}")
        active_by_snapshot[snapshot] = _norm_hex(row.get("root_value"), field=f"root value for {snapshot}")

    active_count = capture.get("capture", {}).get("active_nonzero_root_snapshot_count")
    if active_count != len(active_by_snapshot):
        raise ValueError("active snapshot count drift")
    active_snapshots = set(active_by_snapshot)
    distinct_active_roots = set(active_by_snapshot.values())
    blocks = _memory_blocks(binary)

    classified: list[dict] = []
    seen_addresses: set[str] = set()
    storage_counts: Counter[str] = Counter()
    lifetime_counts: Counter[str] = Counter()
    root_tracking: list[dict] = []
    retail_global_candidates: list[dict] = []

    for candidate in capture.get("surface", {}).get("exact_outer_root_alias_candidates", []):
        address, hits, roots = _validate_candidate(candidate, active_snapshots=active_snapshots)
        if address in seen_addresses:
            raise ValueError(f"duplicate candidate address {address}")
        seen_addresses.add(address)
        address_int = int(address, 16)
        block = _find_block(blocks, address_int)
        storage = _storage_class(candidate, block)
        covers_all = hits == active_snapshots and bool(active_snapshots)
        tracks_all_values = covers_all and roots == distinct_active_roots and bool(distinct_active_roots)
        if tracks_all_values and len(distinct_active_roots) > 1:
            lifetime = "persistent-tracks-root-changes"
        elif covers_all:
            lifetime = "persistent-over-supplied-capture"
        else:
            lifetime = "intermittent-over-supplied-capture"

        labels = globals_by_address.get(address_int, [])
        row = {
            "address": address,
            "mapping_category": candidate.get("category"),
            "mapping_path": candidate.get("path"),
            "mapping_perms": candidate.get("perms"),
            "storage_class": storage,
            "retail_memory_block": None if block is None else {
                "name": block.get("name"),
                "start": f"0x{block['start']:08x}",
                "end": f"0x{block['end']:08x}",
                "write": block.get("write"),
                "execute": block.get("execute"),
            },
            "exact_ghidra_globals": labels,
            "snapshot_hit_count": candidate.get("snapshot_hit_count"),
            "snapshot_hits": sorted(hits),
            "root_values": sorted(roots),
            "covers_all_active_snapshots": covers_all,
            "tracks_all_observed_root_values": tracks_all_values,
            "lifetime_class": lifetime,
        }
        classified.append(row)
        storage_counts[storage] += 1
        lifetime_counts[lifetime] += 1
        if lifetime == "persistent-tracks-root-changes":
            root_tracking.append(row)
        if storage == "retail-image-writable" and labels:
            retail_global_candidates.append(row)

    expected_candidate_count = capture.get("surface", {}).get("exact_outer_root_alias_candidate_count")
    if expected_candidate_count != len(classified):
        raise ValueError("capture candidate count drift")

    classified.sort(key=lambda row: row["address"])
    root_tracking.sort(key=lambda row: row["address"])
    retail_global_candidates.sort(key=lambda row: row["address"])

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "ghidra_program_md5": binary["executable_md5"],
            "canonical_root_slot": ROOT_SLOT,
            "capture_format": CAPTURE_FORMAT,
            "binary_format": BINARY_FORMAT,
        },
        "capture_summary": {
            "active_nonzero_root_snapshot_count": active_count,
            "distinct_active_root_value_count": len(distinct_active_roots),
            "active_root_values": [
                {"snapshot": snapshot, "root_value": active_by_snapshot[snapshot]}
                for snapshot in sorted(active_by_snapshot)
            ],
        },
        "surface": {
            "classified_candidate_count": len(classified),
            "storage_class_counts": dict(sorted(storage_counts.items())),
            "lifetime_class_counts": dict(sorted(lifetime_counts.items())),
            "persistent_root_change_tracking_candidate_count": len(root_tracking),
            "persistent_root_change_tracking_candidates": root_tracking,
            "retail_image_exact_global_candidate_count": len(retail_global_candidates),
            "retail_image_exact_global_candidates": retail_global_candidates,
            "candidates": classified,
        },
        "adjudication": {
            "supplied_capture_alias_candidates_classified": True,
            "persistent_root_change_tracking_candidates_identified": bool(root_tracking),
            "retail_image_exact_global_candidates_identified": bool(retail_global_candidates),
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This classifies only exact pointer-equality candidates observed in the supplied non-atomic snapshots.",
            "Persistence across supplied snapshots, including tracking root changes, is prioritization evidence and not proof of ownership, producer identity or completeness over all process states.",
            "Exact Ghidra global labels are navigation metadata; unlabeled image storage, heap and anonymous mappings may still have program or external producers.",
            "A capture with zero candidates does not promote global alias absence because finite snapshots can miss transient aliases.",
            "No numeric address/offset equality is promoted to semantic object identity."
        ],
        "next_step": (
            "For each persistent root-change tracker or retail-image exact-global candidate, recover the concrete writer/owner; "
            "repeat controlled captures around construction, steady-state and teardown; keep heap/anonymous intermittent hits as explicit unresolved runtime candidates."
        ),
    }


def analyze(capture_json: Path, binary_json: Path, globals_jsonl: Path) -> dict:
    capture = _load_capture(capture_json)
    binary = _validate_binary(binary_json)
    globals_by_address = _load_globals(globals_jsonl)
    return build_payload(capture, binary, globals_by_address)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_json", type=Path)
    parser.add_argument("binary_json", type=Path)
    parser.add_argument("globals_jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.capture_json, args.binary_json, args.globals_jsonl)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
