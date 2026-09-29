import struct
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import analyze_track_paths as runtime


def test_prefixed_array_validator_uses_compact_windows(monkeypatch, tmp_path: Path):
    snapshots = [tmp_path / "snapshot-0", tmp_path / "snapshot-1"]
    indexes = []
    for snap in snapshots:
        region_dir = snap / "regions"
        region_dir.mkdir(parents=True)
        (region_dir / "anon.bin").write_bytes(b"\0" * 0x2000)
        indexes.append({
            0x00200000: {
                "start": 0x00200000,
                "size": 0x2000,
                "file": "regions/anon.bin",
                "perms": "rwxp",
            }
        })

    array = 0x00200400
    calls = []

    def fake_read(snapshot, region_index, starts, address, size):
        calls.append((address, size))
        if address == array - 4:
            return struct.pack("<I", 128)
        if address == array:
            blob = bytearray(128 * 0x24)
            for i in range(128):
                struct.pack_into("<I", blob, i * 0x24, 0x12345678)
            return bytes(blob)
        raise AssertionError((address, size))

    monkeypatch.setattr(runtime, "_read_virtual", fake_read)

    rows = [{
        "address": 0x00200100,
        "nodes": 128,
        "array": array,
    }]
    runtime.validate_prefixed_array_link(
        rows,
        snapshots,
        indexes,
        0x12345678,
        0x24,
        count_field="array_count",
        sequence_field="array_sequence",
    )

    assert rows[0]["array_count"] == 128
    assert rows[0]["array_count_stable"] is True
    assert rows[0]["array_sequence"] == 128
    assert rows[0]["array_sequence_complete"] is True
    assert rows[0]["array_expected_count_match"] is True
    assert len(calls) == 4
    assert all(size in (4, 128 * 0x24) for _, size in calls)


def test_startnode_resolver_uses_compact_window(monkeypatch, tmp_path: Path):
    snapshots = [tmp_path / "s0", tmp_path / "s1"]
    indexes = []
    for snap in snapshots:
        (snap / "regions").mkdir(parents=True)
        (snap / "regions" / "anon.bin").write_bytes(b"\0" * 0x8000)
        indexes.append({
            0x00200000: {
                "start": 0x00200000,
                "size": 0x8000,
                "file": "regions/anon.bin",
                "perms": "rwxp",
            }
        })

    target = 0x00200400
    calls = []

    def fake_read(snapshot, region_index, starts, address, size):
        calls.append((address, size))
        if address == target - 4 and size > 4:
            blob = bytearray(size)
            struct.pack_into("<I", blob, 0, 32)
            for i in range(32):
                off = 4 + i * 0x24
                if off + 4 > len(blob):
                    break
                struct.pack_into("<I", blob, off, 0x00AFBFA8)
            return bytes(blob)
        if address == target:
            blob = bytearray(32 * 0x24)
            for i in range(32):
                struct.pack_into("<I", blob, i * 0x24, 0x00AFBFA8)
            return bytes(blob)
        if address == target - 4:
            return struct.pack("<I", 32)
        raise AssertionError((address, size))

    monkeypatch.setattr(runtime, "_read_virtual", fake_read)

    rows = runtime.resolve_path_start_nodes(
        [{"address": 0x00200100, "start_node": target}],
        snapshots,
        indexes,
        [],
    )

    assert rows[0]["target_vtable"] == 0x00AFBFA8
    assert rows[0]["array_count"] == 32
    assert rows[0]["node_sequence"] == 32
    assert rows[0]["node_sequence_complete"] is True
    assert len(calls) == 4
    assert all(size in (4, 32 * 0x24) for _, size in calls)
