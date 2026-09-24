# Phase 146 — BMW M3 MEB evidence parity

`SHIFT.BMWM3MEBEvidence/1` is a compact snapshot of the exact parsed M3 body MEB
resource from the supplied evidence corpus. `SHIFT.BMWM3MEBEvidenceParity/1` compares
that snapshot against the committed `BMWGoldenAssetManifest/1`.

## Exact resource

- path: `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`;
- SHA-256: `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`;
- BFF entry index: 863;
- uncompressed size: 300,764 bytes;
- 3,550 vertices / 5,034 triangles;
- six primitives;
- eight MEB property descriptors;
- eight property storage/layout records;
- static, non-skinned mesh.

The parity validator checks resource identity, archive metadata, mesh counts, primitive
definitions, property descriptors and property layouts.

## CLI

```bash
python shift_importer.py bmw-meb-evidence-parity \
  evidence/bmw_m3_e36_kit00_body_loda.meb.json \
  evidence/bmw_m3_e36_kit00_body_loda.golden.json \
  bmw-m3-meb-parity.json
```

## Boundary

This artifact contains parsed metadata, not the raw MEB payload. It is resource-level
evidence and does not prove runtime execution.