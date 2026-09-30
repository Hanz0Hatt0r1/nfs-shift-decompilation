"""Source-equivalent 32-bit SHIFT string/byte hash used by FUN_0063ad50.

The raw byte implementation models the retail case-sensitive path exactly:
signed-byte accumulation, big-endian four-byte groups, 32-bit wraparound and
the recovered nine-step mix sequence.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.StringHash32/1"
FUNCTION = "FUN_0063ad50"
PE_ADDRESS = 0x0063AD50
INITIAL_CONSTANT = 0x9E3779B9
MASK32 = 0xFFFFFFFF


def _u32(value: int) -> int:
    return value & MASK32


def _s8(value: int) -> int:
    value &= 0xFF
    return value if value < 0x80 else value - 0x100


def _signed_be32(data: bytes, offset: int) -> int:
    value = _u32(_s8(data[offset]))
    value = _u32((value << 8) + _s8(data[offset + 1]))
    value = _u32((value << 8) + _s8(data[offset + 2]))
    value = _u32((value << 8) + _s8(data[offset + 3]))
    return value


def _mix(a: int, b: int, c: int) -> tuple[int, int, int]:
    a = _u32(_u32(a - c - b) ^ (c >> 13))
    b = _u32(_u32(b - c - a) ^ _u32(a << 8))
    c = _u32(_u32(c - b - a) ^ (b >> 13))

    a = _u32(_u32(a - c - b) ^ (c >> 12))
    b = _u32(_u32(b - c - a) ^ _u32(a << 16))
    c = _u32(_u32(c - b - a) ^ (b >> 5))

    a = _u32(_u32(a - c - b) ^ (c >> 3))
    b = _u32(_u32(b - c - a) ^ _u32(a << 10))
    c = _u32(_u32(c - b - a) ^ (b >> 15))
    return a, b, c


def shift_hash32(data: bytes, seed: int = 0) -> int:
    """Reproduce FUN_0063ad50 with its case-sensitive flag set.

    The retail x86 code uses MOVSX for every source byte, so bytes >= 0x80 are
    sign-extended before being accumulated. The explicit length is the byte
    length supplied here.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    a = INITIAL_CONSTANT
    b = INITIAL_CONSTANT
    c = _u32(seed)
    offset = 0
    remaining = len(data)

    while remaining > 11:
        a = _u32(a + _signed_be32(data, offset))
        b = _u32(b + _signed_be32(data, offset + 4))
        c = _u32(c + _signed_be32(data, offset + 8))
        a, b, c = _mix(a, b, c)
        offset += 12
        remaining -= 12

    c = _u32(c + len(data))

    if remaining >= 11:
        c = _u32(c + _u32(_s8(data[offset + 10]) << 24))
    if remaining >= 10:
        c = _u32(c + _u32(_s8(data[offset + 9]) << 16))
    if remaining >= 9:
        c = _u32(c + _u32(_s8(data[offset + 8]) << 8))

    if remaining >= 8:
        b = _u32(b + _u32(_s8(data[offset + 7]) << 24))
    if remaining >= 7:
        b = _u32(b + _u32(_s8(data[offset + 6]) << 16))
    if remaining >= 6:
        b = _u32(b + _u32(_s8(data[offset + 5]) << 8))
    if remaining >= 5:
        b = _u32(b + _u32(_s8(data[offset + 4])))

    if remaining >= 4:
        a = _u32(a + _u32(_s8(data[offset + 3]) << 24))
    if remaining >= 3:
        a = _u32(a + _u32(_s8(data[offset + 2]) << 16))
    if remaining >= 2:
        a = _u32(a + _u32(_s8(data[offset + 1]) << 8))
    if remaining >= 1:
        a = _u32(a + _u32(_s8(data[offset])))

    _, _, c = _mix(a, b, c)
    return c


def shift_hash32_ascii(
    text: str,
    seed: int = 0,
    *,
    case_sensitive: bool = True,
) -> int:
    """Hash ASCII text, including the retail optional uppercase branch.

    FUN_0063ad50 uses the CRT locale-sensitive strupr_s when its flag is zero.
    Restricting this convenience wrapper to ASCII avoids claiming parity for
    non-ASCII code-page/locale behavior. Raw case-sensitive bytes should use
    shift_hash32() directly.
    """
    data = text.encode("ascii")
    if not case_sensitive:
        data = data.upper()
    return shift_hash32(data, seed)


def describe_shift_hash32_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "pe_address": PE_ADDRESS,
        "initial_constant": INITIAL_CONSTANT,
        "case_sensitive_raw_bytes": {
            "implemented": True,
            "byte_load": "signed/movsx",
            "four_byte_order": "big-endian accumulation",
            "word_size_bits": 32,
            "wraparound": True,
            "block_size": 12,
            "length_added_to_seed_accumulator": True,
        },
        "case_insensitive_text": {
            "source_behavior": "copy up to 0xff bytes then CRT strupr_s",
            "ascii_wrapper_implemented": True,
            "non_ascii_locale_parity": False,
        },
        "evidence_boundary": (
            "Raw case-sensitive byte hashing is source/PE-equivalent. The "
            "optional uppercase convenience wrapper is parity-scoped to ASCII; "
            "non-ASCII CRT locale/code-page behavior is not inferred."
        ),
    }
