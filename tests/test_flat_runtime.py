import struct

import pytest

from flat_runtime import FLATRuntimeDecodeError, parse_flat_runtime


def _leaf(index: int) -> bytes:
    words = [0] * 16
    words[15] = index
    return struct.pack("<16I", *words)


def _node(leaves: list[bytes], children: list[bytes] | None = None, marker: int = 1) -> bytes:
    children = children or []
    body = b"".join(leaves) + b"".join(children)
    span = 0x20 + len(body)
    header = struct.pack("<7I", 0, 0, 0, 0, 0, 0, len(leaves))
    header += struct.pack("<I", (marker << 24) | span)
    return header + body


def test_flat_header_and_leaf_layout():
    data = _node([_leaf(7)], marker=1)
    report = parse_flat_runtime(data)
    assert report["ready"] is True
    assert report["root"]["direct_record_count"] == 1
    assert report["root"]["records"][0]["runtime_index"] == 7
    assert report["root"]["span_bytes"] == 0x60


def test_nested_flat_nodes_follow_low24_span():
    child = _node([_leaf(9)], marker=1)
    root = _node([], [child], marker=1)
    report = parse_flat_runtime(root)
    assert report["stats"]["tree_nodes"] == 2
    assert report["stats"]["leaf_records"] == 1
    assert report["stats"]["max_depth"] == 1


def test_invalid_span_is_rejected():
    data = struct.pack("<8I", 0, 0, 0, 0, 0, 0, 2, 0x100)
    with pytest.raises(FLATRuntimeDecodeError):
        parse_flat_runtime(data)


def test_non_strict_returns_blocker():
    result = parse_flat_runtime(b"\\0" * 8, strict=False)
    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["blockers"]
