from pathlib import Path
import struct

from tools.analyze_apitrace_tail_parts import (
    copy_joined,
    discover_parts,
    find_chunk_start,
    scan_markers,
    valid_chunk,
)

class FakeSnappy:
    def uncompress(self, data: bytes) -> bytes:
        if data.startswith(b"OK:"):
            return data[3:]
        raise RuntimeError("bad")

def test_discover_parts_and_copy(tmp_path: Path):
    directory = tmp_path / "parts"
    directory.mkdir()
    (directory / "SHIFT_tail.part.aa").write_bytes(b"aa")
    (directory / "SHIFT_tail.part.ab").write_bytes(b"bb")
    parts = discover_parts(directory)
    assert [p.name for p in parts] == [
        "SHIFT_tail.part.aa", "SHIFT_tail.part.ab"
    ]
    joined = tmp_path / "joined.trace"
    assert copy_joined(parts, joined) == 4
    assert joined.read_bytes() == b"aabb"

def test_find_chunk_start_skips_leading_fragment(tmp_path: Path):
    # Two valid chunks after an arbitrary leading fragment.
    chunk1 = b"OK:first"
    chunk2 = b"OK:second"
    raw = tmp_path / "tail.trace"
    raw.write_bytes(
        b"garbage"
        + struct.pack("<I", len(chunk1)) + chunk1
        + struct.pack("<I", len(chunk2)) + chunk2
    )
    with raw.open("rb") as fp:
        offset, size, data = find_chunk_start(
            fp, raw.stat().st_size, FakeSnappy(),
            scan_limit=64, max_chunk=1024
        )
    assert offset == 7
    assert size == len(chunk1)
    assert data == b"first"

def test_scan_markers():
    result = scan_markers(b"Present DrawIndexedPrimitive memcpy Present")
    assert "Present" in result
    assert "DrawIndexedPrimitive" in result
    assert "memcpy" in result
