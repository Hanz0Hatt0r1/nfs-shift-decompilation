# Phase 559 — IMB v0.4 primitive records

The full retail `FUN_00859800` body proves the primitive cursor following the
Phase 558 descriptor/vertex blocks. Optional `--decode-primitives` on both
`imb_format.py` and `shift_importer.py imb-binary-schema` consumes these records
for version 0.4.0.0. The default schema-only path remains available, including
its manual header override. Primitive decoding requires automatic prefix
recovery and rejects earlier versions whose bounds reconstruction is different.

## Serialized sequence

| Field | Storage |
|---|---|
| Material resource name | NUL terminated; round its storage length to 4 bytes |
| Unresolved material word | 4 raw bytes preserved as an unsigned integer |
| Triangle count | u32; runtime type is fixed to 4 / triangle list |
| Bone palette | Only when mesh bone count is nonzero: u32 count, count u16 entries, 2 padding bytes for odd count |
| Triangle indices | triangle_count × 3 u16; 2 padding bytes for odd triangle count |
| Vertex range | two u16 values |
| Bounding sphere | center xyz and radius, four f32 values |
| AABB | min xyz and max xyz, six f32 values |

Name padding rounds the **name's storage length**, not the absolute file offset.
An enabled bone header with zero bones does not serialize a primitive palette.
`FUN_00853c80(count, 4)` independently confirms the index count of count × 3.
The range/bounds trailer is exactly 0x2c bytes; runtime AABB w components are
set to 1 by the loader and are not additional source floats.

## Output and validation

Each record preserves source offset/size, material name and opaque word,
triangle and index counts, exact u16 index/palette arrays, trailer offset,
vertex range, sphere and AABB. The report includes the cursor after all records
and the remaining byte count rather than silently requiring an invented EOF
contract. Indices outside the mesh vertex count are rejected. Palette values,
material lookup and stored bounds are preserved without claiming runtime parity.

Synthetic fixtures cover two successive records, different name lengths,
odd/even triangle and palette counts, unaligned source cursors, zero/nonzero
bone headers, every truncation point, oversized counts, out-of-range indices,
unterminated material names and both CLI paths. The source export identity and
line ranges are recorded in `evidence/imb_binary_primitive_source.json`.

Retail IMB corpus validation, legacy primitive bounds reconstruction, material
word semantics and neutral scene/render adapters remain open. No renderer
admission or same-instance runtime parity is asserted.
