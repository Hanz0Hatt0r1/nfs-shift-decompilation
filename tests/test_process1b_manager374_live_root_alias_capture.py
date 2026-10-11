import importlib.util
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "shift_live_dump" / "analyze_manager374_root_aliases.py"
ROOT_SLOT = 0x00BC185C


def module():
    spec = importlib.util.spec_from_file_location("manager374_aliases", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_snapshot(base: Path, name: str, regions: list[tuple[int, bytes, str, str]]):
    snap = base / name
    (snap / "regions").mkdir(parents=True)
    manifest_regions = []
    for index, (start, data, perms, path) in enumerate(regions):
        rel = f"regions/{index:04d}.bin"
        (snap / rel).write_bytes(data)
        manifest_regions.append({
            "start": start,
            "end": start + len(data),
            "size": len(data),
            "perms": perms,
            "path": path,
            "file": rel,
        })
    manifest = {"format": "SHIFT-LIVE-MEMORY-SNAPSHOT/1", "regions": manifest_regions}
    (snap / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return snap


def root_region(root_value: int):
    start = ROOT_SLOT & ~0xFFF
    data = bytearray(0x1000)
    off = ROOT_SLOT - start
    struct.pack_into("<I", data, off, root_value)
    return start, bytes(data), "rw-p", "/game/SHIFT.exe"


def test_finds_noncanonical_exact_root_alias_across_snapshots(tmp_path):
    value = 0x12345000
    heap1 = bytearray(0x80)
    heap2 = bytearray(0x80)
    struct.pack_into("<I", heap1, 0x20, value)
    struct.pack_into("<I", heap2, 0x20, value)
    write_snapshot(tmp_path, "snapshot-000000", [root_region(value), (0x20000000, bytes(heap1), "rw-p", "[heap]")])
    write_snapshot(tmp_path, "snapshot-000001", [root_region(value), (0x20000000, bytes(heap2), "rw-p", "[heap]")])

    data = module().analyze(tmp_path)
    assert data["capture"]["active_nonzero_root_snapshot_count"] == 2
    assert data["capture"]["canonical_slot_observation_count"] == 2
    assert data["surface"]["exact_outer_root_alias_candidate_count"] == 1
    row = data["surface"]["exact_outer_root_alias_candidates"][0]
    assert row["address"] == "0x20000020"
    assert row["snapshot_hit_count"] == 2
    assert row["category"] == "heap"
    assert data["surface"]["persistent_exact_outer_root_alias_candidate_count"] == 1


def test_root_value_may_change_between_snapshots_and_same_address_still_aggregates(tmp_path):
    values = [0x11111000, 0x22222000]
    for index, value in enumerate(values):
        heap = bytearray(0x40)
        struct.pack_into("<I", heap, 0x10, value)
        write_snapshot(tmp_path, f"snapshot-{index:06d}", [root_region(value), (0x30000000, bytes(heap), "rw-p", "")])

    data = module().analyze(tmp_path)
    row = data["surface"]["exact_outer_root_alias_candidates"][0]
    assert row["address"] == "0x30000010"
    assert row["snapshot_hit_count"] == 2
    assert row["unique_root_value_count"] == 2
    assert row["root_values"] == ["0x11111000", "0x22222000"]


def test_zero_root_snapshot_is_skipped_not_interpreted_as_alias_scan(tmp_path):
    write_snapshot(tmp_path, "snapshot-000000", [root_region(0), (0x40000000, b"\0" * 0x80, "rw-p", "[heap]")])
    write_snapshot(tmp_path, "snapshot-000001", [root_region(0x12340000), (0x40000000, b"\0" * 0x80, "rw-p", "[heap]")])
    data = module().analyze(tmp_path)
    assert data["capture"]["zero_root_snapshot_count"] == 1
    assert data["capture"]["active_nonzero_root_snapshot_count"] == 1
    assert data["surface"]["exact_outer_root_alias_candidate_count"] == 0


def test_readonly_region_is_not_scanned(tmp_path):
    value = 0x12340000
    ro = struct.pack("<I", value) + b"x" * 12
    write_snapshot(tmp_path, "snapshot-000000", [root_region(value), (0x50000000, ro, "r--p", "/tmp/read-only")])
    data = module().analyze(tmp_path)
    assert data["surface"]["exact_outer_root_alias_candidate_count"] == 0


def test_alignment_one_finds_unaligned_pointer_but_alignment_four_does_not(tmp_path):
    value = 0x12345678
    heap = bytearray(0x20)
    heap[3:7] = struct.pack("<I", value)
    write_snapshot(tmp_path, "snapshot-000000", [root_region(value), (0x60000000, bytes(heap), "rw-p", "[heap]")])
    assert module().analyze(tmp_path, alignment=1)["surface"]["exact_outer_root_alias_candidate_count"] == 1
    assert module().analyze(tmp_path, alignment=4)["surface"]["exact_outer_root_alias_candidate_count"] == 0


def test_chunk_overlap_does_not_miss_boundary_match(tmp_path):
    mod = module()
    value = 0xAABBCCDD
    path = tmp_path / "region.bin"
    data = bytearray(16)
    data[6:10] = struct.pack("<I", value)
    path.write_bytes(data)
    assert list(mod.iter_exact_u32_matches(path, value, chunk_size=8)) == [6]


def test_missing_root_slot_fails_closed(tmp_path):
    write_snapshot(tmp_path, "snapshot-000000", [(0x70000000, b"\0" * 0x20, "rw-p", "[heap]")])
    with pytest.raises(ValueError, match="root slot"):
        module().analyze(tmp_path)


def test_semantic_gates_remain_fail_closed(tmp_path):
    value = 0x12340000
    write_snapshot(tmp_path, "snapshot-000000", [root_region(value)])
    adj = module().analyze(tmp_path)["adjudication"]
    assert adj["live_exact_root_alias_capture_complete_for_supplied_snapshots"] is True
    assert adj["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert adj["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert adj["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
