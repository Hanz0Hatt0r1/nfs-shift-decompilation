"""Conservative parser for the binary FLAT tree normalized by the retail runtime.

Recovered from FUN_0068a8b0 -> FUN_006af300 and the tree routines
FUN_006af6c0/FUN_006af780/FUN_006af5a0. The tree header is 0x20 bytes,
direct records are 0x40 bytes each, dword +0x18 is the direct-record count,
and dword +0x1c stores a low-24-bit byte span plus a runtime high-byte depth
/ terminal marker.

Leaf semantic fields remain raw because their vtable-backed meanings are
defined by later runtime code.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

FORMAT = "SHIFT.FLATRuntime/1"
HEADER_SIZE = 0x20
LEAF_SIZE = 0x40


class FLATRuntimeDecodeError(ValueError):
    pass


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise FLATRuntimeDecodeError(f"u32 out of range at 0x{off:x}")
    return struct.unpack_from("<I", data, off)[0]


def _parse_leaf(data: bytes, off: int, end: int, index: int) -> dict[str, Any]:
    if off + LEAF_SIZE > end:
        raise FLATRuntimeDecodeError(f"leaf {index} exceeds FLAT node span")
    words = [_u32(data, off + 4 * i) for i in range(LEAF_SIZE // 4)]
    return {
        "index": index,
        "offset": off,
        "record_bytes": LEAF_SIZE,
        "raw_u32": words,
        "runtime_index": words[15],
        "runtime_links": {
            "tree": words[12],
            "record": words[13],
            "external": words[14],
            "index": words[15],
        },
    }


def _parse_node(
    data: bytes,
    start: int,
    limit: int,
    *,
    depth: int,
    max_depth: int,
) -> tuple[dict[str, Any], int]:
    if depth > max_depth:
        raise FLATRuntimeDecodeError("FLAT tree exceeded maximum recursion depth")
    if start + HEADER_SIZE > limit:
        raise FLATRuntimeDecodeError(f"FLAT node header exceeds input at 0x{start:x}")

    words = [_u32(data, start + 4 * i) for i in range(8)]
    direct_count = words[6]
    span_word = words[7]
    span_bytes = span_word & 0x00FFFFFF
    marker = span_word >> 24
    minimum_span = HEADER_SIZE + direct_count * LEAF_SIZE
    if span_bytes < minimum_span:
        raise FLATRuntimeDecodeError(
            f"FLAT node span {span_bytes} is smaller than header+records {minimum_span}"
        )
    node_end = start + span_bytes
    if node_end > limit:
        raise FLATRuntimeDecodeError(
            f"FLAT node span exceeds input: end 0x{node_end:x}, limit 0x{limit:x}"
        )

    leaves = [
        _parse_leaf(data, start + HEADER_SIZE + LEAF_SIZE * i, node_end, i)
        for i in range(direct_count)
    ]

    children: list[dict[str, Any]] = []
    cursor = start + minimum_span
    while cursor < node_end:
        child, next_cursor = _parse_node(
            data, cursor, node_end, depth=depth + 1, max_depth=max_depth
        )
        children.append(child)
        cursor = next_cursor
        if child["depth_marker"] != 0:
            break
    if cursor != node_end:
        raise FLATRuntimeDecodeError(
            f"FLAT child traversal stopped at 0x{cursor:x}, expected 0x{node_end:x}"
        )

    return ({
        "offset": start,
        "header_bytes": HEADER_SIZE,
        "raw_header_u32": words[:7],
        "span_word": span_word,
        "span_bytes": span_bytes,
        "depth_marker": marker,
        "direct_record_count": direct_count,
        "records": leaves,
        "children": children,
        "depth": depth,
        "total_span_hash": hashlib.sha256(data[start:node_end]).hexdigest(),
    }, node_end)


def parse_flat_runtime(
    data: bytes,
    *,
    strict: bool = True,
    max_depth: int = 64,
) -> dict[str, Any]:
    """Parse a runtime-normalized FLAT tree from its body."""
    blockers: list[str] = []
    root = None
    consumed = 0
    try:
        root, consumed = _parse_node(
            data, 0, len(data), depth=0, max_depth=max_depth
        )
    except FLATRuntimeDecodeError as exc:
        if strict:
            raise
        blockers.append(f"flat:{exc}")

    if root is not None and consumed != len(data):
        blockers.append(f"flat:trailing-bytes:{len(data) - consumed}")

    def count_nodes(node: dict[str, Any] | None) -> tuple[int, int, int]:
        if node is None:
            return 0, 0, 0
        node_count = 1
        leaf_count = len(node["records"])
        max_depth_seen = node["depth"]
        for child in node["children"]:
            n, l, d = count_nodes(child)
            node_count += n
            leaf_count += l
            max_depth_seen = max(max_depth_seen, d)
        return node_count, leaf_count, max_depth_seen

    nodes, leaves, depth = count_nodes(root)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": not blockers and root is not None,
        "status": "decoded" if not blockers and root is not None else "blocked",
        "input_bytes": len(data),
        "consumed_bytes": consumed,
        "trailing_bytes": max(0, len(data) - consumed),
        "root": root,
        "stats": {
            "tree_nodes": nodes,
            "leaf_records": leaves,
            "max_depth": depth,
        },
        "blockers": blockers,
        "evidence": {
            "copy_to_runtime": "FUN_006af300",
            "normalize_tree": "FUN_006af6c0",
            "index_leaves": "FUN_006af780",
            "walk_leaves": "FUN_006af5a0",
        },
        "limitations": [
            "Leaf vtable-backed fields are preserved raw; their semantic meaning is not claimed.",
            "High-byte span marker is exposed as runtime depth/termination metadata rather than assigned a higher-level scene meaning.",
        ],
    }
