# Phase 345: reproducible BMW runtime buffer artifacts

Phase 345 adds a deterministic producer for the byte artifacts consumed by the
Phase 344 runtime-payload comparator.

## Input

`bmw_meb_runtime_buffer_artifacts.py` accepts a retail BFF and resolves the exact
BMW body resource:

`vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`

The extracted MEB is verified against the established SHA-256:

`960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`

## Vertex buffer candidate

The builder reads the preserved MEB property payload offsets and interleaves the
raw bytes in MEB property order. It does not decode/re-encode floats and does
not perform a COLOR byte-order conversion.

For the BMW body this yields the established 3,550-vertex × 76-byte layout:
269,800 bytes.

The result is a deterministic candidate for the runtime D3D9 VB. It is not
declared to be runtime-identical until Phase 344 captures the actual
IDirect3DVertexBuffer9 bytes.

## Index buffer candidates

The full INDEX16 stream is emitted in source index order, and one separate binary
is emitted for each MEB primitive. The primitive buffers therefore correspond
directly to the six runtime buffers already correlated by Phase 343:

- 300 bytes;
- 12,588 bytes;
- 14,772 bytes;
- 1,224 bytes;
- 1,152 bytes;
- 168 bytes.

## Usage

`python bmw_meb_runtime_buffer_artifacts.py BMW_M3_E36.bff out/bmw-buffers`

The output contains:

- `vertex_buffer.meb-order.bin`;
- `index_buffer.uint16.bin`;
- `index_buffer_00.uint16.bin` … `index_buffer_05.uint16.bin`;
- `manifest.json`.

Feed the produced vertex/index candidates into
`bmw_runtime_buffer_payload_parity.py` together with a new D3D9 payload
capture to prove or reject exact byte identity.

## Boundary

This phase makes the expected byte stream reproducible from the retail MEB. It
does not weaken the evidence boundary: reconstructed bytes remain candidates
until they exactly match a bounded runtime payload captured between the resource
creation instance and the target draw.
