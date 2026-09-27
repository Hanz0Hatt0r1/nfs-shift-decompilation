#!/usr/bin/env python3
"""Analyze the binary tail of an apitrace Snappy .trace split into parts.

A tail cut from the middle of an apitrace trace has no apitrace magic and
cannot normally be opened by apitrace directly. This utility works at the
container/chunk level: joins split files, finds the first complete Snappy
chunk boundary, validates/decompresses complete chunks, and scans for useful
D3D9/BMW marker strings.

It deliberately does not claim that a tail is replayable. Function-signature
state can precede the supplied tail, so higher-level call decoding still
requires the original trace or sufficient preceding trace state.
"""
from __future__ import annotations
import argparse, ctypes, ctypes.util, json, re, struct, tempfile
from pathlib import Path
from typing import BinaryIO

MAGIC = b"at"
DEFAULT_MAX_CHUNK = 2 * 1024 * 1024
DEFAULT_SCAN_LIMIT = 2 * 1024 * 1024
MARKERS = (
    b"DrawIndexedPrimitive", b"PresentEx", b"Present",
    b"IDirect3DVertexBuffer9", b"IDirect3DIndexBuffer9",
    b"::Lock", b"::Unlock", b"memcpy", b"fake", b"D3D_OK",
)

class TraceTailError(RuntimeError):
    pass

class Snappy:
    def __init__(self) -> None:
        name = ctypes.util.find_library("snappy") or "libsnappy.so.1"
        try:
            self.lib = ctypes.CDLL(name)
        except OSError as exc:
            raise TraceTailError("libsnappy is required") from exc
        self.lib.snappy_uncompressed_length.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.lib.snappy_uncompressed_length.restype = ctypes.c_int
        self.lib.snappy_uncompress.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t)]
        self.lib.snappy_uncompress.restype = ctypes.c_int

    def uncompress(self, data: bytes) -> bytes:
        source = ctypes.create_string_buffer(data)
        out_len = ctypes.c_size_t()
        if self.lib.snappy_uncompressed_length(
            source, len(data), ctypes.byref(out_len)) != 0:
            raise TraceTailError("invalid Snappy stream")
        target = ctypes.create_string_buffer(out_len.value)
        actual = ctypes.c_size_t(out_len.value)
        if self.lib.snappy_uncompress(
            source, len(data), target, ctypes.byref(actual)) != 0:
            raise TraceTailError("Snappy decompression failed")
        return target.raw[:actual.value]

def discover_parts(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    parts = sorted(path.glob("SHIFT_tail.part.*"))
    if not parts:
        parts = sorted(path.glob("*.part.*"))
    if not parts:
        raise TraceTailError(f"no split parts found in {path}")
    return parts

def copy_joined(parts: list[Path], output: Path) -> int:
    total = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as dst:
        for part in parts:
            with part.open("rb") as src:
                while block := src.read(4 * 1024 * 1024):
                    dst.write(block)
                    total += len(block)
    return total

def valid_chunk(snappy: Snappy, raw: BinaryIO, offset: int,
                file_size: int, max_chunk: int):
    if offset + 4 > file_size:
        return None
    raw.seek(offset)
    header = raw.read(4)
    if len(header) != 4:
        return None
    size = struct.unpack("<I", header)[0]
    if size == 0 or size > max_chunk or offset + 4 + size > file_size:
        return None
    payload = raw.read(size)
    try:
        data = snappy.uncompress(payload)
    except TraceTailError:
        return None
    return size, data

def find_chunk_start(raw: BinaryIO, file_size: int, snappy: Snappy,
                     scan_limit: int, max_chunk: int):
    limit = min(scan_limit, max(0, file_size - 8))
    candidates = 0
    for offset in range(limit + 1):
        item = valid_chunk(snappy, raw, offset, file_size, max_chunk)
        if item is None:
            continue
        candidates += 1
        size, data = item
        if valid_chunk(snappy, raw, offset + 4 + size, file_size, max_chunk):
            return offset, size, data
    raise TraceTailError(
        f"no Snappy boundary found in first {limit} bytes; "
        f"single-chunk candidates={candidates}")

def scan_markers(data: bytes) -> dict[str, list[int]]:
    result = {}
    for marker in MARKERS:
        hits = [m.start() for m in re.finditer(re.escape(marker), data)]
        if hits:
            result[marker.decode("ascii")] = hits[:32]
    return result

def analyze(joined: Path, *, scan_limit: int, max_chunk: int,
            max_chunks: int | None) -> dict:
    snappy = Snappy()
    file_size = joined.stat().st_size
    with joined.open("rb") as raw:
        raw.seek(0)
        magic = raw.read(2)
        start, _, _ = find_chunk_start(
            raw, file_size, snappy, scan_limit, max_chunk)
        pos = start
        chunk_index = 0
        decompressed_total = 0
        markers = []
        truncated_tail = False
        while pos + 4 <= file_size:
            if max_chunks is not None and chunk_index >= max_chunks:
                break
            raw.seek(pos)
            size = struct.unpack("<I", raw.read(4))[0]
            payload_end = pos + 4 + size
            if size == 0 or size > max_chunk or payload_end > file_size:
                truncated_tail = True
                break
            raw.seek(pos + 4)
            payload = raw.read(size)
            try:
                data = snappy.uncompress(payload)
            except TraceTailError:
                truncated_tail = True
                break
            hit = scan_markers(data)
            if hit:
                markers.append({
                    "chunk_index": chunk_index,
                    "file_offset": pos,
                    "compressed_bytes": size,
                    "decompressed_bytes": len(data),
                    "markers": hit,
                })
            decompressed_total += len(data)
            chunk_index += 1
            pos = payload_end
        return {
            "format": "SHIFT.APITRACETraceTailAnalysis/1",
            "input": {"path": str(joined), "size_bytes": file_size},
            "snappy": {
                "magic_present": magic == MAGIC,
                "first_complete_chunk_offset": start,
                "leading_partial_bytes": start,
                "chunks_decoded": chunk_index,
                "decompressed_bytes": decompressed_total,
                "trailing_partial_or_invalid_data": truncated_tail,
            },
            "marker_chunks": markers,
            "replayability": {
                "ready": False,
                "reason": "tail-only input does not preserve preceding apitrace function-signature/replay state",
            },
        }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path,
                   help="joined tail file or directory containing SHIFT_tail.part.*")
    p.add_argument("-o", "--report", type=Path,
                   default=Path("trace_tail_analysis.json"))
    p.add_argument("--joined", type=Path,
                   help="write joined parts here before analysis")
    p.add_argument("--scan-limit", type=int, default=DEFAULT_SCAN_LIMIT)
    p.add_argument("--max-chunk", type=int, default=DEFAULT_MAX_CHUNK)
    p.add_argument("--max-chunks", type=int)
    args = p.parse_args()

    parts = discover_parts(args.input)
    cleanup = False
    if len(parts) == 1 and args.input.is_file():
        joined = parts[0]
    else:
        if args.joined:
            joined = args.joined
        else:
            tmp = tempfile.NamedTemporaryFile(prefix="shift-tail-",
                                               suffix=".trace", delete=False)
            joined = Path(tmp.name)
            tmp.close()
            cleanup = True
        copy_joined(parts, joined)
    try:
        report = analyze(joined, scan_limit=args.scan_limit,
                         max_chunk=args.max_chunk, max_chunks=args.max_chunks)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        if cleanup:
            joined.unlink(missing_ok=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
