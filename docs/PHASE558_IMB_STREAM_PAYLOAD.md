# Phase 558 — IMB descriptor/vertex blocks

The complete `FUN_00859800` body corrects the Phase 556 assumption that all
stream descriptors form one contiguous table. The actual source sequence is:

`descriptor[0] → vertices[0] → descriptor[1] → vertices[1] → primitives`.

Each descriptor is 12 bytes (`Type`, `Usage`, `Channel`). Its payload contains
`vertex_count` elements before the next descriptor is consumed. The loader
later interleaves these separate buffers into its runtime vertex buffer.

## Supported consumption

| Mapped D3D9 Type | Bytes per vertex |
|---|---:|
| FLOAT1 / 0 | 4 |
| FLOAT2 / 1 | 8 |
| FLOAT3 / 2 | 12 |
| FLOAT4 / 3 | 16 |
| D3DCOLOR / 4 | 4 |
| UBYTE4 / 5 | 4 |
| UBYTE4N / 8 | 4 |

The retail PE's `DAT_00b90088` table confirms that these source ordinals map
to the same numeric Types. Other Types reach the loader's default branch
without source-cursor advancement. This decoder rejects them rather than
applying generic D3D9 element sizes to the serialized IMB stream.

## Decoder contract

`SHIFT.IMBBinaryMeshSchema/1` now preserves each supported stream's exact
payload as hex, its source offset/size, and its runtime element offset.
`streams.runtime_vertex_stride` records the combined supported element sizes.
`primitives.source_section_offset` is now the exact cursor after all streams.
`vertex_payload_offset` identifies the first stream's payload; each later
payload has its own offset. With no streams it identifies the section end.

The existing automatic and manual CLI paths both use the corrected layout.
Files with unsupported Types fail with `ValueError`. Primitive records are
still unparsed, and no neutral renderer admission is enabled by this change.

## Evidence and validation

The source export retrieved from Google Drive has SHA-256
`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`,
matching the project's earlier source snapshot. The retrieved executable's
SHA-256 and relevant file-backed type-table bytes are recorded in
`evidence/imb_binary_stream_payload_source.json`.

Tests use two distinguishable streams to prevent a regression to contiguous
descriptors, check exact consumption for every supported Type, reject
unsupported Types and truncated payloads, and exercise every truncation of
version/header/bone/descriptor fixtures. Oversized bone counts and incomplete
matrix blocks are rejected before name iteration.

Next: parse the material-name/count/palette/index/bounds primitive records
using the now-proven section boundary; validate against extracted retail IMB
files and adapt proven geometry/material data into the scene pipeline.
