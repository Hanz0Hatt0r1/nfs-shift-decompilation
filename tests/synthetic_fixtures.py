from __future__ import annotations

import struct


def glass_fxo() -> bytes:
    out = bytearray()
    ctab = bytearray(b"CTAB")
    ctab += struct.pack("<7I", 64, 32, 0x00030000, 0, 0, 0, 0)
    ctab += b"Microsoft\x00"
    ctab += bytes(64 - len(ctab))
    comment = struct.pack("<I", (16 << 16) | 0xFFFE) + ctab
    def blob(version: int, dst_type: int) -> bytes:
        b = bytearray(struct.pack("<I", version))
        b += comment
        dst = 0x80000000 | (0 << 16) | dst_type
        src = 0x80000000 | 0
        mov = struct.pack("<I", (2 << 24) | 1) + struct.pack("<II", dst, src)
        b += mov * 6
        b += struct.pack("<I", 0xFFFF)
        return bytes(b)
    out += blob(0xFFFE0300, 0x60000000)
    out += blob(0xFFFE0300, 0x60000000)
    out += blob(0xFFFF0300, 0x80000000)
    out += blob(0xFFFF0300, 0x80000000)
    return bytes(out)
