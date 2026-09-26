#!/usr/bin/env python3
"""Extract raw D3D9 buffer upload blobs from a compact apitrace trace.

The D3D9 tracer records write-side mapped memory as a fake memcpy call whose
src argument is a TYPE_BLOB. This parser reads the apitrace binary format,
associates each fake memcpy with its enclosing VertexBuffer9/IndexBuffer9
Unlock call, and filters to exact BMW resource instances from the Phase 348
geometry report.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path


FORMAT = "SHIFT.APITRACEBMWBufferBlobEvidence/1"
TRACE_VERSION = 6

EVENT_ENTER = 0
EVENT_LEAVE = 1
CALL_END = 0
CALL_ARG = 1
CALL_RET = 2
CALL_THREAD = 3
CALL_BACKTRACE = 4
CALL_FLAGS = 5
FLAG_FAKE = 1

TYPE_NULL = 0
TYPE_FALSE = 1
TYPE_TRUE = 2
TYPE_SINT = 3
TYPE_UINT = 4
TYPE_FLOAT = 5
TYPE_DOUBLE = 6
TYPE_STRING = 7
TYPE_BLOB = 8
TYPE_ENUM = 9
TYPE_BITMASK = 10
TYPE_ARRAY = 11
TYPE_STRUCT = 12
TYPE_OPAQUE = 13
TYPE_REPR = 14
TYPE_WSTRING = 15

THIS_RE = re.compile(r"\bthis\s*=\s*(0x[0-9a-fA-F]+)")
LENGTH_RE = re.compile(r"\bLength\s*=\s*(\d+)")


class TraceFormatError(ValueError):
    pass


class Snappy:
    def __init__(self) -> None:
        name = ctypes.util.find_library("snappy") or "libsnappy.so.1"
        try:
            self.lib = ctypes.CDLL(name)
        except OSError as exc:
            raise RuntimeError(
                "libsnappy is required to read apitrace .trace files"
            ) from exc
        self.lib.snappy_uncompressed_length.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.snappy_uncompressed_length.restype = ctypes.c_int
        self.lib.snappy_uncompress.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.lib.snappy_uncompress.restype = ctypes.c_int

    def uncompress(self, data: bytes) -> bytes:
        source = ctypes.create_string_buffer(data)
        out_len = ctypes.c_size_t()
        if self.lib.snappy_uncompressed_length(
            source, len(data), ctypes.byref(out_len)
        ) != 0:
            raise TraceFormatError("invalid Snappy chunk")
        target = ctypes.create_string_buffer(out_len.value)
        actual = ctypes.c_size_t(out_len.value)
        if self.lib.snappy_uncompress(
            source, len(data), target, ctypes.byref(actual)
        ) != 0 or actual.value != out_len.value:
            raise TraceFormatError("Snappy decompression failed")
        return target.raw[:actual.value]


def read_trace_bytes(path: Path, max_decompressed_bytes: int) -> bytes:
    raw = path.read_bytes()
    if len(raw) < 6 or raw[:2] != b"at":
        raise TraceFormatError(
            "not an apitrace Snappy trace (missing 'at' magic)"
        )
    snappy = Snappy()
    out = bytearray()
    pos = 2
    while pos < len(raw):
        if pos + 4 > len(raw):
            raise TraceFormatError("truncated Snappy chunk length")
        size = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        end = pos + size
        if end > len(raw):
            raise TraceFormatError("truncated Snappy chunk")
        out.extend(snappy.uncompress(raw[pos:end]))
        if len(out) > max_decompressed_bytes:
            raise TraceFormatError(
                f"decompressed trace exceeds safety limit ({max_decompressed_bytes} bytes)"
            )
        pos = end
    return bytes(out)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.function_sigs = {}
        self.struct_sigs = {}
        self.enum_sigs = set()
        self.bitmask_sigs = set()
        self.backtrace_frames = set()

    def byte(self) -> int:
        if self.pos >= len(self.data):
            raise TraceFormatError("unexpected end of trace")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def uint(self) -> int:
        value = 0
        shift = 0
        while True:
            c = self.byte()
            value |= (c & 0x7F) << shift
            if not c & 0x80:
                return value
            shift += 7
            if shift > 70:
                raise TraceFormatError("invalid varuint")

    def string(self) -> str:
        size = self.uint()
        end = self.pos + size
        if end > len(self.data):
            raise TraceFormatError("truncated string")
        value = self.data[self.pos:end].decode("utf-8", "replace")
        self.pos = end
        return value

    def sint(self) -> int:
        kind = self.byte()
        if kind == TYPE_SINT:
            return -self.uint()
        if kind == TYPE_UINT:
            return self.uint()
        raise TraceFormatError(f"invalid signed integer type {kind}")

    def enum_sig(self) -> None:
        sig_id = self.uint()
        if sig_id in self.enum_sigs:
            return
        count = self.uint()
        for _ in range(count):
            self.string()
            self.sint()
        self.enum_sigs.add(sig_id)

    def bitmask_sig(self) -> None:
        sig_id = self.uint()
        if sig_id in self.bitmask_sigs:
            return
        count = self.uint()
        for _ in range(count):
            self.string()
            self.uint()
        self.bitmask_sigs.add(sig_id)

    def function_sig(self):
        sig_id = self.uint()
        cached = self.function_sigs.get(sig_id)
        if cached is not None:
            return cached
        name = self.string()
        count = self.uint()
        args = [self.string() for _ in range(count)]
        cached = (name, args)
        self.function_sigs[sig_id] = cached
        return cached

    def backtrace(self) -> None:
        count = self.uint()
        for _ in range(count):
            frame_id = self.uint()
            if frame_id in self.backtrace_frames:
                continue
            self.backtrace_frames.add(frame_id)
            while True:
                detail = self.byte()
                if detail == 0:
                    break
                if detail in (1, 2, 3):
                    self.string()
                elif detail in (4, 5):
                    self.uint()
                else:
                    raise TraceFormatError(f"unknown backtrace detail {detail}")

    def value(self):
        kind = self.byte()
        if kind == TYPE_NULL:
            return None
        if kind == TYPE_FALSE:
            return False
        if kind == TYPE_TRUE:
            return True
        if kind == TYPE_SINT:
            return -self.uint()
        if kind == TYPE_UINT:
            return self.uint()
        if kind == TYPE_FLOAT:
            end = self.pos + 4
            if end > len(self.data):
                raise TraceFormatError("truncated float")
            value = struct.unpack_from("<f", self.data, self.pos)[0]
            self.pos = end
            return value
        if kind == TYPE_DOUBLE:
            end = self.pos + 8
            if end > len(self.data):
                raise TraceFormatError("truncated double")
            value = struct.unpack_from("<d", self.data, self.pos)[0]
            self.pos = end
            return value
        if kind == TYPE_STRING:
            return self.string()
        if kind == TYPE_BLOB:
            size = self.uint()
            end = self.pos + size
            if end > len(self.data):
                raise TraceFormatError("truncated blob")
            value = self.data[self.pos:end]
            self.pos = end
            return value
        if kind == TYPE_ENUM:
            self.enum_sig()
            return self.sint()
        if kind == TYPE_BITMASK:
            self.bitmask_sig()
            return self.uint()
        if kind == TYPE_ARRAY:
            return [self.value() for _ in range(self.uint())]
        if kind == TYPE_STRUCT:
            sig_id = self.uint()
            count = self.struct_sigs.get(sig_id)
            if count is None:
                self.string()
                count = self.uint()
                for _ in range(count):
                    self.string()
                self.struct_sigs[sig_id] = count
            return [self.value() for _ in range(count)]
        if kind == TYPE_OPAQUE:
            return self.uint()
        if kind == TYPE_REPR:
            return (self.value(), self.value())
        if kind == TYPE_WSTRING:
            return [self.uint() for _ in range(self.uint())]
        raise TraceFormatError(
            f"unknown value type {kind} at offset {self.pos - 1}"
        )

    def properties(self) -> dict[str, str]:
        result = {}
        while True:
            name = self.string()
            if not name:
                return result
            result[name] = self.string()


def pointer(value) -> str | None:
    return f"0x{value:x}" if isinstance(value, int) else None


def geometry_identities(path: Path) -> dict[str, list[dict]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != "SHIFT.APITRACEUniqueBMWGeometry/1":
        raise ValueError(
            f"unsupported geometry report format: {report.get('format')!r}"
        )
    result: dict[str, list[dict]] = defaultdict(list)
    for kind, plural in (
        ("vertex_buffer", "vertex_buffers"),
        ("index_buffer", "index_buffers"),
    ):
        for resource in report.get("resources", {}).get(plural, []):
            ptr = resource.get("pointer")
            creation = (resource.get("creation") or {}).get("call")
            if not ptr or not isinstance(creation, int):
                continue
            raw = str((resource.get("creation") or {}).get("raw") or "")
            length_match = LENGTH_RE.search(raw)
            expected_size = int(length_match.group(1)) if length_match else None
            if kind == "vertex_buffer":
                expected_size = expected_size or resource.get(
                    "derived_bytes_if_num_vertices_times_stride"
                )
            lifecycle = resource.get("lifecycle") or {}
            releases = [
                n for n in lifecycle.get("release_calls") or []
                if isinstance(n, int) and n > creation
            ]
            stop = min(releases) if releases else None
            locks = {
                n for n in lifecycle.get("lock_calls") or []
                if isinstance(n, int)
                and n > creation
                and (stop is None or n < stop)
            }
            unlocks = {
                n for n in lifecycle.get("unlock_calls") or []
                if isinstance(n, int)
                and n > creation
                and (stop is None or n < stop)
            }
            result[ptr].append(
                {
                    "kind": kind,
                    "pointer": ptr,
                    "creation_call": creation,
                    "expected_size": expected_size,
                    "lock_calls": locks,
                    "unlock_calls": unlocks,
                }
            )
    return result


def extract(
    trace: Path,
    geometry_report: Path,
    output_dir: Path,
    *,
    max_decompressed_bytes: int = 128 * 1024 * 1024,
) -> dict:
    allowed = geometry_identities(geometry_report)
    data = read_trace_bytes(trace, max_decompressed_bytes)

    reader = Reader(data)
    trace_version = reader.uint()
    semantic_version = reader.uint()
    if trace_version != TRACE_VERSION:
        raise TraceFormatError(
            f"unsupported trace version {trace_version}; expected {TRACE_VERSION}"
        )
    reader.properties()

    stacks: dict[int, list[dict]] = defaultdict(list)
    last_lock: dict[str, int] = {}
    records = []
    dedup = {}

    while reader.pos < len(data):
        event = reader.byte()
        if event == EVENT_ENTER:
            thread_id = reader.uint() if semantic_version >= 4 else 0
            name, _ = reader.function_sig()
            frame = {
                "call": getattr(reader, "_call_no", 0),
                "thread": thread_id,
                "name": name,
                "args": {},
                "fake": False,
                "parent": stacks[thread_id][-1] if stacks[thread_id] else None,
            }
            reader._call_no = frame["call"] + 1
            stacks[thread_id].append(frame)

            while True:
                detail = reader.byte()
                if detail == CALL_END:
                    break
                if detail == CALL_ARG:
                    index = reader.uint()
                    frame["args"][index] = reader.value()
                elif detail == CALL_RET:
                    frame["ret"] = reader.value()
                elif detail == CALL_THREAD:
                    frame["thread_detail"] = reader.uint()
                elif detail == CALL_BACKTRACE:
                    reader.backtrace()
                elif detail == CALL_FLAGS:
                    frame["fake"] = bool(reader.uint() & FLAG_FAKE)
                else:
                    raise TraceFormatError(
                        f"unknown call detail {detail} for {name}"
                    )

            if name.endswith("::Lock"):
                ptr = pointer(frame["args"].get(0))
                if ptr:
                    last_lock[ptr] = frame["call"]
            elif name.endswith("::Release"):
                ptr = pointer(frame["args"].get(0))
                if ptr:
                    last_lock.pop(ptr, None)

            if name == "memcpy" and frame["fake"]:
                parent = frame["parent"]
                blob = frame["args"].get(1)
                unlock_call = parent["call"] if parent else None
                unlock_name = parent["name"] if parent else None
                buffer_ptr = (
                    pointer(parent["args"].get(0)) if parent else None
                )
                if (
                    isinstance(blob, bytes)
                    and unlock_name in {
                        "IDirect3DVertexBuffer9::Unlock",
                        "IDirect3DIndexBuffer9::Unlock",
                    }
                    and unlock_call is not None
                    and buffer_ptr in allowed
                ):
                    candidates = [
                        row for row in allowed[buffer_ptr]
                        if unlock_call in row["unlock_calls"]
                    ]
                    if candidates:
                        row = candidates[0]
                        sha = hashlib.sha256(blob).hexdigest()
                        payload_dir = output_dir / "buffer_payloads"
                        payload_dir.mkdir(parents=True, exist_ok=True)
                        filename = (
                            f"{row['kind']}_{buffer_ptr[2:]}_"
                            f"{unlock_call}_{frame['call']}_{sha[:16]}.bin"
                        )
                        path = payload_dir / filename
                        if sha not in dedup:
                            path.write_bytes(blob)
                            dedup[sha] = path
                        else:
                            path = dedup[sha]
                        expected = row["expected_size"]
                        records.append(
                            {
                                "fake_memcpy_call": frame["call"],
                                "unlock_call": unlock_call,
                                "lock_call": last_lock.get(buffer_ptr),
                                "thread": thread_id,
                                "buffer_kind": row["kind"],
                                "buffer_pointer": buffer_ptr,
                                "creation_call": row["creation_call"],
                                "blob_size": len(blob),
                                "expected_buffer_size": expected,
                                "full_buffer_candidate": (
                                    expected is not None and len(blob) == expected
                                ),
                                "blob_sha256": sha,
                                "payload_path": str(path),
                                "n_argument": frame["args"].get(2),
                                "n_matches_blob_size": (
                                    frame["args"].get(2) == len(blob)
                                ),
                                "dest_pointer": pointer(frame["args"].get(0)),
                            }
                        )
            continue

        if event == EVENT_LEAVE:
            call_no = reader.uint()
            while True:
                detail = reader.byte()
                if detail == CALL_END:
                    break
                if detail == CALL_ARG:
                    reader.uint()
                    reader.value()
                elif detail == CALL_RET:
                    reader.value()
                elif detail == CALL_THREAD:
                    reader.uint()
                elif detail == CALL_BACKTRACE:
                    reader.backtrace()
                elif detail == CALL_FLAGS:
                    reader.uint()
                else:
                    raise TraceFormatError(
                        f"unknown leave detail {detail} for call {call_no}"
                    )
            for stack in stacks.values():
                if stack and stack[-1]["call"] == call_no:
                    stack.pop()
                    break
            continue

        raise TraceFormatError(
            f"unknown event {event} at offset {reader.pos - 1}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "format": FORMAT,
        "source": {
            "trace": str(trace),
            "trace_size_bytes": trace.stat().st_size,
            "decompressed_size_bytes": len(data),
            "geometry_report": str(geometry_report),
        },
        "buffers": records,
        "summary": {
            "payload_records": len(records),
            "unique_payload_blobs": len({r["blob_sha256"] for r in records}),
            "full_buffer_candidates": sum(
                bool(r["full_buffer_candidate"]) for r in records
            ),
            "kinds": {
                kind: sum(1 for r in records if r["buffer_kind"] == kind)
                for kind in ("vertex_buffer", "index_buffer")
            },
        },
        "evidence_boundary": {
            "fake_memcpy_blob": "observed" if records else "not-observed",
            "runtime_buffer_identity": "observed" if records else "not-observed",
            "exact_vb_bytes": "candidate-only",
            "exact_ib_bytes": "candidate-only",
            "meb_byte_parity": "not-run",
        },
    }
    (output_dir / "buffer_blob_evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence["summary"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("geometry_report", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--max-decompressed-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    args = parser.parse_args(argv)
    result = extract(
        args.trace.expanduser().resolve(),
        args.geometry_report.expanduser().resolve(),
        args.output_dir.expanduser().resolve(),
        max_decompressed_bytes=max(1, args.max_decompressed_bytes),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
