from __future__ import annotations

import struct


def glass_fxo() -> bytes:
    ctab = bytearray(b"CTAB")
    ctab += struct.pack("<7I", 64, 32, 0x00030000, 0, 0, 0, 0)
    ctab += b"Microsoft\x00"
    ctab += bytes(64 - len(ctab))
    comment = struct.pack("<I", (16 << 16) | 0xFFFE) + ctab

    def blob(version: int, dst_type: int) -> bytes:
        b = bytearray(struct.pack("<I", version))
        b += comment
        dst = 0x80000000 | dst_type
        src = 0x80000000
        mov = struct.pack("<I", (2 << 24) | 1) + struct.pack("<II", dst, src)
        b += mov * 6
        b += struct.pack("<I", 0xFFFF)
        return bytes(b)

    return b"".join([
        blob(0xFFFE0300, 0x60000000),
        blob(0xFFFE0300, 0x60000000),
        blob(0xFFFF0300, 0x80000000),
        blob(0xFFFF0300, 0x80000000),
    ])


BASIC_FX = b'''#include "stddefs.fxh"\ntechnique First { pass P { } }\ntechnique Second { pass P { } }\n'''



def basic_bab() -> bytes:
    b = bytearray(b"BAB\x00")
    b += struct.pack("<7I", 13, 10, 0, 0, 1, 0, 0)
    b[0x18:0x30] = struct.pack(
        "<6I", 1, 3, 2, 0x3F700000, 2, 0
    )
    b += b"\x00" * (0x30 - len(b))
    for name, q, t in [
        ("Hips", (0, 0, 0, 1), (1, 2, 3)),
        ("Spine", (0, 0, 0, 1), (0, 1, 0)),
    ]:
        nb = name.encode()
        b += struct.pack("<I", len(nb)) + nb
        b += b"\x00" * ((-(len(nb) + 4) % 4))
        b += struct.pack("<7f", *q, *t)
        b += struct.pack("<I", 3) + struct.pack("<4f", 1, 1, 1, 0)
    return bytes(b)
