"""Byte-level differential analysis for opaque SHIFT BAB animation payloads.

No keyframe meaning is inferred here. The analyzer only measures exact byte
relationships so later reverse-engineering can distinguish shared structure
from clip-varying data.
"""
from __future__ import annotations

import hashlib
from typing import Any


def _longest_equal_prefix(a: bytes, b: bytes) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def _longest_equal_suffix(a: bytes, b: bytes) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[-1 - i] == b[-1 - i]:
        i += 1
    return i


def _block_match_ratio(a: bytes, b: bytes, block_size: int) -> float:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    blocks_a = {
        a[i:i + block_size]
        for i in range(0, max(0, len(a) - block_size + 1), block_size)
    }
    if not blocks_a:
        return 0.0
    blocks_b = {
        b[i:i + block_size]
        for i in range(0, max(0, len(b) - block_size + 1), block_size)
    }
    return len(blocks_a & blocks_b) / len(blocks_a)


def compare_bab_payload_bytes(a: bytes, b: bytes) -> dict[str, Any]:
    """Measure payload byte relationships without interpreting their grammar."""
    overlap = min(len(a), len(b))
    equal_overlap = sum(1 for i in range(overlap) if a[i] == b[i])
    differing_overlap = overlap - equal_overlap
    return {
        "format": "SHIFT.BABPayloadByteComparison/1",
        "a": {
            "size": len(a),
            "sha256": hashlib.sha256(a).hexdigest(),
        },
        "b": {
            "size": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
        },
        "size_delta": len(a) - len(b),
        "overlap_size": overlap,
        "equal_overlap_bytes": equal_overlap,
        "differing_overlap_bytes": differing_overlap,
        "overlap_equal_ratio": (equal_overlap / overlap) if overlap else 1.0,
        "equal_prefix_bytes": _longest_equal_prefix(a, b),
        "equal_suffix_bytes": _longest_equal_suffix(a, b),
        "block_match_ratio": {
            str(size): _block_match_ratio(a, b, size)
            for size in (4, 8, 16, 32)
        },
    }
