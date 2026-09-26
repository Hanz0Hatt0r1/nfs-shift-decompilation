# Phase 350: recover raw BMW VB/IB blobs from apitrace

Phase 349 now retains the exact D3D9 Unlock calls and the separate fake memcpy
calls emitted by apitrace. Those fake calls carry the mapped bytes as TYPE_BLOB
values. Phase 350 parses the compact binary trace directly and extracts those
blob bytes for the seven verified BMW buffer instances.

## Command

    python tools/extract_apitrace_bmw_buffer_blobs.py       ./bmw_buffer_payload/bmw_buffer_payload.trace       ./bmw-apitrace-evidence/unique_bmw_geometry.json       ./bmw_buffer_payload/extracted

## Output

    extracted/
    ├── buffer_blob_evidence.json
    └── buffer_payloads/
        └── *.bin

Each payload record preserves the fake memcpy call, the immediately following Unlock call,
resource creation call, buffer pointer, payload size and SHA-256. A payload is
marked a full-buffer candidate only when its byte count equals the verified
D3D9 creation length.

## Format implementation

The reader handles the apitrace version-6 header, Snappy chunks, varuint values,
function signatures, call nesting, opaque pointers and TYPE_BLOB values. It
tracks the active call stack per thread so a fake memcpy is attributed to the
Unlock that emitted it.

The parser reads the compact trace into a bounded decompressed buffer. The
default safety limit is 128 MiB, far above the expected roughly 310 KiB total
BMW VB/IB upload data while keeping accidental huge inputs fail-closed.

## Evidence boundary

This phase establishes raw runtime buffer bytes from the apitrace capture. It
does not automatically declare MEB parity. The final check remains an explicit
byte-for-byte comparison against the canonical MEB-derived candidates, with the
runtime resource instance as the identity gate.
