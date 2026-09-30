"""Conservative parser for the binary FLAT tree normalized by the retail runtime.

Recovered from FUN_0068a8b0 -> FUN_006af300 and the tree routines
FUN_006af6c0/FUN_006af780/FUN_006af5a0/FUN_006af640/FUN_006af830. The tree
header is 0x20 bytes, direct records are 0x40 bytes each, dword +0x18 is the
direct-record count, and dword +0x1c carries the node byte span.

Raw retail SGB files can encode terminal spans as a negative signed dword.
FUN_006af6c0 normalizes that encoding into the low-24-bit span plus a runtime
high-byte depth/termination marker before traversal.

Unknown leaf payload fields remain raw. Only offsets with explicit runtime
consumers are assigned operational names.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

FORMAT = "SHIFT.FLATRuntime/1"
HEADER_SIZE = 0x20
LEAF_SIZE = 0x40

# FUN_006af330 allocates the runtime tables indexed by direct-record +0x3c.
RUNTIME_PRIMARY_STRIDE = 0x28
RUNTIME_PRIMARY_VALUE_OFFSET = 0x20
RUNTIME_SECONDARY_STRIDE = 0x40
RUNTIME_SECONDARY_NODE_OFFSET = 0x30
RUNTIME_SECONDARY_RECORD_OFFSET = 0x34
RUNTIME_SECONDARY_PRIMARY_SLOT_OFFSET = 0x38
LEAF_DIRECT_OBJECT_POINTER_OFFSET = 0x38
LEAF_RUNTIME_INDEX_OFFSET = 0x3C
RUNTIME_SECONDARY_DISPATCH_VFUNC_OFFSET = 0x08
RUNTIME_SECONDARY_RELEASE_VFUNC_OFFSET = 0x0C
DIRECT_OBJECT_CHILD_POINTER_OFFSET = 0x08
DIRECT_OBJECT_REFCOUNT_OFFSET = 0x20
DIRECT_OBJECT_CHILD_RELEASE_VFUNC_OFFSET = 0x0C
DIRECT_OBJECT_DESTROY_VFUNC_OFFSET = 0x10


class FLATRuntimeDecodeError(ValueError):
    pass


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise FLATRuntimeDecodeError(f"u32 out of range at 0x{off:x}")
    return struct.unpack_from("<I", data, off)[0]


def _signed_u32(value: int) -> int:
    return value if value < 0x80000000 else value - 0x100000000


def _normalize_span_word(
    raw_word: int,
    *,
    normalize_signed_terminal_spans: bool,
    normalization_base: int,
    normalization_depth: int,
) -> dict[str, Any]:
    signed = _signed_u32(raw_word)
    sign_normalized = bool(
        normalize_signed_terminal_spans and signed < 0
    )
    if sign_normalized:
        span_bytes = -signed
        if span_bytes > 0x00FFFFFF:
            raise FLATRuntimeDecodeError(
                f"signed FLAT span exceeds low-24-bit runtime range: {span_bytes}"
            )
        working_word = 0x01000000 | span_bytes
    else:
        working_word = raw_word
        span_bytes = working_word & 0x00FFFFFF

    terminal = (working_word & 0xFF000000) != 0
    marker = (
        normalization_depth - normalization_base
        if terminal
        else 0
    )
    if marker < 0 or marker > 0xFF:
        raise FLATRuntimeDecodeError(
            f"normalized FLAT marker out of range: {marker}"
        )
    normalized_word = (marker << 24) | span_bytes
    return {
        "serialized_word": raw_word,
        "serialized_signed": signed,
        "signed_terminal_encoding": signed < 0,
        "sign_normalization_applied": sign_normalized,
        "span_bytes": span_bytes,
        "terminal": terminal,
        "normalized_marker": marker,
        "normalized_word": normalized_word,
    }


def _parse_leaf(data: bytes, off: int, end: int, index: int) -> dict[str, Any]:
    if off + LEAF_SIZE > end:
        raise FLATRuntimeDecodeError(f"leaf {index} exceeds FLAT node span")
    words = [_u32(data, off + 4 * i) for i in range(LEAF_SIZE // 4)]
    return {
        "index": index,
        "offset": off,
        "record_bytes": LEAF_SIZE,
        "raw_u32": words,
        # +0x38 is a nullable direct object pointer slot. FUN_006af640
        # passes it to FUN_006b0440 for recursive scene-object lookup.
        # FUN_006af830 owns its fallback teardown when no normalized
        # secondary-table entry exists.
        "object_handle": words[14],
        "direct_object_pointer_word": words[14],
        "runtime_index": words[15],
        "child_index": words[15],
        "index_word": words[15],
        "runtime_link_metadata": {
            "index_word_offset": 0x3c,
            "index": words[15],
            "primary_table": {
                "stride": RUNTIME_PRIMARY_STRIDE,
                "value_offset": RUNTIME_PRIMARY_VALUE_OFFSET,
                "slot_offset": (
                    RUNTIME_PRIMARY_VALUE_OFFSET
                    + words[15] * RUNTIME_PRIMARY_STRIDE
                ),
            },
            "secondary_table": {
                "stride": RUNTIME_SECONDARY_STRIDE,
                "node_pointer_offset": RUNTIME_SECONDARY_NODE_OFFSET,
                "record_pointer_offset": RUNTIME_SECONDARY_RECORD_OFFSET,
                "primary_slot_pointer_offset": RUNTIME_SECONDARY_PRIMARY_SLOT_OFFSET,
                "slot_offset": words[15] * RUNTIME_SECONDARY_STRIDE,
            },
        },
        "runtime_consumer_metadata": {
            "direct_object_pointer_offset": LEAF_DIRECT_OBJECT_POINTER_OFFSET,
            "runtime_index_offset": LEAF_RUNTIME_INDEX_OFFSET,
            "dispatch": {
                "function": "FUN_006af5a0",
                "secondary_table_index": words[15],
                "secondary_table_vfunc_offset": (
                    RUNTIME_SECONDARY_DISPATCH_VFUNC_OFFSET
                ),
                "order": "direct-records-before-child-nodes",
            },
            "recursive_lookup": {
                "function": "FUN_006af640 -> FUN_006b0440",
                "direct_object_pointer_offset": (
                    LEAF_DIRECT_OBJECT_POINTER_OFFSET
                ),
                "tree_order": "child-nodes-before-direct-records",
                "lookup_target_class": "unresolved",
            },
            "teardown": {
                "function": "FUN_006af830",
                "secondary_slot_release_vfunc_offset": (
                    RUNTIME_SECONDARY_RELEASE_VFUNC_OFFSET
                ),
                "fallback_direct_pointer": {
                    "child_pointer_offset": (
                        DIRECT_OBJECT_CHILD_POINTER_OFFSET
                    ),
                    "child_release_vfunc_offset": (
                        DIRECT_OBJECT_CHILD_RELEASE_VFUNC_OFFSET
                    ),
                    "refcount_offset": DIRECT_OBJECT_REFCOUNT_OFFSET,
                    "destroy_vfunc_offset": DIRECT_OBJECT_DESTROY_VFUNC_OFFSET,
                    "leaf_pointer_cleared": True,
                },
            },
        },
        "runtime_generated_links": False,
    }


def _parse_node(
    data: bytes,
    start: int,
    limit: int,
    *,
    depth: int,
    max_depth: int,
    normalize_signed_terminal_spans: bool,
    normalization_base: int,
    normalization_depth: int,
) -> tuple[dict[str, Any], int]:
    if depth > max_depth:
        raise FLATRuntimeDecodeError("FLAT tree exceeded maximum recursion depth")
    if start + HEADER_SIZE > limit:
        raise FLATRuntimeDecodeError(f"FLAT node header exceeds input at 0x{start:x}")

    words = [_u32(data, start + 4 * i) for i in range(8)]
    direct_count = words[6]
    span_info = _normalize_span_word(
        words[7],
        normalize_signed_terminal_spans=normalize_signed_terminal_spans,
        normalization_base=normalization_base,
        normalization_depth=normalization_depth,
    )
    span_word = int(span_info["normalized_word"])
    span_bytes = int(span_info["span_bytes"])
    marker = int(span_info["normalized_marker"])
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
    child_normalization_base = (
        normalization_base if marker != 0 else normalization_depth
    )
    child_normalization_depth = normalization_depth + 1
    while cursor < node_end:
        child, next_cursor = _parse_node(
            data,
            cursor,
            node_end,
            depth=depth + 1,
            max_depth=max_depth,
            normalize_signed_terminal_spans=normalize_signed_terminal_spans,
            normalization_base=child_normalization_base,
            normalization_depth=child_normalization_depth,
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
        "serialized_span_word": words[7],
        "serialized_span_signed": span_info["serialized_signed"],
        "serialized_terminal_encoding": span_info[
            "signed_terminal_encoding"
        ],
        "span_normalization_applied": span_info[
            "sign_normalization_applied"
        ],
        "span_word": span_word,
        "normalized_span_word": span_word,
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
    normalize_signed_terminal_spans: bool = True,
) -> dict[str, Any]:
    """Parse a runtime-normalized FLAT tree from its body."""
    blockers: list[str] = []
    root = None
    consumed = 0
    try:
        root, consumed = _parse_node(
            data,
            0,
            len(data),
            depth=0,
            max_depth=max_depth,
            normalize_signed_terminal_spans=normalize_signed_terminal_spans,
            normalization_base=0,
            normalization_depth=1,
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
        "normalization": {
            "signed_terminal_spans_enabled": (
                normalize_signed_terminal_spans
            ),
            "source_function": "FUN_006af6c0",
            "root_call": {
                "normalization_base": 0,
                "normalization_depth": 1,
            },
        },
        "blockers": blockers,
        "evidence": {
            "copy_to_runtime": "FUN_006af300",
            "normalize_tree": "FUN_006af6c0",
            "index_leaves": "FUN_006af780",
            "release_leaves": "FUN_006af830",
            "runtime_link_indexer": "FUN_006af780",
            "runtime_link_table_builder": "FUN_006af330",
            "walk_leaves": "FUN_006af5a0",
            "recursive_object_lookup": "FUN_006af640 -> FUN_006b0440",
            "release_leaf_objects": "FUN_006af830",
        },
        "limitations": [
            "Unknown leaf payload words are preserved raw; only +0x38/+0x3c runtime consumers are named.",
            "The class behind a populated leaf +0x38 direct object pointer remains unresolved.",
            "High-byte span marker is exposed as runtime depth/termination metadata rather than assigned a higher-level scene meaning.",
        ],
    }
