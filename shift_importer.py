#!/usr/bin/env python3
"""Need for Speed: SHIFT universal resource importer.

Features:
  * BFF v3 parsing (big-endian marker, little-endian fields as used by SHIFT)
  * Type 0 / Type 1 extraction
  * Type 2 XMem/LZX extraction with a pure-Python LZX decoder
  * resource signature/extension classification
  * manifest generation with compressed/uncompressed hashes
  * extraction preserving logical resource paths
  * package creation into a platform-neutral content-addressed tree

The LZX implementation follows the public algorithm used by OpenAssetTools's
LZX implementation and the XMem framing behavior documented by that project.
See NOTICE.md for attribution and source references.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import struct
import sys
import zlib
import ctypes

from resource_formats import analyze_decoded_resource, parse_bml, parse_reflection_xml, parse_dds_metadata
from shader_ir import parse_shader_blobs, parse_fx_source
from shader_asm import parse_program, to_glsl
from meb_format import read_meb, mesh_summary, mesh_to_jsonable, write_mgeo
from csm_format import read_csm, csm_summary, mesh_to_jsonable as csm_to_jsonable, write_cmesh
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

REC_SIZE = 42
NAME_REC_SIZE = 16
HEADER_RECORDS_OFFSET = 0x130
NAME_BASE_OFFSET = 0x438

# ---------------------------------------------------------------------------
# LZX / XMem
# ---------------------------------------------------------------------------

DECR_OK = 0
LZX_MIN_MATCH = 2
LZX_NUM_CHARS = 256
LZX_NUM_PRIMARY_LENGTHS = 7
LZX_NUM_SECONDARY_LENGTHS = 249

EXTRA_BITS = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8,
    9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16,
    17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17, 17,
]
POSITION_BASE = [
    0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192,
    256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096, 6144, 8192,
    12288, 16384, 24576, 32768, 49152, 65536, 98304, 131072, 196608,
    262144, 393216, 524288, 655360, 786432, 917504, 1048576, 1179648,
    1310720, 1441792, 1572864, 1703936, 1835008, 1966080, 2097152,
]


class BitReader:
    """LZX reads a stream as little-endian 16-bit words, MSB first."""

    def __init__(self, data: bytes):
        # The reference decoder permits a small amount of look-ahead.
        self.data = data + b"\x00\x00\x00\x00"
        self.pos = 0
        self.word = 0
        self.bits = 0

    def _fill_word(self) -> None:
        if self.pos + 2 > len(self.data):
            raise EOFError("LZX input exhausted")
        self.word = self.data[self.pos] | (self.data[self.pos + 1] << 8)
        self.pos += 2
        self.bits = 16

    def ensure(self, n: int) -> None:
        while self.bits < n:
            if self.bits == 0:
                self._fill_word()
                continue
            if self.pos + 2 > len(self.data):
                raise EOFError("LZX input exhausted")
            nxt = self.data[self.pos] | (self.data[self.pos + 1] << 8)
            self.pos += 2
            self.word = (self.word << 16) | nxt
            self.bits += 16

    def peek(self, n: int) -> int:
        self.ensure(n)
        return self.word >> (self.bits - n)

    def consume(self, n: int) -> None:
        if n < 0 or n > self.bits:
            raise ValueError("invalid bit consume")
        self.bits -= n
        self.word &= (1 << self.bits) - 1 if self.bits else 0

    def read(self, n: int) -> int:
        if n < 0 or n > 24:
            raise ValueError(f"invalid bit count: {n}")
        if n == 0:
            return 0
        value = self.peek(n)
        self.consume(n)
        return value

    def align16(self) -> None:
        self.word = 0
        self.bits = 0

    def read_u32le(self) -> int:
        if self.bits != 0:
            raise RuntimeError("LZX stream not word-aligned")
        p = self.pos
        if p + 4 > len(self.data):
            raise EOFError("LZX input exhausted")
        self.pos += 4
        return (
            self.data[p]
            | (self.data[p + 1] << 8)
            | (self.data[p + 2] << 16)
            | (self.data[p + 3] << 24)
        )


@dataclass
class HuffmanTable:
    table_bits: int
    lookup: list[int]
    long_codes: dict[tuple[int, int], int]

    def decode(self, br: "BitReader") -> int:
        br.ensure(self.table_bits)
        prefix = br.peek(self.table_bits)
        packed = self.lookup[prefix]
        if packed:
            length = packed >> 16
            symbol = packed & 0xFFFF
            br.consume(length)
            return symbol
        # Rare long-code path. The first table_bits have already been
        # inspected but not consumed, so continue one bit at a time.
        code = 0
        for length in range(1, 17):
            code = (code << 1) | br.read(1)
            symbol = self.long_codes.get((length, code))
            if symbol is not None:
                return symbol
        raise ValueError("invalid LZX Huffman code")


def build_huffman(lengths: list[int], table_bits: int = 12) -> HuffmanTable:
    """Build canonical MSB-first Huffman lookup tables."""
    max_len = max(lengths, default=0)
    counts = [0] * (max_len + 1)
    for length in lengths:
        if length:
            counts[length] += 1
    next_code = [0] * (max_len + 1)
    code = 0
    for bits in range(1, max_len + 1):
        code = (code + counts[bits - 1]) << 1
        next_code[bits] = code

    long_codes: dict[tuple[int, int], int] = {}
    table = [0] * (1 << table_bits)
    for symbol, length in enumerate(lengths):
        if not length:
            continue
        c = next_code[length]
        next_code[length] += 1
        long_codes[(length, c)] = symbol
        if length <= table_bits:
            base = c << (table_bits - length)
            fill = 1 << (table_bits - length)
            packed = (length << 16) | symbol
            for idx in range(base, base + fill):
                table[idx] = packed
    return HuffmanTable(table_bits, table, long_codes)


def read_huffman(br: BitReader, table: HuffmanTable) -> int:
    return table.decode(br)


def read_code_lengths(br: BitReader, lengths: list[int], first: int, last: int) -> None:
    pretree = [br.read(4) for _ in range(20)]
    pretree_table = build_huffman(pretree, 6)
    x = first
    while x < last:
        z = read_huffman(br, pretree_table)
        if z == 17:
            run = br.read(4) + 4
            if x + run > last:
                raise ValueError("LZX code-length run overruns table")
            for _ in range(run):
                lengths[x] = 0
                x += 1
        elif z == 18:
            run = br.read(5) + 20
            if x + run > last:
                raise ValueError("LZX code-length run overruns table")
            for _ in range(run):
                lengths[x] = 0
                x += 1
        elif z == 19:
            run = br.read(1) + 4
            z2 = read_huffman(br, pretree_table)
            z2 = lengths[x] - z2
            if z2 < 0:
                z2 += 17
            if x + run > last:
                raise ValueError("LZX code-length run overruns table")
            for _ in range(run):
                lengths[x] = z2
                x += 1
        else:
            z2 = lengths[x] - z
            if z2 < 0:
                z2 += 17
            lengths[x] = z2
            x += 1


class LZXState:
    """Enough mutable state to decode a complete XMem Type-2 stream."""

    def __init__(self, window_bits: int = 17):
        if not 15 <= window_bits <= 21:
            raise ValueError("LZX window must be 15..21 bits")
        self.window_size = 1 << window_bits
        self.window = bytearray(self.window_size)
        pos_slots = 42 if window_bits == 20 else 50 if window_bits == 21 else window_bits * 2
        self.main_elements = 256 + (pos_slots << 3)
        self.reset()

    def reset(self) -> None:
        self.window_posn = 0
        self.r0 = self.r1 = self.r2 = 1
        self.header_read = False
        self.block_type = 0
        self.block_length = 0
        self.block_remaining = 0
        self.frames_read = 0
        self.intel_filesize = 0
        self.intel_curpos = 0
        self.intel_started = False
        self.main_lengths = [0] * self.main_elements
        self.length_lengths = [0] * 250
        self.aligned_lengths = [0] * 8
        self.main_table = build_huffman(self.main_lengths, 12)
        self.length_table = build_huffman(self.length_lengths, 12)
        self.aligned_table = build_huffman(self.aligned_lengths, 7)

    def process(self, data: bytes, outlen: int) -> bytes:
        if outlen <= 0 or outlen > 0x8000:
            raise ValueError(f"unsupported XMem output block size: {outlen}")
        br = BitReader(data)
        window = self.window
        ws = self.window_size
        wp = self.window_posn
        r0, r1, r2 = self.r0, self.r1, self.r2

        if not self.header_read:
            has_intel_header = br.read(1)
            i = j = 0
            if has_intel_header:
                i = br.read(16)
                j = br.read(16)
            self.intel_filesize = (i << 16) | j
            self.header_read = True

        togo = outlen
        while togo > 0:
            if self.block_remaining == 0:
                if self.block_type == 3:
                    br.align16()

                block_type = br.read(3)
                i = br.read(16)
                j = br.read(8)
                block_length = (i << 8) | j
                if block_length == 0:
                    raise ValueError("zero-length LZX block")
                self.block_type = block_type
                self.block_length = block_length
                self.block_remaining = block_length

                if block_type == 2:
                    self.aligned_lengths = [br.read(3) for _ in range(8)]
                    self.aligned_table = build_huffman(self.aligned_lengths, 7)
                if block_type in (1, 2):
                    read_code_lengths(br, self.main_lengths, 0, 256)
                    read_code_lengths(br, self.main_lengths, 256, self.main_elements)
                    self.main_table = build_huffman(self.main_lengths, 12)
                    if self.main_lengths[0xE8] != 0:
                        self.intel_started = True
                    read_code_lengths(br, self.length_lengths, 0, LZX_NUM_SECONDARY_LENGTHS)
                    self.length_table = build_huffman(self.length_lengths, 12)
                elif block_type == 3:
                    self.intel_started = True
                    br.align16()
                    r0 = br.read_u32le()
                    r1 = br.read_u32le()
                    r2 = br.read_u32le()
                else:
                    raise ValueError(f"illegal LZX block type {block_type}")

            this_run = min(self.block_remaining, togo)
            togo -= this_run
            self.block_remaining -= this_run

            wp &= ws - 1
            if wp + this_run > ws:
                raise ValueError("LZX run crosses window boundary")

            if self.block_type == 3:
                if br.pos + this_run > len(br.data):
                    raise EOFError("LZX uncompressed block exceeds input")
                window[wp:wp + this_run] = br.data[br.pos:br.pos + this_run]
                br.pos += this_run
                wp += this_run
                continue

            while this_run > 0:
                main_element = read_huffman(br, self.main_table)
                if main_element < LZX_NUM_CHARS:
                    window[wp] = main_element
                    wp += 1
                    this_run -= 1
                    continue

                main_element -= LZX_NUM_CHARS
                match_length = main_element & LZX_NUM_PRIMARY_LENGTHS
                if match_length == LZX_NUM_PRIMARY_LENGTHS:
                    match_length += read_huffman(br, self.length_table)
                match_length += LZX_MIN_MATCH

                match_offset = main_element >> 3
                if match_offset > 2:
                    extra = EXTRA_BITS[match_offset]
                    if self.block_type == 1:
                        if match_offset != 3:
                            verbatim = br.read(extra)
                            match_offset = POSITION_BASE[match_offset] - 2 + verbatim
                        else:
                            match_offset = 1
                    else:
                        match_offset = POSITION_BASE[match_offset] - 2
                        if extra > 3:
                            extra -= 3
                            verbatim = br.read(extra)
                            match_offset += verbatim << 3
                            match_offset += read_huffman(br, self.aligned_table)
                        elif extra == 3:
                            match_offset += read_huffman(br, self.aligned_table)
                        elif extra > 0:
                            match_offset += br.read(extra)
                        else:
                            match_offset = 1
                    r2, r1, r0 = r1, r0, match_offset
                elif match_offset == 0:
                    match_offset = r0
                elif match_offset == 1:
                    match_offset = r1
                    r1, r0 = r0, match_offset
                else:
                    match_offset = r2
                    r2, r0 = r0, match_offset

                dest = wp
                src = wp - match_offset
                wp += match_length
                if wp > ws:
                    raise ValueError("LZX match crosses window boundary")
                this_run -= match_length

                remain = match_length
                while src < 0 and remain > 0:
                    window[dest] = window[src + ws]
                    dest += 1
                    src += 1
                    remain -= 1
                while remain > 0:
                    window[dest] = window[src]
                    dest += 1
                    src += 1
                    remain -= 1

        end = ws if wp == 0 else wp
        start = end - outlen
        if start < 0:
            raise ValueError("LZX output window underflow")
        out = bytearray(window[start:end])

        self.window_posn = wp
        self.r0, self.r1, self.r2 = r0, r1, r2
        self.frames_read += 1

        # Intel E8 transform, matching the public reference implementation.
        if self.frames_read < 32768 and self.intel_filesize:
            if outlen <= 6 or not self.intel_started:
                self.intel_curpos += outlen
            else:
                data_end = max(0, outlen - 10)
                curpos = self.intel_curpos
                filesize = self.intel_filesize
                p = 0
                while p < data_end:
                    if out[p] != 0xE8:
                        p += 1
                        curpos += 1
                        continue
                    abs_off = int.from_bytes(out[p + 1:p + 5], "little", signed=True)
                    if -curpos <= abs_off < filesize:
                        rel_off = abs_off - curpos if abs_off >= 0 else abs_off + filesize
                        out[p + 1:p + 5] = int(rel_off & 0xFFFFFFFF).to_bytes(4, "little")
                    p += 5
                    curpos += 5
                self.intel_curpos += outlen
        return bytes(out)


_NATIVE_LZX = None
_NATIVE_LZX_ATTEMPTED = False

def _native_xmem_decompress(data: bytes, expected_size: int) -> bytes | None:
    """Use the optional native LZX backend when built next to the importer."""
    global _NATIVE_LZX, _NATIVE_LZX_ATTEMPTED
    if _NATIVE_LZX_ATTEMPTED:
        if _NATIVE_LZX is None:
            return None
    else:
        _NATIVE_LZX_ATTEMPTED = True
        candidates = [
            Path(__file__).with_name("native_ir") / "build" / "libshift_lzx.so",
            Path(__file__).with_name("native_ir") / "build" / "libshift_lzx.dylib",
            Path(__file__).with_name("native_ir") / "build" / "shift_lzx.dll",
        ]
        for cand in candidates:
            if cand.exists():
                try:
                    lib = ctypes.CDLL(str(cand))
                    fn = lib.shift_xmem_decompress
                    fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
                    fn.restype = ctypes.c_int
                    _NATIVE_LZX = fn
                    break
                except OSError:
                    pass
    if _NATIVE_LZX is None:
        return None
    src = ctypes.create_string_buffer(data)
    dst = ctypes.create_string_buffer(expected_size)
    rc = _NATIVE_LZX(src, len(data), dst, expected_size, expected_size)
    if rc != 0:
        raise ValueError(f"native XMem/LZX decoder failed with code {rc}")
    return dst.raw


def xmem_decompress(data: bytes, expected_size: int, *, reset: bool = True) -> bytes:
    """Decode a SHIFT Type-2 XMem/LZX stream."""
    if reset and os.environ.get("SHIFT_LZX_NATIVE") == "1":
        native = _native_xmem_decompress(data, expected_size)
        if native is not None:
            return native
    state = LZXState(17)
    if reset:
        state.reset()
    out = bytearray()
    pos = 0
    blocks: list[tuple[int, int]] = []
    while pos < len(data) and len(out) < expected_size:
        high = data[pos]
        pos += 1
        if high == 0xFF:
            if pos + 4 > len(data):
                raise ValueError("truncated XMem short-block header")
            dst_size = int.from_bytes(data[pos:pos + 2], "big")
            src_size = int.from_bytes(data[pos + 2:pos + 4], "big")
            pos += 4
            suffix = 5
        else:
            if pos >= len(data):
                raise ValueError("truncated XMem block header")
            dst_size = 0x8000
            src_size = (high << 8) | data[pos]
            pos += 1
            suffix = 0

        if src_size == 0 or dst_size == 0:
            raise ValueError("invalid zero-sized XMem block")
        if pos + src_size > len(data):
            raise ValueError("XMem block extends past compressed payload")
        payload = data[pos:pos + src_size]
        pos += src_size
        decoded = state.process(payload, dst_size)
        if len(decoded) != dst_size:
            raise ValueError("LZX decoder returned wrong block size")
        out += decoded
        blocks.append((src_size, dst_size))
        if suffix:
            if pos + suffix > len(data):
                raise ValueError("XMem suffix extends past compressed payload")
            pos += suffix

    if len(out) != expected_size:
        raise ValueError(f"XMem decoded {len(out)} bytes, expected {expected_size}; blocks={blocks}")
    return bytes(out)


# ---------------------------------------------------------------------------
# BFF
# ---------------------------------------------------------------------------

@dataclass
class Entry:
    archive: str
    index: int
    path: str
    offset: int
    compressed_size: int
    uncompressed_size: int
    type: int
    crc32_field: int
    fileext: int


class BFF:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._fp = self.path.open("rb")
        self._size = self.path.stat().st_size
        if self._size < NAME_BASE_OFFSET:
            raise ValueError(f"{self.path}: too small for BFF header")

        hdr = self._fp.read(0x438)
        self.magic = hdr[:4]
        self.version = struct.unpack_from("<I", hdr, 4)[0] & 0xFF
        self.file_count = struct.unpack_from("<I", hdr, 8)[0]
        self.x118 = struct.unpack_from("<I", hdr, 0x118)[0]
        self.x120_raw = struct.unpack_from("<I", hdr, 0x120)[0]
        self.x120 = self.x120_raw - 0x308
        self.x12d = hdr[0x12D]
        if self.magic not in (b" KAP", b"PAK "):
            raise ValueError(f"{self.path}: not a SHIFT BFF/PAK archive ({self.magic!r})")
        if self.x118 != self.file_count * REC_SIZE:
            raise ValueError(
                f"{self.path}: record table mismatch x118=0x{self.x118:X}, "
                f"expected=0x{self.file_count * REC_SIZE:X}"
            )

        self.records_offset = HEADER_RECORDS_OFFSET
        self.name_base = NAME_BASE_OFFSET + self.x118
        self.name_end = self.name_base + self.x120
        if self.name_end > self._size:
            raise ValueError(f"{self.path}: name table exceeds file size")
        self.entries = list(self._read_entries())

    def close(self) -> None:
        try:
            self._fp.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _read_entries(self) -> Iterator[Entry]:
        self._fp.seek(self.records_offset)
        records = self._fp.read(self.file_count * REC_SIZE)
        for i in range(self.file_count):
            ro = i * REC_SIZE
            offset = struct.unpack_from("<Q", records, ro + 8)[0]
            zsize = struct.unpack_from("<I", records, ro + 16)[0]
            size = struct.unpack_from("<I", records, ro + 20)[0]
            typ = records[ro + 32]
            crc = struct.unpack_from("<I", records, ro + 34)[0]
            ext = struct.unpack_from("<I", records, ro + 38)[0]
            self._fp.seek(self.name_base + i * NAME_REC_SIZE)
            name_off = struct.unpack("<Q", self._fp.read(8))[0]
            if not (self.name_base <= name_off < self.name_end):
                raise ValueError(f"{self.path}: entry {i} has invalid name offset 0x{name_off:X}")
            self._fp.seek(name_off)
            nraw = self._fp.read(1)
            if not nraw:
                raise ValueError(f"{self.path}: entry {i} missing name length")
            n = nraw[0]
            name = self._fp.read(n).decode("utf-8", "replace").replace("\\", "/")
            if offset + zsize > self._size:
                raise ValueError(f"{self.path}: entry {i} data range outside archive")
            yield Entry(self.path.name, i, name, offset, zsize, size, typ, crc, ext)

    def raw_payload(self, entry: Entry) -> bytes:
        self._fp.seek(entry.offset)
        return self._fp.read(entry.compressed_size)

    def extract_entry(self, entry: Entry, type2: str = "lzx") -> bytes:
        payload = self.raw_payload(entry)
        if entry.type == 0:
            out = payload[:entry.uncompressed_size]
        elif entry.type == 1:
            out = zlib.decompress(payload)
        elif entry.type == 2:
            if type2 == "raw":
                return payload
            out = xmem_decompress(payload, entry.uncompressed_size)
        else:
            raise ValueError(f"{entry.path}: unsupported BFF compression type {entry.type}")
        if len(out) != entry.uncompressed_size:
            raise ValueError(
                f"{entry.path}: decoded {len(out)} bytes, expected {entry.uncompressed_size}"
            )
        return out

    def extract_entry_to_file(
        self,
        entry: Entry,
        output_path: str | os.PathLike[str],
        type2: str = "lzx",
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        """Extract one entry directly to disk without retaining the decoded file in RAM."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._fp.seek(entry.offset)

        if entry.type == 0:
            remaining = entry.uncompressed_size
            with out_path.open("wb") as out:
                while remaining:
                    chunk = self._fp.read(min(chunk_size, remaining))
                    if not chunk:
                        raise ValueError(f"{entry.path}: truncated raw payload")
                    out.write(chunk)
                    remaining -= len(chunk)
            return out_path

        if entry.type == 1:
            decoder = zlib.decompressobj()
            remaining = entry.compressed_size
            with out_path.open("wb") as out:
                while remaining:
                    chunk = self._fp.read(min(chunk_size, remaining))
                    if not chunk:
                        raise ValueError(f"{entry.path}: truncated zlib payload")
                    remaining -= len(chunk)
                    decoded = decoder.decompress(chunk)
                    if decoded:
                        out.write(decoded)
                tail = decoder.flush()
                if tail:
                    out.write(tail)
            size = out_path.stat().st_size
            if size != entry.uncompressed_size:
                raise ValueError(
                    f"{entry.path}: decoded {size} bytes, expected {entry.uncompressed_size}"
                )
            return out_path

        if entry.type == 2:
            if type2 == "raw":
                remaining = entry.compressed_size
                with out_path.open("wb") as out:
                    while remaining:
                        chunk = self._fp.read(min(chunk_size, remaining))
                        if not chunk:
                            raise ValueError(f"{entry.path}: truncated raw XMem payload")
                        out.write(chunk)
                        remaining -= len(chunk)
                return out_path

            state = LZXState(17)
            state.reset()
            compressed_remaining = entry.compressed_size
            decoded_total = 0

            def read_exact(size: int) -> bytes:
                nonlocal compressed_remaining
                if size > compressed_remaining:
                    raise ValueError(f"{entry.path}: XMem block exceeds compressed payload")
                data = self._fp.read(size)
                if len(data) != size:
                    raise ValueError(f"{entry.path}: truncated XMem payload")
                compressed_remaining -= size
                return data

            with out_path.open("wb") as out:
                while decoded_total < entry.uncompressed_size:
                    high = read_exact(1)[0]
                    if high == 0xFF:
                        header = read_exact(4)
                        dst_size = int.from_bytes(header[:2], "big")
                        src_size = int.from_bytes(header[2:], "big")
                        suffix = 5
                    else:
                        low = read_exact(1)[0]
                        dst_size = 0x8000
                        src_size = (high << 8) | low
                        suffix = 0
                    if src_size == 0 or dst_size == 0:
                        raise ValueError(f"{entry.path}: invalid zero-sized XMem block")
                    payload = read_exact(src_size)
                    decoded = state.process(payload, dst_size)
                    if len(decoded) != dst_size:
                        raise ValueError(f"{entry.path}: LZX decoder returned wrong block size")
                    out.write(decoded)
                    decoded_total += len(decoded)
                    if suffix:
                        read_exact(suffix)

            if decoded_total != entry.uncompressed_size:
                raise ValueError(
                    f"{entry.path}: decoded {decoded_total} bytes, expected {entry.uncompressed_size}"
                )
            return out_path

        raise ValueError(f"{entry.path}: unsupported BFF compression type {entry.type}")



# ---------------------------------------------------------------------------
# Classification / dependency hints
# ---------------------------------------------------------------------------

EXT_CATEGORY = {
    ".dds": "TEXTURE",
    ".png": "TEXTURE",
    ".jpg": "TEXTURE",
    ".jpeg": "TEXTURE",
    ".tga": "TEXTURE",
    ".bmp": "TEXTURE",
    ".fx": "SHADER",
    ".fxh": "SHADER",
    ".fxo": "SHADER_BINARY",
    ".bmt": "MATERIAL",
    ".meb": "MESH",
    ".vhf": "VEHICLE_RENDER",
    ".cpt": "COCKPIT",
    ".cgp": "VEHICLE_PHYSICS",
    ".csd": "VEHICLE_PHYSICS",
    ".cdp": "VEHICLE_PHYSICS",
    ".cdv": "VEHICLE_PHYSICS",
    ".vud": "VEHICLE_DATA",
    ".gdf": "GEARBOX_DATA",
    ".edf": "ENGINE_DATA",
    ".sdf": "SUSPENSION_DATA",
    ".tbf": "TURBO_DATA",
    ".joi": "COLLISION",
    ".xml": "CONFIG_XML",
    ".bml": "SCRIPT_BML",
    ".bmdef": "GUI_DEFINITION",
    ".bab": "ANIMATION",
    ".bas": "ANIMATION",
    ".imb": "ANIMATION",
    ".spe": "EFFECT",
    ".lod": "LOD",
    ".lsd": "SCENE_DATA",
    ".enx": "SCENE_DATA",
    ".sgb": "SCENE_DATA",
    ".trd": "TRACK_DATA",
    ".new": "TRACK_DATA",
    ".fsb": "AUDIO_FSB",
    ".fev": "AUDIO_FEV",
    ".rcf": "CHARACTER_DATA",
    ".log": "TEXT_OR_LOG",
    ".bad": "CONFIG",
}

MAGIC_CATEGORY = [
    (b"DDS ", "TEXTURE"),
    (b"RIFF", "AUDIO_OR_RIFF"),
    (b"OggS", "AUDIO"),
    (b"PK\x03\x04", "ZIP_CONTAINER"),
    (b"<?xml", "CONFIG_XML"),
    (b"<", "TEXT"),
]

PATH_CATEGORY = [
    ("/physics/", "VEHICLE_PHYSICS"),
    ("/collision/", "COLLISION"),
    ("/tracks/", "TRACK"),
    ("/vehicles/", "VEHICLE"),
    ("/render/", "RENDER"),
    ("/characters/", "CHARACTER"),
    ("/animation/", "ANIMATION"),
    ("/effects/", "EFFECT"),
    ("/ai/", "AI"),
    ("/cameras/", "CAMERA"),
    ("/gui/", "GUI"),
    ("/campaign/", "CAMPAIGN"),
    ("/scripts/", "SCRIPT"),
    ("/audio/", "AUDIO"),
]


# Conservative path-like dependency regex; false positives are intentionally
# allowed and marked as "hint" in the graph.
DEP_RE = re.compile(
    rb"(?P<q>['\"])(?P<path>[A-Za-z0-9_./\\ -]+\.(?:dds|meb|bmt|mtx|vhf|xml|bml|fxo|fx|fxh|bab|bas|imb|fsb|fev|cgp|csd|cdp|cdv|vud|gdf|edf|sdf|tbf|cpt|lod|spe|sgb|trd|new|joi))(?:['\"])?"
)


def classify(path: str, data: bytes | None = None) -> str:
    lower = path.lower().replace("\\", "/")
    ext = Path(lower).suffix
    ext_cat = EXT_CATEGORY.get(ext)
    if data:
        head = data[:64].lstrip()
        for sig, cat in MAGIC_CATEGORY:
            if data.startswith(sig) or head.startswith(sig):
                if cat == "AUDIO_OR_RIFF" and lower.endswith(".fsb"):
                    return "AUDIO_FSB"
                return cat
    if ext_cat:
        return ext_cat
    for needle, category in PATH_CATEGORY:
        if needle in "/" + lower:
            return category
    return "UNKNOWN"


def dependency_hints(data: bytes, source_path: str) -> list[str]:
    hints: list[str] = []
    source_norm = source_path.replace("\\", "/")
    scan_data = data
    if source_norm.lower().endswith((".fx", ".fxh")):
        # Includes inside shader comments are not dependencies. Keep the raw
        # resource untouched; only sanitize the scanner input.
        scan_data = re.sub(rb"/\*.*?\*/", b"", scan_data, flags=re.S)
        scan_data = re.sub(rb"//[^\r\n]*", b"", scan_data)
    for m in DEP_RE.finditer(scan_data):
        raw = m.group("path").decode("utf-8", "replace").replace("\\", "/")
        if raw != source_norm and raw not in hints:
            hints.append(raw)

    # MEB stores material paths as raw C-strings rather than quoted XML.
    if source_norm.lower().endswith(".meb"):
        try:
            from meb_format import read_meb
            mesh = read_meb(data)
            for prim in mesh.primitives:
                raw = prim.material.replace("\\", "/")
                if raw and raw not in hints:
                    hints.append(raw)
        except Exception:
            pass

    # BMT's material graph contains semantic shader/texture links that are not
    # necessarily quoted in the binary representation.
    if source_norm.lower().endswith(".bmt"):
        try:
            from resource_formats import parse_bmt_material
            mat = parse_bmt_material(data).get("material", {})
            for raw in [mat.get("shader"), *mat.get("textures", [])]:
                if raw:
                    raw = str(raw).replace("\\", "/")
                    if raw not in hints:
                        hints.append(raw)
            for param in mat.get("shaderparams", []):
                value = param.get("value")
                if isinstance(value, str) and any(value.lower().endswith(ext) for ext in (".dds", ".fx", ".fxo", ".bmt", ".mtx")):
                    if value not in hints:
                        hints.append(value.replace("\\", "/"))
        except Exception:
            pass
    return hints[:256]


def normalize_ref(path: str) -> str:
    """Normalize a SHIFT resource reference for graph resolution."""
    p = path.replace("\\", "/").strip().lower()
    while p.startswith("./"):
        p = p[2:]
    return p


def resolve_resource_ref(ref: str, path_map: dict[str, list[tuple[str, str]]], basename_map: dict[str, list[tuple[str, str]]]) -> list[dict[str, str]]:
    """Resolve an in-game reference; .mtx/.bmt is a known legacy alias."""
    n = normalize_ref(ref)
    candidates = [n]
    if n.endswith(".mtx"):
        candidates.append(n[:-4] + ".bmt")
    elif n.endswith(".bmt"):
        candidates.append(n[:-4] + ".mtx")
    if n.endswith(".fx"):
        candidates.append(n[:-3] + ".fxh")
    elif n.endswith(".fxh"):
        candidates.append(n[:-4] + ".fx")
    hits: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for c in candidates:
        for archive, logical in path_map.get(c, []):
            key = (archive, logical)
            if key not in seen:
                hits.append({"archive": archive, "path": logical, "method": "path"})
                seen.add(key)
    if not hits:
        bases = [Path(c).name for c in candidates]
        for base in bases:
            for archive, logical in basename_map.get(base, []):
                key = (archive, logical)
                if key not in seen:
                    hits.append({"archive": archive, "path": logical, "method": "basename"})
                    seen.add(key)
    return hits


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_bffs(root: Path) -> Iterator[Path]:
    if root.is_file() and root.suffix.lower() == ".bff":
        yield root
        return
    for p in sorted(root.rglob("*.bff")):
        if p.is_file():
            yield p


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_inspect(args: argparse.Namespace) -> int:
    with BFF(args.file) as bff:
        from collections import Counter
        types = Counter(e.type for e in bff.entries)
        exts = Counter(Path(e.path).suffix.lower() or "<none>" for e in bff.entries)
        roots = Counter(e.path.split("/", 1)[0].lower() for e in bff.entries)
        raw = sum(e.uncompressed_size for e in bff.entries)
        packed = sum(e.compressed_size for e in bff.entries)
        print(f"file: {bff.path}")
        print(f"magic: {bff.magic!r}")
        print(f"version: {bff.version}")
        print(f"files: {bff.file_count}")
        print(f"record_table: 0x{bff.records_offset:X} + {bff.x118} bytes")
        print(f"name_table: 0x{bff.name_base:X} + {bff.x120} bytes")
        print(f"types: {dict(sorted(types.items()))}")
        print(f"compressed: {packed} ({packed / 1048576:.2f} MiB)")
        print(f"uncompressed: {raw} ({raw / 1048576:.2f} MiB)")
        print("extensions:", dict(exts.most_common()))
        print("roots:", dict(roots.most_common()))
        for e in bff.entries[:args.samples]:
            print(f"  {e.index:4d} t={e.type} {e.path} {e.compressed_size}->{e.uncompressed_size}")
    return 0



def _resource_analysis_output(data: bytes, path: str) -> dict:
    return analyze_decoded_resource(path, data)


def cmd_analyze_resource(args: argparse.Namespace) -> int:
    """Decode one BFF resource and emit format-aware JSON analysis."""
    with BFF(args.archive) as bff:
        matches = [e for e in bff.entries if e.path == args.resource]
        if not matches:
            needle = args.resource.lower().replace("\\", "/")
            matches = [e for e in bff.entries if e.path.lower().replace("\\", "/") == needle]
        if not matches:
            raise SystemExit(f"resource not found: {args.resource}")
        e = matches[0]
        data = bff.extract_entry(e, type2="lzx")
        result = {
            "archive": bff.path.name,
            "entry": asdict(e),
            "sha256": sha256(data),
            "category": classify(e.path, data),
            "dependency_hints": dependency_hints(data, e.path),
            "analysis": _resource_analysis_output(data, e.path),
        }
        out = Path(args.output) if args.output else None
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_analyze_dir(args: argparse.Namespace) -> int:
    """Decode selected resources and write a compact format analysis set."""
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    wanted_exts = {x.lower() if x.startswith(".") else "." + x.lower() for x in args.ext}
    rows = []
    for bp in inputs:
        emitted = 0
        with BFF(bp) as bff:
            for e in bff.entries:
                if wanted_exts and Path(e.path).suffix.lower() not in wanted_exts:
                    continue
                if args.max_per_archive and emitted >= args.max_per_archive:
                    break
                try:
                    d = bff.extract_entry(e, type2="lzx")
                    a = _resource_analysis_output(d, e.path)
                    row = {**asdict(e), "sha256": sha256(d), "category": classify(e.path, d), "analysis": a["analysis"]}
                    rows.append(row)
                    emitted += 1
                except Exception as exc:
                    rows.append({**asdict(e), "error": f"{type(exc).__name__}: {exc}"})
                    emitted += 1
    (out / "resource_analysis.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"analyzed {len(rows)} resources -> {out / 'resource_analysis.json'}")
    return 0

def cmd_convert_meb(args: argparse.Namespace) -> int:
    """Convert one SHIFT MEB mesh into Android-neutral MGEO or JSON."""
    source = Path(args.input)
    data: bytes
    source_name = source.name

    if source.suffix.lower() == ".bff":
        if not args.resource:
            raise SystemExit("--resource is required when input is a .bff archive")
        with BFF(source) as bff:
            needle = args.resource.lower().replace("\\", "/")
            matches = [e for e in bff.entries if e.path.lower().replace("\\", "/") == needle]
            if not matches:
                raise SystemExit(f"resource not found: {args.resource}")
            e = matches[0]
            data = bff.extract_entry(e, type2="lzx")
            source_name = e.path
    else:
        data = source.read_bytes()

    if not source_name.lower().endswith(".meb"):
        raise SystemExit(f"input is not a .meb resource: {source_name}")

    mesh = read_meb(data)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        out.write_text(json.dumps(mesh_to_jsonable(mesh), ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        write_mgeo(mesh, out)
    print(json.dumps({"input": source_name, "output": str(out), **mesh_summary(mesh)}, ensure_ascii=False, indent=2))
    return 0


def cmd_convert_csm(args: argparse.Namespace) -> int:
    """Convert one SHIFT CSM collision mesh into Android-neutral CMES or JSON."""
    source = Path(args.input)
    if source.suffix.lower() == ".bff":
        if not args.resource:
            raise SystemExit("--resource is required when input is a .bff archive")
        with BFF(source) as bff:
            needle = args.resource.lower().replace("\\", "/")
            matches = [e for e in bff.entries if e.path.lower().replace("\\", "/") == needle]
            if not matches:
                raise SystemExit(f"resource not found: {args.resource}")
            data = bff.extract_entry(matches[0], type2="lzx")
            source_name = matches[0].path
    else:
        data = source.read_bytes()
        source_name = source.name
    if not source_name.lower().endswith(".csm"):
        raise SystemExit(f"input is not a .csm resource: {source_name}")
    mesh = read_csm(data)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        out.write_text(json.dumps(csm_to_jsonable(mesh), ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        write_cmesh(mesh, out)
    print(json.dumps({"input": source_name, "output": str(out), **csm_summary(mesh)}, ensure_ascii=False, indent=2))
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Build a cross-BFF dependency graph with legacy path normalization."""
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    wanted_exts = {x.lower() if x.startswith(".") else "." + x.lower() for x in args.ext}

    path_map: dict[str, list[tuple[str, str]]] = {}
    basename_map: dict[str, list[tuple[str, str]]] = {}
    entries: list[tuple[Path, object]] = []
    for bp in inputs:
        with BFF(bp) as bff:
            # Copy entry objects; BFF itself is reopened during decode.
            for e in bff.entries:
                n = normalize_ref(e.path)
                path_map.setdefault(n, []).append((bp.name, e.path))
                basename_map.setdefault(Path(n).name, []).append((bp.name, e.path))
                if Path(n).suffix in wanted_exts:
                    entries.append((bp, e))

    nodes: list[dict] = []
    edges: list[dict] = []
    unresolved: list[dict] = []
    stats = {"archives": len(inputs), "selected_entries": len(entries), "nodes": 0, "edges": 0, "resolved_edges": 0, "unresolved_refs": 0}
    cache: dict[str, bytes] = {}
    for bp, e in entries:
        key = f"{bp.name}:{e.index}"
        try:
            with BFF(bp) as bff:
                data = bff.extract_entry(e, type2="lzx")
            refs = dependency_hints(data, e.path)
            node = {"id": key, "archive": bp.name, "path": e.path, "category": classify(e.path, data), "sha256": sha256(data)}
            nodes.append(node); stats["nodes"] += 1
            for ref in refs:
                hits = resolve_resource_ref(ref, path_map, basename_map)
                edge = {"from": key, "ref": ref, "resolved": hits}
                edges.append(edge); stats["edges"] += 1
                if hits:
                    stats["resolved_edges"] += 1
                else:
                    stats["unresolved_refs"] += 1; unresolved.append({"from": key, "ref": ref})
        except Exception as exc:
            nodes.append({"id": key, "archive": bp.name, "path": e.path, "error": f"{type(exc).__name__}: {exc}"}); stats["nodes"] += 1

    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    report = {"stats": stats, "nodes": nodes, "edges": edges, "unresolved": unresolved}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"graph: {out}")
    return 1 if args.fail_on_unresolved and unresolved else 0


def cmd_build_ir(args: argparse.Namespace) -> int:
    """Build an Android-oriented intermediate representation from selected BFF resources."""
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    wanted_exts = {x.lower() if x.startswith(".") else "." + x.lower() for x in args.ext}

    path_map: dict[str, list[tuple[str, str]]] = {}
    basename_map: dict[str, list[tuple[str, str]]] = {}
    for bp in inputs:
        with BFF(bp) as bff:
            for e in bff.entries:
                n = normalize_ref(e.path)
                path_map.setdefault(n, []).append((bp.name, e.path))
                basename_map.setdefault(Path(n).name, []).append((bp.name, e.path))

    raw_root = root / "raw"
    dirs = {k: root / k for k in ("meshes", "collisions", "materials", "reflection", "bml", "shaders", "textures", "scenes", "physics", "upgrades", "xml", "other")}
    raw_root.mkdir(parents=True, exist_ok=True)
    for d in dirs.values(): d.mkdir(parents=True, exist_ok=True)
    manifest = []
    stats = {"archives": len(inputs), "resources": 0, "converted": 0, "failed": 0, "categories": {}, "outputs": {}}

    def output_for(path: str, digest: str) -> tuple[Path, str]:
        ext = Path(path).suffix.lower()
        if ext == ".meb": return dirs["meshes"] / f"{digest}.mgeo", "mgeo"
        if ext == ".csm": return dirs["collisions"] / f"{digest}.cmesh", "cmesh"
        if ext == ".bmt": return dirs["materials"] / f"{digest}.json", "json"
        if ext == ".bml": return dirs["bml"] / f"{digest}.json", "json"
        if ext in {".fx", ".fxh"}: return dirs["shaders"] / f"{digest}.json", "json"
        if ext == ".dds": return dirs["textures"] / f"{digest}.dds", "raw"
        if ext in {".vhf", ".sgb"}: return dirs["scenes"] / f"{digest}.json", "json"
        if ext in {".cgp", ".cdp", ".cdv", ".csd"}: return dirs["physics"] / f"{digest}.json", "json"
        if ext == ".vud": return dirs["upgrades"] / f"{digest}.json", "json"
        if ext in {".xml", ".lod", ".new", ".old", ".cpt", ".bas", ".bad", ".spe", ".enx", ".trd"}: return dirs["xml"] / f"{digest}.json", "json"
        return dirs["other"] / f"{digest}.bin", "raw"

    import shutil
    for bp in inputs:
        with BFF(bp) as bff:
            for e in bff.entries:
                ext = Path(e.path).suffix.lower()
                if ext not in wanted_exts:
                    continue
                stats["resources"] += 1
                try:
                    data = bff.extract_entry(e, type2="lzx")
                    digest = sha256(data)
                    raw_blob = raw_root / digest[:2] / digest[2:]
                    raw_blob.parent.mkdir(parents=True, exist_ok=True)
                    if not raw_blob.exists(): raw_blob.write_bytes(data)
                    analysis = _resource_analysis_output(data, e.path)
                    out_path, out_kind = output_for(e.path, digest)
                    if not out_path.exists():
                        if out_kind == "mgeo":
                            write_mgeo(read_meb(data), out_path)
                        elif out_kind == "cmesh":
                            write_cmesh(read_csm(data), out_path)
                        elif out_kind == "json":
                            out_path.write_text(json.dumps(analysis.get("analysis", {}), ensure_ascii=False, indent=2), encoding="utf-8")
                        else:
                            out_path.write_bytes(data)
                    refs = dependency_hints(data, e.path)
                    resolved = []
                    for ref in refs:
                        hits = resolve_resource_ref(ref, path_map, basename_map)
                        resolved.append({"ref": ref, "resolved": hits})
                    cat = classify(e.path, data)
                    row = {"archive": bp.name, "path": e.path, "sha256": digest, "size": len(data), "category": cat, "raw": str(raw_blob.relative_to(root)).replace(os.sep, "/"), "output": str(out_path.relative_to(root)).replace(os.sep, "/"), "output_kind": out_kind, "dependencies": resolved}
                    manifest.append(row); stats["converted"] += 1; stats["categories"][cat] = stats["categories"].get(cat, 0) + 1; stats["outputs"][out_kind] = stats["outputs"].get(out_kind, 0) + 1
                except Exception as exc:
                    stats["failed"] += 1
                    manifest.append({"archive": bp.name, "path": e.path, "error": f"{type(exc).__name__}: {exc}"})
                    if args.fail_fast: raise
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 1 if stats["failed"] else 0


def cmd_manifest(args: argparse.Namespace) -> int:
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    rows: list[dict] = []
    for bff_path in inputs:
        with BFF(bff_path) as bff:
            for e in bff.entries:
                row = asdict(e)
                if args.decode:
                    try:
                        decoded = bff.extract_entry(e, type2="lzx")
                        row["decode"] = "ok"
                        row["sha256"] = sha256(decoded)
                        row["detected_type"] = classify(e.path, decoded)
                        row["dependency_hints"] = dependency_hints(decoded, e.path)
                    except Exception as exc:
                        row["decode"] = f"error:{type(exc).__name__}:{exc}"
                        row["sha256"] = ""
                        row["detected_type"] = classify(e.path)
                        row["dependency_hints"] = []
                else:
                    payload = bff.raw_payload(e)
                    row["sha256_compressed"] = sha256(payload)
                    row["decode"] = "not_run"
                    row["detected_type"] = classify(e.path)
                    row["dependency_hints"] = []
                rows.append(row)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".csv":
        fields = list(rows[0].keys())
        # JSON values inside CSV remain valid JSON strings.
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in rows:
                r = dict(row)
                if isinstance(r.get("dependency_hints"), list):
                    r["dependency_hints"] = json.dumps(r["dependency_hints"], ensure_ascii=False)
                w.writerow(r)
    else:
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} entries -> {out}")
    return 0


def safe_rel(path: str) -> Path:
    # Do not permit source resource paths to escape output roots.
    parts = []
    for p in Path(path.replace("\\", "/")).parts:
        if p in ("", "."):
            continue
        if p == "..":
            parts.append("__up__")
        else:
            parts.append(p)
    return Path(*parts)


def cmd_extract(args: argparse.Namespace) -> int:
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = []
    ok = fail = 0
    for bff_path in inputs:
        with BFF(bff_path) as bff:
            for e in bff.entries:
                target = dest / bff_path.stem / safe_rel(e.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    data = bff.extract_entry(e, type2=args.type2)
                    target.write_bytes(data)
                    manifest.append({
                        **asdict(e),
                        "status": "ok",
                        "sha256": sha256(data),
                        "detected_type": classify(e.path, data),
                    })
                    ok += 1
                except Exception as exc:
                    manifest.append({**asdict(e), "status": f"error:{type(exc).__name__}:{exc}"})
                    fail += 1
                    if args.fail_fast:
                        raise
    (dest / "extraction_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"extracted: {ok}, failed: {fail}, output: {dest}")
    return 1 if fail else 0


def cmd_package(args: argparse.Namespace) -> int:
    """Create a platform-neutral content-addressed asset database."""
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    root = Path(args.output)
    blob_root = root / "blobs"
    blob_root.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    path_map: dict[str, list[dict]] = {}
    stats = {"archives": 0, "resources": 0, "decoded": 0, "failed": 0, "bytes": 0, "categories": {}}

    for bff_path in inputs:
        stats["archives"] += 1
        with BFF(bff_path) as bff:
            for e in bff.entries:
                stats["resources"] += 1
                try:
                    data = bff.extract_entry(e, type2="lzx")
                    digest = sha256(data)
                    blob = blob_root / digest[:2] / digest[2:]
                    blob.parent.mkdir(parents=True, exist_ok=True)
                    if not blob.exists():
                        blob.write_bytes(data)
                    cat = classify(e.path, data)
                    row = {
                        **asdict(e),
                        "sha256": digest,
                        "size": len(data),
                        "category": cat,
                        "blob": str(blob.relative_to(root)).replace(os.sep, "/"),
                        "dependency_hints": dependency_hints(data, e.path),
                    }
                    manifest.append(row)
                    path_map.setdefault(e.path, []).append({
                        "sha256": digest,
                        "archive": e.archive,
                        "blob": row["blob"],
                    })
                    stats["decoded"] += 1
                    stats["bytes"] += len(data)
                    stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
                except Exception as exc:
                    stats["failed"] += 1
                    manifest.append({**asdict(e), "error": f"{type(exc).__name__}: {exc}"})
                    if args.fail_fast:
                        raise

    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "path_map.json").write_text(json.dumps(path_map, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 1 if stats["failed"] else 0


def cmd_render_bindings(args: argparse.Namespace) -> int:
    """Build VHF/MEB/BMT/FXO render bindings from an existing Android IR."""
    from render_pipeline import build_render_bindings
    result = build_render_bindings(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    return 1 if result["stats"]["unresolved"] else 0


def cmd_bab_corpus(args: argparse.Namespace) -> int:
    """Build a BAB corpus report from resource_analysis.json."""
    from bab_corpus import build_bab_corpus_report

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = next(
            (
                payload[key]
                for key in ("resources", "rows", "analyses")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
        if records is None:
            raise ValueError("BAB corpus input must contain a resource list")
    else:
        raise ValueError("BAB corpus input must be a JSON list or resource container object")

    report = build_bab_corpus_report(records)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "sample_count": report["sample_count"],
        "skeleton_group_count": report["skeleton_group_count"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_bab_payload_diff(args: argparse.Namespace) -> int:
    """Compare two opaque BAB animation payloads byte-for-byte."""
    from bab_payload_diff import compare_bab_payload_bytes

    a = Path(args.first).read_bytes()
    b = Path(args.second).read_bytes()
    result = compare_bab_payload_bytes(a, b)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "size_delta": result["size_delta"],
        "overlap_equal_ratio": result["overlap_equal_ratio"],
        "equal_prefix_bytes": result["equal_prefix_bytes"],
        "equal_suffix_bytes": result["equal_suffix_bytes"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_bab_animation_runtime(args: argparse.Namespace) -> int:
    """Decode the recovered runtime animation bank from an extracted BAB file."""
    from bab_animation_runtime import parse_bab_animation_payload
    from bab_format import parse_bab

    data = Path(args.input).read_bytes()
    bab = parse_bab(data, preserve_tail=True)
    payload_offset = int(bab["animation_payload_offset"])
    report = parse_bab_animation_payload(
        data[payload_offset:],
        mode=args.mode,
        strict=not args.allow_partial,
    )
    report["source"] = {
        "input": str(args.input),
        "sha256": sha256(data),
        "animation_payload_offset": payload_offset,
        "animation_payload_size": len(data) - payload_offset,
        "bab_header_name": bab["header"].get("name"),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "mode": report["mode"],
        "consumed_bytes": report.get("consumed_bytes", 0),
        "trailing_bytes": report.get("trailing_bytes", 0),
        "blockers": report.get("blockers", []),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_sgb_runtime(args: argparse.Namespace) -> int:
    """Decode source-backed binary SGB chunk structures."""
    from sgb_runtime import parse_sgb_runtime

    data = Path(args.input).read_bytes()
    report = parse_sgb_runtime(data, strict=not args.allow_partial)
    report["source"] = {
        "input": str(args.input),
        "sha256": sha256(data),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "chunk_count": report["chunk_count"],
        "recognized_chunks": sum(
            bool(row.get("recognized_by_runtime")) for row in report["chunks"]
        ),
        "blockers": report["blockers"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2

def cmd_color_evidence_bff_corpus(args: argparse.Namespace) -> int:
    """Scan BFF archives for MEB COLOR0/COLOR1 streams and aggregate evidence."""
    from color_abi import aggregate_color_abi_evidence, build_color_abi_evidence

    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")

    reports: list[dict] = []
    resources: list[dict] = []
    errors: list[dict] = []

    for archive in inputs:
        with BFF(archive) as bff:
            for entry in bff.entries:
                if not entry.path.lower().endswith(".meb"):
                    continue
                try:
                    data = bff.extract_entry(entry, type2="lzx")
                    mesh = read_meb(data)
                    for property_id, stream_name, stream in (
                        ("460", "colors", mesh.colors),
                        ("461", "colors2", mesh.colors2),
                    ):
                        if not stream:
                            continue
                        raw = bytes(component for row in stream for component in row)
                        report = build_color_abi_evidence(property_id, raw)
                        report["source"] = {
                            "kind": "bff-meb-corpus",
                            "archive": archive.name,
                            "resource": entry.path,
                            "entry_index": entry.index,
                            "resource_sha256": sha256(data),
                            "stream": stream_name,
                            "vertex_count": mesh.vertex_count,
                        }
                        reports.append(report)
                        resources.append(report["source"])
                except Exception as exc:
                    errors.append({
                        "archive": archive.name,
                        "resource": entry.path,
                        "error": f"{type(exc).__name__}: {exc}",
                    })

    aggregate = aggregate_color_abi_evidence(reports)
    aggregate["source"] = {
        "kind": "bff-corpus",
        "archives": [archive.name for archive in inputs],
        "accepted_reports": len(reports),
        "resource_count": len(resources),
        "errors": errors,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": aggregate["format"],
        "archives": len(inputs),
        "accepted_reports": len(reports),
        "resource_count": len(resources),
        "errors": len(errors),
        "selection": aggregate["selection"],
        "properties": {
            key: value["report_count"]
            for key, value in aggregate["properties"].items()
        },
    }, ensure_ascii=False, indent=2))
    return 1 if errors and args.fail_on_error else 0



def cmd_color_evidence_corpus(args: argparse.Namespace) -> int:
    """Aggregate multiple SHIFT.ColorABIEvidence/1 JSON reports."""
    from color_abi import aggregate_color_abi_evidence

    files: list[Path] = []
    for raw in args.input:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.json")))
        elif path.is_file():
            files.append(path)
        else:
            raise SystemExit(f"evidence input not found: {path}")

    reports = []
    seen: set[Path] = set()
    for path in files:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"failed to read evidence JSON {path}: {exc}") from exc
        if payload.get("format") == "SHIFT.ColorABIEvidence/1":
            reports.append(payload)

    report = aggregate_color_abi_evidence(reports)
    report["source"] = {
        "inputs": [str(path) for path in files],
        "accepted_reports": len(reports),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "report_count": report["report_count"],
        "accepted_reports": len(reports),
        "properties": {
            key: value["report_count"]
            for key, value in report["properties"].items()
        },
        "selection": report["selection"],
    }, ensure_ascii=False, indent=2))
    return 0



def cmd_color_evidence_resource(args: argparse.Namespace) -> int:
    """Extract one MEB resource from a BFF and emit COLOR ABI evidence."""
    from color_abi import build_color_abi_evidence, compare_color_candidate

    with BFF(args.archive) as bff:
        needle = args.resource.lower().replace("\\", "/")
        matches = [
            entry
            for entry in bff.entries
            if entry.path.lower().replace("\\", "/") == needle
        ]
        if not matches:
            raise SystemExit(f"resource not found: {args.resource}")
        entry = matches[0]
        data = bff.extract_entry(entry, type2="lzx")

    if not entry.path.lower().endswith(".meb"):
        raise SystemExit(f"input is not a .meb resource: {entry.path}")

    mesh = read_meb(data)
    stream = mesh.colors if args.property_id == "460" else mesh.colors2
    if not stream:
        raise ValueError(
            f"MEB resource has no property {args.property_id} stream"
        )
    raw = bytes(component for row in stream for component in row)
    report = build_color_abi_evidence(args.property_id, raw)

    property_layout = next(
        (
            layout
            for layout in mesh.property_layouts
            if str(layout.get("id")) == args.property_id
        ),
        None,
    )
    property_descriptor = next(
        (
            descriptor
            for descriptor in getattr(mesh, "property_descriptors", [])
            if str(descriptor.get("id")) == args.property_id
        ),
        None,
    )
    raw_payload = b""
    payload_range = None
    descriptor_range = None
    if isinstance(property_layout, dict):
        payload_offset = property_layout.get("payload_offset")
        payload_bytes = property_layout.get("bytes")
        if isinstance(payload_offset, int) and isinstance(payload_bytes, int):
            payload_end = payload_offset + payload_bytes
            if 0 <= payload_offset <= payload_end <= len(data):
                raw_payload = data[payload_offset:payload_end]
                payload_range = {
                    "offset": payload_offset,
                    "length": payload_bytes,
                    "end": payload_end,
                }
    if isinstance(property_descriptor, dict):
        descriptor_offset = property_descriptor.get("offset")
        descriptor_hex = property_descriptor.get("raw_hex")
        if isinstance(descriptor_offset, int) and isinstance(descriptor_hex, str):
            descriptor_length = len(descriptor_hex) // 2
            descriptor_end = descriptor_offset + descriptor_length
            if (
                descriptor_length == 12
                and 0 <= descriptor_offset <= descriptor_end <= len(data)
                and data[descriptor_offset:descriptor_end].hex() == descriptor_hex
            ):
                descriptor_range = {
                    "offset": descriptor_offset,
                    "length": descriptor_length,
                    "end": descriptor_end,
                }

    report["source"] = {
        "kind": "bff-meb",
        "archive": bff.path.name,
        "resource": entry.path,
        "entry_index": entry.index,
        "resource_sha256": sha256(data),
        "stream": "colors" if args.property_id == "460" else "colors2",
        "vertex_count": mesh.vertex_count,
        "property_layout": property_layout,
        "property_descriptor": property_descriptor,
        "descriptor_range": descriptor_range,
        "descriptor_range_status": "observed" if descriptor_range else "not-proven",
        "payload_range": payload_range,
        "payload_range_status": "observed" if payload_range else "not-proven",
        "payload_raw_bytes_sha256": sha256(raw_payload) if raw_payload else None,
        "payload_raw_hex": raw_payload.hex() if raw_payload else None,
        "decoded_stream_matches_payload": raw_payload == raw,
        "decoded_stream_matches_payload_status": (
            "observed" if raw_payload and raw_payload == raw else "not-proven"
        ),
    }
    if args.expected_rgba:
        expected = Path(args.expected_rgba).read_bytes()
        report["comparison"] = compare_color_candidate(
            args.property_id,
            raw,
            expected,
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "property_id": report["property_id"],
        "sample_count": report["sample_count"],
        "confidence": report["confidence"],
        "archive": bff.path.name,
        "resource": entry.path,
        "selection": (report.get("comparison") or {}).get("selection", "not-selected"),
        "descriptor_range_status": report["source"].get("descriptor_range_status"),
        "payload_range_status": report["source"].get("payload_range_status"),
        "decoded_stream_matches_payload_status": report["source"].get(
            "decoded_stream_matches_payload_status"
        ),
    }, ensure_ascii=False, indent=2))
    return 0



def cmd_color_evidence(args: argparse.Namespace) -> int:
    """Build non-selecting COLOR0/COLOR1 ABI evidence from raw bytes or MEB JSON."""
    from color_abi import build_color_abi_evidence, compare_color_candidate

    source = "raw"
    if args.mesh_json:
        source = "meb-json"
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        field = "colors" if args.property_id == "460" else "colors2"
        rows = payload.get(field)
        if rows is None:
            raise ValueError(
                f"MEB JSON has no {field} stream for property {args.property_id}"
            )
        try:
            raw = bytes(
                component
                for row in rows
                for component in row
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"MEB JSON {field} stream is not a numeric 4-byte color array"
            ) from exc
    else:
        raw = Path(args.input).read_bytes()
    report = build_color_abi_evidence(args.property_id, raw)
    report["source"] = {
        "kind": source,
        "input": str(args.input),
    }
    if args.mesh_json:
        report["source"]["stream"] = field
        report["source"]["vertex_count"] = len(rows)
    if args.expected_rgba:
        expected = Path(args.expected_rgba).read_bytes()
        report["comparison"] = compare_color_candidate(
            args.property_id,
            raw,
            expected,
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "property_id": report["property_id"],
        "sample_count": report["sample_count"],
        "confidence": report["confidence"],
        "candidate_orders": [x["order"] for x in report["candidates"]],
        "selection": (report.get("comparison") or {}).get("selection", "not-selected"),
    }, ensure_ascii=False, indent=2))
    return 0



def cmd_meb_d3d9_descriptor_triple(args: argparse.Namespace) -> int:
    """Cross-check exact MEB 460/461 descriptor triples against recovered binary loader semantics."""
    from meb_d3d9_descriptor_triple_evidence import write_descriptor_triple_report

    resource_reports = [
        Path(path)
        for path in args.resource_report
    ]
    report = write_descriptor_triple_report(
        args.meb_report,
        args.source_report,
        args.output,
        resource_reports=resource_reports,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["d3d9_type_mapping"]["status"],
        "meb_property_mapping": report["meb_property_mapping"]["status"],
        "type_codes": report["d3d9_type_mapping"]["type_codes"],
        "usage_ordinals": report["d3d9_type_mapping"]["usage_ordinals"],
        "channels": report["d3d9_type_mapping"]["channels"],
        "selection": report["selection"],
        "verified_abi": report["verified_abi"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_source_evidence(args: argparse.Namespace) -> int:
    """Analyze recovered SHIFT.exe C source for explicit D3D9 vertex evidence."""
    from d3d9_source_evidence import analyze_shift_exe_c_file

    report = analyze_shift_exe_c_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "source_sha256": report["source"]["sha256"],
        "observed": sum(
            row["status"] == "observed"
            for row in report["observations"]
        ),
        "not_found": sum(
            row["status"] == "not-found"
            for row in report["observations"]
        ),
        "type_4_to_packed_color": report["linkage"]["type_4_to_packed_color"]["status"],
        "meb_460_461_to_type_4": report["linkage"]["meb_460_461_to_type_4"]["status"],
        "selection": report["selection"],
        "verified_abi": report["verified_abi"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_type_evidence(args: argparse.Namespace) -> int:
    """Analyze the recovered primitive-type switch for D3D9 semantics."""
    from d3d9_type_semantics import analyze_d3d9_type_semantics_file

    report = analyze_d3d9_type_semantics_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "function": report["function"],
        "enum_alignment": report["enum_alignment"]["status"],
        "observed_case_count": report["enum_alignment"].get("observed_case_count", 0),
        "missing_cases": report["enum_alignment"].get("missing_cases", []),
        "meb_property_mapping": report["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_table_evidence(args: argparse.Namespace) -> int:
    """Analyze recovered D3D9 lookup-table bounds and XML ordinal limits."""
    from d3d9_table_shape_evidence import analyze_d3d9_table_shapes

    source = Path(args.input).read_bytes()
    report = analyze_d3d9_table_shapes(source)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "type_table_slots_hint": report["indexing"]["type_table"]["layout_hint_dword_slots"],
        "size_table_slots_hint": report["indexing"]["size_table"]["layout_hint_dword_slots"],
        "xml_type_ordinal_exclusive_limit": report["xml_stream"]["type_ordinal_exclusive_limit"],
        "xml_status": report["xml_stream"]["status"],
        "initializer_status": report["conclusions"]["type_table_initializer_bytes"]["status"],
        "meb_460_461_mapping": report["conclusions"]["meb_460_461_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_usage_evidence(args: argparse.Namespace) -> int:
    """Analyze the recovered XML STREAM Usage table."""
    from d3d9_usage_evidence import analyze_d3d9_usage_semantics_file

    report = analyze_d3d9_usage_semantics_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "usage_exclusive_limit": report["switch"]["usage_exclusive_limit"],
        "usage_6_to_colour": report["semantic_links"]["usage_6_to_colour"]["status"],
        "usage_6_to_meb_colour_properties": report["semantic_links"]["usage_6_to_meb_colour_properties"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_memory_table_evidence(args: argparse.Namespace) -> int:
    """Decode D3D9 lookup-table bytes from a raw loaded-memory window."""
    from d3d9_memory_table_evidence import analyze_d3d9_memory_tables_file

    report = analyze_d3d9_memory_tables_file(
        args.input,
        int(args.base_address, 0),
        include_channel_layout_hint=args.include_channel_layout_hint,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "type_table_status": report["tables"]["type_code"]["status"],
        "type_name_pointer_count": len(report["type_name_pointers"]),
        "decoded_type_name_count": sum(
            item["status"] == "decoded" for item in report["type_name_pointers"]
        ),
        "meb_460_461_mapping": report["conclusions"]["meb_460_461_to_type_code"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_pe_evidence(args: argparse.Namespace) -> int:
    """Resolve recovered D3D9 virtual addresses in a PE image."""
    from d3d9_pe_evidence import analyze_d3d9_pe_image_file

    override = int(args.image_base, 0) if args.image_base else None
    report = analyze_d3d9_pe_image_file(
        args.input,
        image_base_override=override,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "image_base": report["image"]["image_base"],
        "machine": report["image"]["machine"],
        "type_table_file_backed": report["tables"]["type_code_table"]["file_backed"],
        "type_name_pointer_table_file_backed": report["tables"]["type_name_pointer_table"]["file_backed"],
        "decoded_type_name_count": sum(
            item["status"] == "decoded" for item in report["type_name_pointers"]
        ),
        "meb_460_461_mapping": report["conclusions"]["meb_460_461_to_type_code"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_stream_record_evidence(args: argparse.Namespace) -> int:
    """Analyze the recovered 8-byte XML STREAM declaration records."""
    from d3d9_stream_record_evidence import analyze_d3d9_stream_record_semantics_file

    report = analyze_d3d9_stream_record_semantics_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "record_stride": report["record"]["stride"],
        "d3dvertexelement9_shape": report["semantic_links"]["d3dvertexelement9_shape"]["status"],
        "type_field_offset": report["record"]["field_offsets"]["type"],
        "usage_field_offset": report["record"]["field_offsets"]["usage"],
        "usage_index_field_offset": report["record"]["field_offsets"]["usage_index"],
        "meb_property_mapping": report["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_canonicalizer_evidence(args: argparse.Namespace) -> int:
    """Analyze the recovered D3D9 declaration canonicalizer."""
    from d3d9_declaration_canonicalizer_evidence import (
        analyze_d3d9_declaration_canonicalizer_file,
    )

    report = analyze_d3d9_declaration_canonicalizer_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "record_stride": report["canonicalization"]["record_stride"],
        "full_record_identity": report["canonicalization"]["full_record_identity"],
        "d3dvertexelement9_shape": report["semantic_links"]["d3dvertexelement9_shape"]["status"],
        "meb_property_mapping": report["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_type_layout_evidence(args: argparse.Namespace) -> int:
    """Analyze D3D9 Type size/component-count table semantics."""
    from d3d9_type_layout_evidence import analyze_d3d9_type_layout_tables_file

    report = analyze_d3d9_type_layout_tables_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "type_domain_status": report["type_domain"]["status"],
        "type_size_status": report["semantics"]["type_code_to_byte_size"]["status"],
        "type_component_status": report["semantics"]["type_code_to_component_count"]["status"],
        "type3_size_entry": report["semantics"]["type3_size_entry"]["status"],
        "sentinel_type_code": report["type_domain"]["sentinel_type_code"],
        "meb_property_mapping": report["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_type_profile(args: argparse.Namespace) -> int:
    """Validate raw Type table values against the D3D9 semantic profile."""
    from d3d9_type_profile import validate_type_table_report

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = validate_type_table_report(report)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["validation"]["status"],
        "match_count": result["validation"]["match_count"],
        "mismatch_count": result["validation"]["mismatch_count"],
        "unavailable_count": result["validation"]["unavailable_count"],
        "meb_property_mapping": result["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_d3d9_stream_topology_evidence(args: argparse.Namespace) -> int:
    """Analyze Stream-group topology in FUN_00854e70."""
    from d3d9_stream_topology_evidence import analyze_d3d9_stream_topology_file

    report = analyze_d3d9_stream_topology_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "group_stride": report["grouping"].get("group_stride"),
        "stream_to_group": report["grouping"].get("stream_to_group_index"),
        "record_pointer_array": report["grouping"].get("record_pointer_array"),
        "byte_size_accumulation": report["grouping"].get("byte_size_accumulation"),
        "meb_property_mapping": report["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0



def cmd_d3d9_declaration_chain(args: argparse.Namespace) -> int:
    """Cross-check the recovered D3D9 declaration evidence chain."""
    from d3d9_declaration_chain_evidence import analyze_d3d9_declaration_chain_files

    result = analyze_d3d9_declaration_chain_files(
        args.type_profile,
        args.stream_topology,
        args.stream_record,
        args.canonicalizer,
        pe_evidence_path=args.pe_evidence,
        declaration_instance_path=args.declaration_instance,
        runtime_memory_evidence_path=args.runtime_memory_evidence,
        runtime_layout_evidence_path=args.runtime_layout_evidence,
        api_bind_evidence_path=args.api_bind_evidence,
        render_api_evidence_path=args.render_api_evidence,
        declaration_create_evidence_path=args.declaration_create_evidence,
        declaration_count_evidence_path=args.declaration_count_evidence,
        declaration_sentinel_evidence_path=args.declaration_sentinel_evidence,
        declaration_lifecycle_evidence_path=args.declaration_lifecycle_evidence,
        meb_color_bridge_evidence_path=args.meb_color_bridge_evidence,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "observed_checks": result["summary"]["observed_checks"],
        "required_checks": result["summary"]["required_checks"],
        "blocking_checks": result["summary"]["blocking_checks"],
        "meb_property_mapping": result["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_decode_d3d9_declaration(args: argparse.Namespace) -> int:
    """Decode raw 8-byte D3D9 declaration records from a memory dump."""
    from d3d9_declaration_instance import decode_d3d9_declaration_records_file

    result = decode_d3d9_declaration_records_file(
        args.input,
        count=args.count,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "decoded_records": result["payload"]["decoded_records"],
        "trailing_bytes": result["payload"]["trailing_bytes"],
        "terminator_indices": result["validation"]["terminator_indices"],
        "meb_property_mapping": result["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0

def cmd_capture_d3d9_memory_declaration(args: argparse.Namespace) -> int:
    """Capture an address/range-qualified D3D9 declaration from a memory dump."""
    from d3d9_memory_declaration_evidence import capture_d3d9_memory_declaration_file

    result = capture_d3d9_memory_declaration_file(
        args.input,
        base_address=args.base_address,
        offset=args.offset,
        length=args.length,
        count=args.count,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "slice_start_address": result["memory"]["slice_start_address"],
        "slice_length": result["memory"]["slice_length"],
        "declaration_array_records": result["extraction"]["declaration_array_records"],
        "end_sentinel_status": result["extraction"]["end_sentinel_status"],
        "meb_property_mapping": result["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_validate_d3d9_runtime_layout(args: argparse.Namespace) -> int:
    """Validate runtime declaration offsets against recovered Type sizes."""
    from d3d9_runtime_declaration_layout import validate_d3d9_runtime_declaration_layout_file

    result = validate_d3d9_runtime_declaration_layout_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "records_considered": result.get("declaration", {}).get("records_considered"),
        "streams": len(result.get("stream_summaries", [])),
        "issues": len(result.get("issues", [])),
        "meb_property_mapping": result["meb_property_mapping"]["status"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_bmw_reference_render(args: argparse.Namespace) -> int:
    """Render one ready BMW material slice through the desktop reference renderer."""
    from bmw_reference_render import render_files

    result = render_files(
        args.slice,
        args.mesh,
        args.output,
        width=args.width,
        height=args.height,
        shader_reference=args.shader_reference,
        texture_path=args.texture_json,
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "sha256": result["sha256"],
        "width": result["width"],
        "height": result["height"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_bmw_material_slice(args: argparse.Namespace) -> int:
    """Extract one exact BMW material draw from a BMW render slice."""
    from bmw_material_slice import validate_files

    report = validate_files(args.slice, primitive_index=args.primitive_index)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "primitive_index": report["primitive_index"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_bmw_render_slice(args: argparse.Namespace) -> int:
    """Extract one exact BMW M3 packet from a RenderBinding report."""
    from bmw_render_slice import validate_files

    report = validate_files(args.golden, args.render_binding)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "packet_index": report["packet_index"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_bmw_golden_gate(args: argparse.Namespace) -> int:
    """Validate the BMW M3 golden asset against a DrawPacket."""
    from bmw_golden_gate import validate_files

    report = validate_files(
        args.golden,
        args.draw_packet,
        material_binding_path=args.material_binding,
    )
    out = Path(args.output) if args.output else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_source_d3d9_shader_constant_bind(args: argparse.Namespace) -> int:
    """Analyze source-backed D3D9 float shader constant bind wrappers."""
    from d3d9_shader_constant_bind_evidence import analyze_d3d9_shader_constant_bind_file

    report = analyze_d3d9_shader_constant_bind_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "bindings": report["bindings"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "observed" else 2


def cmd_source_d3d9_shader_lifecycle(args: argparse.Namespace) -> int:
    """Analyze source-backed D3D9 shader bind lifecycle in SHIFT.exe.c."""
    from d3d9_shader_lifecycle_evidence import analyze_d3d9_shader_lifecycle_file

    report = analyze_d3d9_shader_lifecycle_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "function": report["function"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "observed" else 2


def cmd_validate_d3d9_capture(args: argparse.Namespace) -> int:
    """Validate a JSONL runtime capture against SHIFT.D3D9RuntimeCaptureSchema/1."""
    from d3d9_capture_schema import validate_capture_events

    events = []
    for line_no, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        events.append(row)
    report = validate_capture_events(events)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "event_count": report["event_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_d3d9_runtime_trace(args: argparse.Namespace) -> int:
    """Build runtime D3D9 binding evidence from an external JSONL capture."""
    from d3d9_runtime_trace import build_runtime_binding_evidence, load_events

    events = load_events(args.trace)
    meb = json.loads(Path(args.meb_resource).read_text(encoding="utf-8")) if args.meb_resource else None
    raw_map = json.loads(Path(args.usage_map).read_text(encoding="utf-8")) if args.usage_map else None
    usage_map = {int(k): int(v) for k, v in raw_map.items()} if isinstance(raw_map, dict) else None
    report = build_runtime_binding_evidence(
        events,
        meb_resource=meb,
        usage_ordinal_map=usage_map,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "events": report["trace"]["event_count"],
        "frames": report["trace"]["frame_count"],
        "declarations": report["trace"]["declaration_instance_count"],
        "specific_mesh_instance": report["evidence_boundary"]["specific_mesh_instance"],
        "same_instance_gate": report["same_instance_gate"]["status"],
    }, ensure_ascii=False, indent=2))
    if args.require_same_instance and not report["same_instance_gate"].get("ready"):
        return 2
    return 0

def cmd_bmw_runtime_render_contract(args: argparse.Namespace) -> int:
    """Build the exact BMW runtime render contract from shader selection and capture."""
    from bmw_runtime_render_contract import validate_files

    report = validate_files(
        args.material_input,
        args.runtime_report,
        primary_bff=args.primary_bff,
        render_bff=args.render_bff,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "reference_render_ready": report["reference_render_ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_bmw_runtime_shader_select(args: argparse.Namespace) -> int:
    """Select one exact static BMW FXO permutation from a runtime shader identity."""
    from bmw_runtime_shader_select import validate_files

    report = validate_files(
        args.material_input,
        args.runtime_report,
        require_same_resource=not args.allow_resource_mismatch,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "selected": report.get("selected"),
        "blocking_reasons": report.get("blocking_reasons", []),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_bmw_runtime_shader_join(args: argparse.Namespace) -> int:
    """Join an exact BMW material slice with captured D3D9 runtime shader state."""
    from bmw_runtime_shader_join import validate_files

    report = validate_files(args.material_slice, args.runtime_report)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "matched_frame_count": report["matched_frame_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_vertex_input_parity(args: argparse.Namespace) -> int:
    """Validate BMW shader semantic inputs against a captured D3D9 declaration."""
    from bmw_vertex_input_parity import validate_bmw_vertex_input_parity

    material = json.loads(Path(args.material_slice).read_text(encoding="utf-8"))
    runtime = json.loads(Path(args.runtime_report).read_text(encoding="utf-8"))
    usage_raw = json.loads(Path(args.usage_map).read_text(encoding="utf-8"))
    usage_map = {int(k): int(v) for k, v in usage_raw.items()}
    report = validate_bmw_vertex_input_parity(material, runtime, usage_map=usage_map)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_runtime_draw_correlation(args: argparse.Namespace) -> int:
    """Correlate one exact BMW primitive with a captured indexed draw."""
    from bmw_runtime_draw_correlation import correlate_runtime_draw

    material = json.loads(Path(args.material_slice).read_text(encoding="utf-8"))
    runtime = json.loads(Path(args.runtime_report).read_text(encoding="utf-8"))
    report = correlate_runtime_draw(material, runtime)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "primitive_index": report["primitive_index"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_material_slice_golden_gate(args: argparse.Namespace) -> int:
    """Validate one BMWMaterialSlice/1 against the exact M3 golden manifest."""
    from bmw_material_slice_golden_gate import validate_bmw_material_slice_golden

    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    slice_data = json.loads(Path(args.slice).read_text(encoding="utf-8"))
    report = validate_bmw_material_slice_golden(
        golden,
        slice_data,
        primitive_index=args.primitive_index,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "primitive_index": report["primitive_index"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_real_material_slice(args: argparse.Namespace) -> int:
    """Build a real renderer-compatible BMWMaterialSlice/1 from retail BFF data."""
    from bmw_real_material_slice import build_real_bmw_material_slice

    report = build_real_bmw_material_slice(
        args.input,
        args.golden,
        primitive_index=args.primitive_index,
        supplemental_bffs=args.supplemental_bff or [],
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "primitive_index": report["primitive_index"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_bff_intake(args: argparse.Namespace) -> int:
    """Verify the exact retail BMW M3 BFF intake before material extraction."""
    from bmw_bff_intake import validate_bmw_bff

    report = validate_bmw_bff(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_material_from_bff(args: argparse.Namespace) -> int:
    """Build a real BMW M3 MaterialBinding directly from retail BFF archives."""
    from bmw_material_from_bff import build_real_bmw_material_binding

    report = build_real_bmw_material_binding(
        args.input,
        supplemental_bffs=args.supplemental_bff or [],
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
        "fxo_candidate_count": report["provenance"]["fxo_candidate_count"],
        "dds_path_count": report["provenance"]["dds_path_count"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_meb_evidence_parity(args: argparse.Namespace) -> int:
    """Compare the exact BMW M3 MEB evidence snapshot with the golden manifest."""
    from bmw_m3_meb_evidence_parity import validate_bmw_meb_evidence

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    report = validate_bmw_meb_evidence(evidence, golden)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_source_bmw_vehicle_identity(args: argparse.Namespace) -> int:
    """Verify the source-level BMW M3 vehicle selector in SHIFT.exe.c."""
    from source_vehicle_identity import validate_source_vehicle_file

    report = validate_source_vehicle_file(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "selector_case": report["selector_case"],
        "selector_line": report["selector_line"],
        "selector_value": report["selector_value"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_paint_asset_contract(args: argparse.Namespace) -> int:
    """Validate the exact BMW M3 golden MEB -> paint material relationship."""
    from bmw_m3_paint_asset_contract import validate_bmw_paint_asset

    golden = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = validate_bmw_paint_asset(golden)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_paint_contract(args: argparse.Namespace) -> int:
    """Validate an evidence-backed BMW M3 paint material binding."""
    from bmw_m3_paint_contract import validate_material_binding

    binding = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = validate_material_binding(binding)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_render_command_constant_parity(args: argparse.Namespace) -> int:
    """Validate MaterialConstantPayload/uniform ranges against RenderCommand constants."""
    from render_command_constant_parity import validate_render_command_constant_parity

    command = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = validate_render_command_constant_parity(command)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_meb_runtime_usage_bridge(args: argparse.Namespace) -> int:
    """Build an evidence-backed MEB Usage-ordinal -> D3D9 Usage-byte bridge."""
    from meb_runtime_usage_bridge import build_usage_ordinal_bridge

    material = json.loads(Path(args.material_slice).read_text(encoding="utf-8"))
    runtime = json.loads(Path(args.runtime_report).read_text(encoding="utf-8"))
    report = build_usage_ordinal_bridge(material, runtime)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "usage_map": report["usage_map"],
        "blocking": report.get("conflicts") or report.get("unmapped_usage_ordinals") or [],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def cmd_bmw_runtime_golden_gate(args: argparse.Namespace) -> int:
    """Gate BMW golden rendering on complete runtime parity."""
    from bmw_runtime_golden_gate import validate_runtime_golden_gate

    report = validate_runtime_golden_gate(
        args.material_slice,
        args.runtime_report,
        usage_map_path=args.usage_map,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_bmw_runtime_parity(args: argparse.Namespace) -> int:
    """Validate BMW runtime shader, constant and declaration parity."""
    from bmw_runtime_parity import validate_files

    report = validate_files(
        args.material_slice,
        args.runtime_report,
        usage_map_path=args.usage_map,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2



def _write_evidence_report(report: dict, output: str | Path) -> int:
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "format": report.get("format"),
        "status": report.get("status"),
        "ready": report.get("ready"),
        "blocking_reasons": report.get("blocking_reasons", []),
    }, ensure_ascii=False, indent=2))
    return 0 if report.get("status") in ("observed", "match") or report.get("ready") is True else 2


def cmd_d3d9_declaration_lifecycle(args: argparse.Namespace) -> int:
    from d3d9_declaration_lifecycle_evidence import analyze_d3d9_declaration_lifecycle_file
    return _write_evidence_report(analyze_d3d9_declaration_lifecycle_file(args.input), args.output)


def cmd_d3d9_declaration_sentinel_evidence(args: argparse.Namespace) -> int:
    from d3d9_declaration_sentinel_evidence import analyze_d3d9_declaration_sentinel_file
    return _write_evidence_report(analyze_d3d9_declaration_sentinel_file(args.input), args.output)


def cmd_d3d9_declaration_count_evidence(args: argparse.Namespace) -> int:
    from d3d9_declaration_count_evidence import analyze_d3d9_declaration_count_file
    return _write_evidence_report(analyze_d3d9_declaration_count_file(args.input), args.output)


def cmd_d3d9_declaration_create_evidence(args: argparse.Namespace) -> int:
    from d3d9_declaration_create_evidence import analyze_d3d9_declaration_create_file
    return _write_evidence_report(analyze_d3d9_declaration_create_file(args.input), args.output)


def cmd_d3d9_render_api_boundary(args: argparse.Namespace) -> int:
    from d3d9_render_api_boundary import analyze_d3d9_render_api_boundary_file
    return _write_evidence_report(analyze_d3d9_render_api_boundary_file(args.input), args.output)


def cmd_d3d9_api_bind_evidence(args: argparse.Namespace) -> int:
    from d3d9_api_bind_evidence import analyze_d3d9_api_bind_file
    return _write_evidence_report(analyze_d3d9_api_bind_file(args.input), args.output)
def cmd_bmw_runtime_shader_render(args: argparse.Namespace) -> int:
    """Execute one exact captured BMW VS/PS permutation through the reference rasterizer."""
    from bmw_runtime_shader_render import render_runtime_shader

    result = render_runtime_shader(
        args.contract,
        args.material_input,
        args.mesh_json,
        args.primary_bff,
        args.output,
        external_resources=args.external_resource or [],
        width=args.width,
        height=args.height,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_bmw_runtime_capture_pipeline(args: argparse.Namespace) -> int:
    """Run the complete BMW capture -> runtime evidence -> shader -> render contract pipeline."""
    from bmw_runtime_capture_pipeline import build_pipeline

    report = build_pipeline(
        args.primary_bff,
        args.render_bff,
        args.capture_jsonl,
        cockpit_bff=args.cockpit_bff,
        meb_evidence=args.meb_evidence,
        usage_map=args.usage_map,
        require_same_instance=args.require_same_instance,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "material_ready": report["material_binding"].get("ready"),
        "runtime_status": report["runtime_evidence"].get("status"),
        "shader_selection_status": report["shader_selection"].get("status"),
        "reference_render_ready": report["runtime_render_contract"].get("reference_render_ready"),
        "texture_snapshot_count": report["texture_snapshots"]["converted_snapshot_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_render_bff_evidence(args: argparse.Namespace) -> int:
    """Build evidence for BMW M3 BMT/MEB plus the split RENDER.bff shader corpus."""
    from render_bff_evidence import build_evidence

    report = build_evidence(
        args.primary,
        args.render_bff,
        supplemental_bffs=args.supplemental_bff or [],
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "bmt": report["targets"]["bmt"]["path"],
        "meb_vertex_count": report["targets"]["meb"]["vertex_count"],
        "meb_triangle_count": report["targets"]["meb"]["triangle_count"],
        "render_fxo_count": report["render_archive"]["fxo_count"],
        "bodywork_fxo_count": report["render_archive"]["bodywork"]["bodywork_fxo_count"],
        "full_paint_sampler_program_count": report["render_archive"]["bodywork"]["full_paint_sampler_program_count"],
        "shader_selection_status": report["shader_probe"].get("status"),
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    inputs = list(iter_bffs(Path(args.input)))
    if not inputs:
        raise SystemExit("no .bff archives found")
    total = ok = failed = 0
    failures = []
    for bff_path in inputs:
        with BFF(bff_path) as bff:
            for e in bff.entries:
                total += 1
                try:
                    data = bff.extract_entry(e, type2="lzx")
                    if len(data) != e.uncompressed_size:
                        raise ValueError("size mismatch")
                    # Do not assume the mysterious BFF CRC field is CRC32 of
                    # decompressed data; SHIFT's record field is intentionally
                    # recorded but not validated here.
                    ok += 1
                except Exception as exc:
                    failed += 1
                    failures.append({"archive": bff_path.name, "path": e.path, "error": str(exc)})
                    if args.fail_fast:
                        break
        print(f"{bff_path.name}: done")
    report = {"total": total, "ok": ok, "failed": failed, "failures": failures[:args.max_failures]}
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0



def _shader_family(path: str) -> str:
    stem = Path(path).stem.lower()
    stem = re.sub(r"_[0-9a-f]{8,}$", "", stem)
    for prefix in ("render_shaders_", "effects_particles_shaders_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
            break
    return re.sub(r"[^a-z0-9]", "", stem)

def cmd_analyze_shaders(args: argparse.Namespace) -> int:
    from collections import Counter
    inp = Path(args.input)
    bffs = list(iter_bffs(inp))
    rows=[]
    for bp in bffs:
        with BFF(bp) as bff:
            sources = {}
            for e in bff.entries:
                if e.path.lower().endswith('.fx'):
                    try: sources[e.path] = parse_fx_source(bff.extract_entry(e, type2='lzx'))
                    except Exception: pass
            source_by_stem = {Path(k).stem.lower(): (k,v) for k,v in sources.items()}
            for e in bff.entries:
                if not e.path.lower().endswith('.fxo'): continue
                try:
                    data=bff.extract_entry(e, type2='lzx')
                    blobs=parse_shader_blobs(data)
                    fam=_shader_family(e.path)
                    match=source_by_stem.get(fam)
                    if not match:
                        candidates=[(k,v) for k,v in sources.items() if re.sub(r'[^a-z0-9]','',Path(k).stem.lower()) in fam]
                        match=candidates[0] if len(candidates)==1 else None
                    rows.append({
                        'archive':bp.name,'path':e.path,'bytes':len(data),'family':fam,
                        'source':match[0] if match else None,
                        'source_techniques':match[1]['techniques'] if match else [],
                        'source_includes':match[1]['includes'] if match else [],
                        'source_parameters':len(match[1]['parameters']) if match else 0,
                        'blobs':[asdict(x) for x in blobs],
                    })
                except Exception as exc:
                    rows.append({'archive':bp.name,'path':e.path,'error':f'{type(exc).__name__}: {exc}'})
    summary={
        'fxo':len(rows),
        'decoded_ok':sum('error' not in r for r in rows),
        'errors':sum('error' in r for r in rows),
        'blobs':sum(len(r.get('blobs',[])) for r in rows),
        'stages':dict(Counter(b['stage'] for r in rows for b in r.get('blobs',[]))),
        'source_linked':sum(bool(r.get('source')) for r in rows),
        'unique_sources':len({r['source'] for r in rows if r.get('source')}),
    }
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'summary':summary,'shaders':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 1 if summary['errors'] else 0


def cmd_analyze_shader_asm(args: argparse.Namespace) -> int:
    from collections import Counter
    inp = Path(args.input)
    bffs = list(iter_bffs(inp))
    rows=[]
    opcode_counts=Counter(); stage_counts=Counter(); errors=[]
    total_blobs=0; total_instructions=0
    for bp in bffs:
        with BFF(bp) as bff:
            for e in bff.entries:
                if not e.path.lower().endswith('.fxo'):
                    continue
                try:
                    data=bff.extract_entry(e,type2='lzx')
                    blobs=parse_shader_blobs(data)
                    for b in blobs:
                        p=parse_program(data,b.offset,b.end,b.stage,b.major,b.minor)
                        total_blobs += 1
                        total_instructions += len(p.instructions)
                        stage_counts[p.stage]+=1
                        opcode_counts.update(i.name for i in p.instructions)
                        rows.append({
                            'archive':bp.name,'path':e.path,'offset':b.offset,'end':b.end,
                            'stage':p.stage,'version':f'{p.major}_{p.minor}',
                            'instructions':len(p.instructions),
                            'inputs':p.inputs,'outputs':p.outputs,
                            'samplers':p.samplers,'constants':p.constants,'temps':p.temps,
                            'unsupported_opcodes':p.unsupported_opcodes,
                            'instruction_names':[i.name for i in p.instructions],
                        })
                except Exception as exc:
                    errors.append({'archive':bp.name,'path':e.path,'error':f'{type(exc).__name__}: {exc}'})
    summary={
        'fxo_programs':total_blobs,'instructions':total_instructions,
        'stages':dict(stage_counts),'errors':len(errors),
        'unique_opcodes':len(opcode_counts),
        'opcodes':[{'name':n,'count':c} for n,c in opcode_counts.most_common()],
        'programs_with_unknown_opcodes':sum(bool(r['unsupported_opcodes']) for r in rows),
    }
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'summary':summary,'programs':rows,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 1 if errors else 0


def cmd_translate_shader(args: argparse.Namespace) -> int:
    inp=Path(args.input)
    with BFF(inp) as bff:
        matches=[e for e in bff.entries if e.path==args.resource]
        if not matches: raise SystemExit(f'resource not found: {args.resource}')
        data=bff.extract_entry(matches[0],type2='lzx')
    blobs=parse_shader_blobs(data)
    if args.index<0 or args.index>=len(blobs): raise SystemExit(f'blob index out of range: 0..{len(blobs)-1}')
    b=blobs[args.index]
    p=parse_program(data,b.offset,b.end,b.stage,b.major,b.minor)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    if args.format=='json':
        out.write_text(json.dumps(asdict(p),ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        out.write_text(to_glsl(p),encoding='utf-8')
    print(json.dumps({'resource':args.resource,'blob_index':args.index,'stage':p.stage,'version':f'{p.major}_{p.minor}','instructions':len(p.instructions),'output':str(out)},ensure_ascii=False,indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="SHIFT universal BFF/resource importer")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("inspect", help="inspect one BFF")
    p.add_argument("file")
    p.add_argument("--samples", type=int, default=12)
    p.set_defaults(fn=cmd_inspect)

    p = sp.add_parser("analyze-resource", help="decode one resource and produce typed format analysis")
    p.add_argument("archive", help="BFF archive")
    p.add_argument("resource", help="logical resource path inside BFF")
    p.add_argument("--output")
    p.set_defaults(fn=cmd_analyze_resource)

    p = sp.add_parser("analyze-shader-asm", help="decode D3D9 FXO instruction operands into neutral ShaderIR")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output", help="ShaderIR report JSON")
    p.set_defaults(fn=cmd_analyze_shader_asm)

    p = sp.add_parser("translate-shader", help="translate one FXO blob to JSON ShaderIR or first-pass GLSL ES 3.1")
    p.add_argument("input", help="BFF archive")
    p.add_argument("resource", help="logical .fxo resource path")
    p.add_argument("output")
    p.add_argument("--index", type=int, default=0, help="shader blob index inside FXO")
    p.add_argument("--format", choices=["json","glsl"], default="json")
    p.set_defaults(fn=cmd_translate_shader)

    p = sp.add_parser("analyze-shaders", help="analyze compiled FXO shaders and link them to FX source")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output", help="shader report JSON")
    p.set_defaults(fn=cmd_analyze_shaders)

    p = sp.add_parser("analyze-dir", help="analyze resources by extension across BFF archives")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output")
    p.add_argument("--ext", nargs="+", default=[".xml", ".bml", ".dds", ".fx", ".fxh", ".meb", ".bmt", ".cgp", ".cdp", ".cdv", ".csd", ".vud"], help="extensions to analyze")
    p.add_argument("--max-per-archive", type=int, default=0)
    p.set_defaults(fn=cmd_analyze_dir)

    p = sp.add_parser("convert-meb", help="convert one MEB mesh to Android-neutral MGEO or JSON")
    p.add_argument("input", help=".meb file or BFF archive")
    p.add_argument("output", help="output .mgeo or .json")
    p.add_argument("--resource", help="logical .meb path inside the BFF archive")
    p.add_argument("--format", choices=["mgeo", "json"], default="mgeo")
    p.set_defaults(fn=cmd_convert_meb)

    p = sp.add_parser("convert-csm", help="convert one CSM collision mesh to Android-neutral CMES or JSON")
    p.add_argument("input", help=".csm file or BFF archive")
    p.add_argument("output", help="output .cmesh or .json")
    p.add_argument("--resource", help="logical .csm path inside the BFF archive")
    p.add_argument("--format", choices=["cmesh", "json"], default="cmesh")
    p.set_defaults(fn=cmd_convert_csm)

    p = sp.add_parser("graph", help="build a cross-BFF dependency graph")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output", help="graph JSON output")
    p.add_argument("--ext", nargs="+", default=[".cpt", ".vhf", ".meb", ".bmt", ".bml", ".dds", ".fx", ".fxh", ".fxo", ".xml", ".csm"], help="resource extensions to decode")
    p.add_argument("--fail-on-unresolved", action="store_true")
    p.set_defaults(fn=cmd_graph)

    p = sp.add_parser("build-ir", help="build Android-oriented intermediate representation")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output", help="IR output directory")
    p.add_argument("--ext", nargs="+", default=[".cpt", ".vhf", ".meb", ".csm", ".bmt", ".bml", ".dds", ".fx", ".fxh", ".fxo", ".xml", ".lod", ".new", ".old", ".vud", ".cgp", ".cdp", ".cdv", ".csd", ".bab", ".bas", ".bad", ".spe", ".enx", ".trd", ".sgb"], help="resource extensions to convert")
    p.add_argument("--fail-fast", action="store_true")
    p.set_defaults(fn=cmd_build_ir)

    p = sp.add_parser("manifest", help="build resource manifest")
    p.add_argument("input", help="BFF file or directory containing BFFs")
    p.add_argument("output")
    p.add_argument("--decode", action="store_true", help="decode all resources and hash/classify decoded bytes")
    p.set_defaults(fn=cmd_manifest)

    p = sp.add_parser("extract", help="extract BFF resources")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output")
    p.add_argument("--type2", choices=["lzx", "raw"], default="lzx")
    p.add_argument("--fail-fast", action="store_true")
    p.set_defaults(fn=cmd_extract)

    p = sp.add_parser("package", help="build content-addressed platform-neutral asset database")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output")
    p.add_argument("--fail-fast", action="store_true")
    p.set_defaults(fn=cmd_package)

    p = sp.add_parser("render-bindings", help="build VHF -> MEB -> BMT -> FXO render bindings from Android IR")
    p.add_argument("input", help="IR output directory produced by build-ir")
    p.add_argument("output", help="SHIFT.RenderBinding/1 JSON output")
    p.set_defaults(fn=cmd_render_bindings)

    p = sp.add_parser("bab-payload-diff", help="compare two opaque BAB animation payload files without assigning semantics")
    p.add_argument("first", help="first extracted .bab file")
    p.add_argument("second", help="second extracted .bab file")
    p.add_argument("output", help="SHIFT.BABPayloadByteComparison/1 JSON output")
    p.set_defaults(fn=cmd_bab_payload_diff)

    p = sp.add_parser("bab-animation-runtime", help="decode the recovered BAB runtime animation bank from an extracted .bab")
    p.add_argument("input", help="extracted .bab file")
    p.add_argument("output", help="SHIFT.BABAnimationRuntime/1 JSON output")
    p.add_argument("--mode", type=int, choices=[0, 1, 2], required=True, help="runtime animation-bank variant recovered from SHIFT.exe.c")
    p.add_argument("--allow-partial", action="store_true", help="return a blocker instead of raising on truncated payload")
    p.set_defaults(fn=cmd_bab_animation_runtime)

    p = sp.add_parser("sgb-runtime", help="decode source-backed binary SGB scene chunks")
    p.add_argument("input", help="extracted .sgb file")
    p.add_argument("output", help="SHIFT.SGBRuntime/1 JSON output")
    p.add_argument("--allow-partial", action="store_true", help="return blockers instead of raising on malformed chunk records")
    p.set_defaults(fn=cmd_sgb_runtime)    p = sp.add_parser("color-evidence-bff-corpus", help="scan BFF archives for MEB COLOR0/COLOR1 evidence and aggregate it")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("output", help="SHIFT.ColorABICorpusEvidence/1 JSON output")
    p.add_argument(
        "--fail-on-error",
        action="store_true",
        help="return non-zero when any MEB resource fails to decode",
    )
    p.set_defaults(fn=cmd_color_evidence_bff_corpus)

    p = sp.add_parser("color-evidence-corpus", help="aggregate multiple COLOR ABI evidence JSON reports without selecting an ABI")
    p.add_argument("input", nargs="+", help="evidence JSON file(s) or directories")
    p.add_argument("output", help="SHIFT.ColorABICorpusEvidence/1 JSON output")
    p.set_defaults(fn=cmd_color_evidence_corpus)

    p = sp.add_parser("color-evidence-resource", help="extract a MEB from BFF and report COLOR0/COLOR1 candidates")
    p.add_argument("archive", help="BFF archive")
    p.add_argument("resource", help="logical .meb resource path")
    p.add_argument("property_id", choices=["460", "461"])
    p.add_argument("output", help="SHIFT.ColorABIEvidence/1 JSON output")
    p.add_argument(
        "--expected-rgba",
        help="optional raw RGBA8 stream used only for comparison; no candidate is auto-selected",
    )
    p.set_defaults(fn=cmd_color_evidence_resource)

    p = sp.add_parser("color-evidence", help="report unresolved COLOR0/COLOR1 channel-order candidates")
    p.add_argument("property_id", choices=["460", "461"])
    p.add_argument("input", help="raw packed 4-byte color stream")
    p.add_argument("output", help="SHIFT.ColorABIEvidence/1 JSON output")
    p.add_argument(
        "--mesh-json",
        action="store_true",
        help="interpret input as MEB mesh_to_jsonable/1 JSON and read colors/colors2",
    )
    p.add_argument(
        "--expected-rgba",
        help="optional raw RGBA8 stream used only for candidate comparison; no candidate is auto-selected",
    )
    p.set_defaults(fn=cmd_color_evidence)

    p = sp.add_parser("meb-d3d9-descriptor-triple", help="prove MEB 460/461 descriptor triples against the recovered binary mesh loader")
    p.add_argument("meb_report", help="SHIFT.MEB JSON report with property_descriptors")
    p.add_argument("source_report", help="SHIFT.D3D9SourceVertexEvidence/1 JSON report")
    p.add_argument("output", help="SHIFT.MEBD3D9DescriptorTripleEvidence/1 JSON output")
    p.add_argument(
        "--resource-report",
        action="append",
        default=[],
        help="optional real BFF-backed SHIFT.ColorABIEvidence/1 report; repeat for 460 and 461",
    )
    p.set_defaults(fn=cmd_meb_d3d9_descriptor_triple)

    p = sp.add_parser("source-d3d9-evidence", help="analyze SHIFT.exe.c for explicit D3D9 vertex/color evidence")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9SourceVertexEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_source_evidence)

    p = sp.add_parser("source-d3d9-declaration-lifecycle", help="analyze the recovered D3D9 declaration creation/bind call chain")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9DeclarationLifecycleEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_declaration_lifecycle)

    p = sp.add_parser("source-d3d9-declaration-sentinel-evidence", help="analyze exact D3DDECL_END sentinel production in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9DeclarationSentinelEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_declaration_sentinel_evidence)

    p = sp.add_parser("source-d3d9-declaration-count-evidence", help="analyze declaration count/sentinel boundary in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9DeclarationCountEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_declaration_count_evidence)

    p = sp.add_parser("source-d3d9-declaration-create-evidence", help="analyze D3D9 vertex declaration creation in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9DeclarationCreateEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_declaration_create_evidence)

    p = sp.add_parser("source-d3d9-render-api-boundary", help="analyze declaration/stream/index/draw D3D9 API boundaries in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9RenderApiBoundaryEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_render_api_boundary)

    p = sp.add_parser("source-d3d9-api-bind-evidence", help="analyze the D3D9 declaration bind API boundary in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9ApiBindEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_api_bind_evidence)

    p = sp.add_parser("source-d3d9-type-evidence", help="analyze the D3D9 primitive type switch in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9TypeSemanticsEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_type_evidence)

    p = sp.add_parser("source-d3d9-table-evidence", help="analyze D3D9 lookup-table bounds in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9TypeTableShapeEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_table_evidence)

    p = sp.add_parser("source-d3d9-usage-evidence", help="analyze XML STREAM Usage semantics in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9UsageSemanticsEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_usage_evidence)

    p = sp.add_parser("source-d3d9-memory-evidence", help="decode D3D9 tables from a raw memory dump")
    p.add_argument("input", help="raw loaded-memory window")
    p.add_argument("base_address", help="virtual address of the first dump byte, e.g. 0xB90000")
    p.add_argument("output", help="SHIFT.D3D9MemoryTableEvidence/1 JSON output")
    p.add_argument("--include-channel-layout-hint", action="store_true")
    p.set_defaults(fn=cmd_d3d9_memory_table_evidence)

    p = sp.add_parser("source-d3d9-pe-evidence", help="resolve D3D9 table addresses in a PE image")
    p.add_argument("input", help="SHIFT.exe or another PE image")
    p.add_argument("output", help="SHIFT.PEImageEvidence/1 JSON output")
    p.add_argument("--image-base", help="override PE image base, e.g. 0x400000")
    p.set_defaults(fn=cmd_d3d9_pe_evidence)

    p = sp.add_parser("source-d3d9-stream-record-evidence", help="analyze 8-byte XML STREAM declaration records in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9StreamRecordEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_stream_record_evidence)

    p = sp.add_parser("source-d3d9-canonicalizer-evidence", help="analyze FUN_00830f80 declaration canonicalization in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9DeclarationCanonicalizerEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_canonicalizer_evidence)

    p = sp.add_parser("source-d3d9-type-layout-evidence", help="analyze Type->size/component-count tables in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9TypeLayoutTableEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_type_layout_evidence)

    p = sp.add_parser("validate-d3d9-type-profile", help="validate a D3D9 memory-table evidence report against the Type profile")
    p.add_argument("input", help="SHIFT.D3D9MemoryTableEvidence/1 JSON input")
    p.add_argument("output", help="SHIFT.D3D9TypeProfile/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_type_profile)

    p = sp.add_parser("source-d3d9-stream-topology-evidence", help="analyze Stream grouping topology in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9StreamTopologyEvidence/1 JSON output")
    p.set_defaults(fn=cmd_d3d9_stream_topology_evidence)

    p = sp.add_parser("validate-d3d9-declaration-chain", help="cross-check the recovered D3D9 declaration evidence chain")
    p.add_argument("type_profile", help="SHIFT.D3D9TypeProfile/1 JSON input")
    p.add_argument("stream_topology", help="SHIFT.D3D9StreamTopologyEvidence/1 JSON input")
    p.add_argument("stream_record", help="SHIFT.D3D9StreamRecordEvidence/1 JSON input")
    p.add_argument("canonicalizer", help="SHIFT.D3D9DeclarationCanonicalizerEvidence/1 JSON input")
    p.add_argument("output", help="SHIFT.D3D9DeclarationChainEvidence/1 JSON output")
    p.add_argument("--pe-evidence", help="optional SHIFT.PEImageEvidence/1 JSON input")
    p.add_argument("--declaration-instance", help="optional SHIFT.D3D9DeclarationInstanceEvidence/1 JSON input")
    p.add_argument("--runtime-memory-evidence", help="optional SHIFT.D3D9MemoryDeclarationEvidence/1 JSON input")
    p.add_argument("--runtime-layout-evidence", help="optional SHIFT.D3D9RuntimeDeclarationLayoutEvidence/1 JSON input")
    p.add_argument("--api-bind-evidence", help="optional SHIFT.D3D9ApiBindEvidence/1 JSON input")
    p.add_argument("--render-api-evidence", help="optional SHIFT.D3D9RenderApiBoundaryEvidence/1 JSON input")
    p.add_argument("--declaration-create-evidence", help="optional SHIFT.D3D9DeclarationCreateEvidence/1 JSON input")
    p.add_argument("--declaration-count-evidence", help="optional SHIFT.D3D9DeclarationCountEvidence/1 JSON input")
    p.add_argument("--declaration-sentinel-evidence", help="optional SHIFT.D3D9DeclarationSentinelEvidence/1 JSON input")
    p.add_argument("--declaration-lifecycle-evidence", help="optional SHIFT.D3D9DeclarationLifecycleEvidence/1 JSON input")
    p.add_argument("--meb-color-bridge-evidence", help="optional SHIFT.MEBD3D9ColorBridgeEvidence/1 JSON input")
    p.set_defaults(fn=cmd_d3d9_declaration_chain)


    p = sp.add_parser("capture-d3d9-memory-declaration", help="capture a D3D9 declaration array from a virtual-addressed memory dump")
    p.add_argument("input", help="raw loaded-memory dump")
    p.add_argument("base_address", type=lambda value: int(value, 0), help="virtual address of the first dump byte, e.g. 0x12340000")
    p.add_argument("output", help="SHIFT.D3D9MemoryDeclarationEvidence/1 JSON output")
    p.add_argument("--offset", type=lambda value: int(value, 0), default=0, help="byte offset within the input dump")
    p.add_argument("--length", type=lambda value: int(value, 0), help="number of bytes to capture")
    p.add_argument("--count", type=int, help="decode at most this many declaration records")
    p.set_defaults(fn=cmd_capture_d3d9_memory_declaration)

    p = sp.add_parser("validate-d3d9-runtime-layout", help="validate runtime declaration offsets against recovered Type sizes")
    p.add_argument("input", help="SHIFT.D3D9DeclarationInstanceEvidence/1 or SHIFT.D3D9MemoryDeclarationEvidence/1 JSON input")
    p.add_argument("output", help="SHIFT.D3D9RuntimeDeclarationLayoutEvidence/1 JSON output")
    p.set_defaults(fn=cmd_validate_d3d9_runtime_layout)


    p = sp.add_parser("decode-d3d9-declaration", help="decode raw 8-byte D3D9 declaration records")
    p.add_argument("input", help="raw declaration-record bytes")
    p.add_argument("output", help="SHIFT.D3D9DeclarationInstanceEvidence/1 JSON output")
    p.add_argument("--count", type=int, help="decode at most this many records")
    p.set_defaults(fn=cmd_decode_d3d9_declaration)

    p = sp.add_parser("bmw-reference-render", help="render one ready BMW material slice through the desktop reference renderer")
    p.add_argument("slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("mesh", help="neutral MEB mesh JSON")
    p.add_argument("output", help="output PPM")
    p.add_argument("--width", type=int, default=512)
    p.add_argument("--height", type=int, default=512)
    p.add_argument("--shader-reference", action="store_true")
    p.add_argument("--texture-json", help="optional SHIFT.ReferenceTexture/1 JSON")
    p.set_defaults(fn=cmd_bmw_reference_render)

    p = sp.add_parser("bmw-material-slice", help="extract one exact BMW material draw from SHIFT.BMWRenderSlice/1")
    p.add_argument("slice", help="SHIFT.BMWRenderSlice/1 JSON")
    p.add_argument("output", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("--primitive-index", type=int, default=0)
    p.set_defaults(fn=cmd_bmw_material_slice)

    p = sp.add_parser("bmw-render-slice", help="extract one exact BMW M3 packet from SHIFT.RenderBinding/1")
    p.add_argument("golden", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("render_binding", help="SHIFT.RenderBinding/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRenderSlice/1 JSON")
    p.set_defaults(fn=cmd_bmw_render_slice)

    p = sp.add_parser("bmw-golden-gate", help="validate the BMW M3 golden asset against a DrawPacket")
    p.add_argument("golden", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("draw_packet", help="SHIFT.DrawPacket/1 JSON")
    p.add_argument("--material-binding", help="optional SHIFT.MaterialBinding/1 JSON")
    p.add_argument("-o", "--output", help="optional SHIFT.BMWGoldenRenderGate/1 JSON")
    p.set_defaults(fn=cmd_bmw_golden_gate)

    p = sp.add_parser("source-d3d9-shader-constant-bind", help="analyze source-backed D3D9 float shader constant bind wrappers")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9ShaderConstantBindEvidence/1 JSON")
    p.set_defaults(fn=cmd_source_d3d9_shader_constant_bind)

    p = sp.add_parser("source-d3d9-shader-lifecycle", help="analyze source-backed D3D9 shader bind lifecycle in SHIFT.exe.c")
    p.add_argument("input", help="recovered SHIFT.exe Ghidra C source")
    p.add_argument("output", help="SHIFT.D3D9ShaderLifecycleEvidence/1 JSON")
    p.set_defaults(fn=cmd_source_d3d9_shader_lifecycle)

    p = sp.add_parser("validate-d3d9-capture", help="validate a JSONL runtime capture against SHIFT.D3D9RuntimeCaptureSchema/1")
    p.add_argument("input", help="D3D9 runtime capture JSONL")
    p.add_argument("output", help="SHIFT.D3D9RuntimeCaptureSchema/1 JSON")
    p.set_defaults(fn=cmd_validate_d3d9_capture)

    p = sp.add_parser("d3d9-runtime-trace", help="build runtime D3D9 declaration/binding evidence from JSONL capture")
    p.add_argument("trace", help="runtime capture JSONL")
    p.add_argument("output", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("--meb-resource", help="optional MEB resource analysis JSON")
    p.add_argument("--usage-map", help="optional JSON mapping MEB Usage ordinals to D3D9 Usage bytes")
    p.add_argument("--require-same-instance", action="store_true", help="return 2 unless strict same-instance proof is established")
    p.set_defaults(fn=cmd_d3d9_runtime_trace)

    p = sp.add_parser("bmw-runtime-render-contract", help="build the exact BMW runtime render contract from shader selection and D3D9 capture")
    p.add_argument("material_input", help="BMW material binding/evidence JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("primary_bff", help="primary BMW_M3_E36.bff")
    p.add_argument("render_bff", help="RENDER.bff containing the selected FXO")
    p.add_argument("output", help="SHIFT.BMWRuntimeRenderContract/1 JSON")
    p.set_defaults(fn=cmd_bmw_runtime_render_contract)

    p = sp.add_parser("bmw-runtime-shader-select", help="select an exact BMW FXO permutation from captured D3D9 shader identity")
    p.add_argument("material_input", help="SHIFT.RealBMWMaterialBindingEvidence/1 or SHIFT.MaterialBinding/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRuntimeShaderSelection/1 JSON")
    p.add_argument("--allow-resource-mismatch", action="store_true", help="diagnostic mode; do not require exact MEB resource identity")
    p.set_defaults(fn=cmd_bmw_runtime_shader_select)

    p = sp.add_parser("bmw-runtime-shader-join", help="join a BMW material slice with captured D3D9 runtime shader state")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRuntimeShaderJoin/1 JSON")
    p.set_defaults(fn=cmd_bmw_runtime_shader_join)

    p = sp.add_parser("bmw-vertex-input-parity", help="validate BMW shader semantic inputs against a captured D3D9 declaration")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWVertexInputParity/1 JSON")
    p.add_argument("--usage-map", required=True, help="evidence-backed JSON mapping MEB Usage ordinals to D3D9 Usage bytes")
    p.set_defaults(fn=cmd_bmw_vertex_input_parity)

    p = sp.add_parser("bmw-runtime-draw-correlation", help="correlate one exact BMW primitive with a captured indexed draw")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRuntimeDrawCorrelation/1 JSON")
    p.set_defaults(fn=cmd_bmw_runtime_draw_correlation)

    p = sp.add_parser("bmw-material-slice-golden-gate", help="validate one BMWMaterialSlice/1 against the exact M3 golden manifest")
    p.add_argument("golden", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("output", help="SHIFT.BMWMaterialSliceGoldenGate/1 JSON")
    p.add_argument("--primitive-index", type=int, default=1)
    p.set_defaults(fn=cmd_bmw_material_slice_golden_gate)

    p = sp.add_parser("bmw-real-material-slice", help="build a renderer-compatible BMWMaterialSlice/1 from retail BFF data")
    p.add_argument("input", help="primary BMW_M3_E36.bff")
    p.add_argument("golden", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("output", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("--primitive-index", type=int, default=1)
    p.add_argument("--supplemental-bff", action="append", default=[], help="additional BFF archives")
    p.set_defaults(fn=cmd_bmw_real_material_slice)

    p = sp.add_parser("bmw-bff-intake", help="verify the exact BMW M3 BFF archive and target entries")
    p.add_argument("input", help="primary BMW_M3_E36.bff")
    p.add_argument("output", help="SHIFT.BMWBFFIntakeEvidence/1 JSON")
    p.set_defaults(fn=cmd_bmw_bff_intake)

    p = sp.add_parser("bmw-runtime-shader-render", help="execute exact captured BMW VS/PS offline")
    p.add_argument("contract", help="SHIFT.BMWRuntimeRenderContract/1 JSON")
    p.add_argument("material_input", help="SHIFT.RealBMWMaterialBindingEvidence/1 JSON")
    p.add_argument("mesh_json", help="neutral MEB JSON with vertices/indices/UVs")
    p.add_argument("primary_bff", help="BMW_M3_E36.bff containing material DDS")
    p.add_argument("output", help="shader-executed PPM output")
    p.add_argument("--external-resource", action="append", default=[], help="STAGE=ReferenceTexture/1, ReferenceCubeTexture/1 or DDS path")
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=800)
    p.set_defaults(fn=cmd_bmw_runtime_shader_render)

    p = sp.add_parser("bmw-runtime-capture-pipeline", help="run BMW capture -> runtime evidence -> exact shader -> RenderContract pipeline")
    p.add_argument("primary_bff", help="primary BMW_M3_E36.bff")
    p.add_argument("render_bff", help="RENDER.bff")
    p.add_argument("capture_jsonl", help="D3D9 producer JSONL capture")
    p.add_argument("output", help="SHIFT.BMWRuntimeCapturePipeline/1 JSON")
    p.add_argument("--cockpit-bff")
    p.add_argument("--meb-evidence", default="evidence/bmw_m3_e36_kit00_body_loda.meb.json")
    p.add_argument("--usage-map")
    p.add_argument("--require-same-instance", action="store_true")
    p.set_defaults(fn=cmd_bmw_runtime_capture_pipeline)

    p = sp.add_parser("render-bff-evidence", help="build real BMW M3 BMT/MEB plus split RENDER.bff shader evidence")
    p.add_argument("primary", help="primary BMW_M3_E36.bff")
    p.add_argument("render_bff", help="renderer archive, normally RENDER.bff")
    p.add_argument("output", help="SHIFT.BMWRenderBFFEvidence/1 JSON output")
    p.add_argument("--supplemental-bff", action="append", default=[], help="additional BFF archives such as BMW_M3_E36_Cockpit.bff")
    p.set_defaults(fn=cmd_render_bff_evidence)

    p = sp.add_parser("bmw-material-from-bff", help="build real BMW M3 MaterialBinding/1 from retail BFF archives")
    p.add_argument("input", help="primary BMW_M3_E36.bff")
    p.add_argument("output", help="SHIFT.RealBMWMaterialBindingEvidence/1 JSON")
    p.add_argument("--supplemental-bff", action="append", default=[], help="additional BFF archives such as BMW_M3_E36_Cockpit.bff")
    p.set_defaults(fn=cmd_bmw_material_from_bff)

    p = sp.add_parser("bmw-meb-evidence-parity", help="compare exact BMW M3 MEB evidence with the golden manifest")
    p.add_argument("evidence", help="SHIFT.BMWM3MEBEvidence/1 JSON")
    p.add_argument("golden", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("output", help="SHIFT.BMWM3MEBEvidenceParity/1 JSON")
    p.set_defaults(fn=cmd_bmw_meb_evidence_parity)

    p = sp.add_parser("source-bmw-vehicle-identity", help="verify the source-level BMW M3 vehicle selector in SHIFT.exe.c")
    p.add_argument("input", help="decompiled SHIFT.exe.c source file")
    p.add_argument("output", help="SHIFT.SourceVehicleIdentityEvidence/1 JSON")
    p.set_defaults(fn=cmd_source_bmw_vehicle_identity)

    p = sp.add_parser("bmw-paint-asset-contract", help="validate the exact BMW M3 golden MEB -> paint material relationship")
    p.add_argument("input", help="SHIFT.BMWGoldenAssetManifest/1 JSON")
    p.add_argument("output", help="SHIFT.BMWM3PaintAssetContract/1 JSON")
    p.set_defaults(fn=cmd_bmw_paint_asset_contract)

    p = sp.add_parser("bmw-paint-contract", help="validate the evidence-backed BMW M3 paint material binding")
    p.add_argument("input", help="BMW paint material binding JSON")
    p.add_argument("output", help="SHIFT.BMWM3PaintMaterialContract/1 validation JSON")
    p.set_defaults(fn=cmd_bmw_paint_contract)

    p = sp.add_parser("render-command-constant-parity", help="validate MaterialConstantPayload/uniform ranges against RenderCommand constants")
    p.add_argument("input", help="SHIFT.RenderCommand/1 JSON")
    p.add_argument("output", help="SHIFT.RenderCommandConstantParity/1 JSON")
    p.set_defaults(fn=cmd_render_command_constant_parity)

    p = sp.add_parser("meb-runtime-usage-bridge", help="derive a MEB Usage-ordinal to D3D9 Usage-byte map from exact same-resource runtime declarations")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.MEBRuntimeUsageOrdinalBridge/1 JSON")
    p.set_defaults(fn=cmd_meb_runtime_usage_bridge)

    p = sp.add_parser("bmw-runtime-golden-gate", help="gate BMW golden rendering on complete runtime parity")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRuntimeGoldenGate/1 JSON")
    p.add_argument("--usage-map", required=True, help="evidence-backed JSON mapping MEB Usage ordinals to D3D9 Usage bytes")
    p.set_defaults(fn=cmd_bmw_runtime_golden_gate)

    p = sp.add_parser("bmw-runtime-parity", help="validate BMW runtime shader, constant and declaration parity")
    p.add_argument("material_slice", help="SHIFT.BMWMaterialSlice/1 JSON")
    p.add_argument("runtime_report", help="SHIFT.D3D9RuntimeBindingEvidence/1 JSON")
    p.add_argument("output", help="SHIFT.BMWRuntimeParity/1 JSON")
    p.add_argument("--usage-map", help="optional JSON mapping MEB Usage ordinals to D3D9 Usage bytes")
    p.set_defaults(fn=cmd_bmw_runtime_parity)

    p = sp.add_parser("validate", help="decode/validate every resource")
    p.add_argument("input", help="BFF file or directory")
    p.add_argument("--report")
    p.add_argument("--max-failures", type=int, default=200)
    p.add_argument("--fail-fast", action="store_true")
    p.set_defaults(fn=cmd_validate)

    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.fn(args))
    except BrokenPipeError:
        return 1
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())