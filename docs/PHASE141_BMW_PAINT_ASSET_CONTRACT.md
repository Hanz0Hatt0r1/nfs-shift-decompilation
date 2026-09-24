# Phase 141 — BMW M3 paint asset contract

`SHIFT.BMWM3PaintAssetContract/1` locks the exact golden MEB to the documented M3
paint material.

## Exact asset

- MEB: `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`;
- SHA-256: `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`;
- static mesh: 3550 vertices / 5034 triangles;
- paint primitive 1: `first_index=150`, `index_count=6294`;
- paint primitive 2: `first_index=6444`, `index_count=7386`;
- material alias: `BMW_M3_E36_PAINT.mtx` ↔ `bmw_m3_e36_paint.bmt`.

The contract also requires the manifest provenance fields `bundle`, `bundle_resource_id`,
`collector_version` and `raw_row_sha256`.

`bmw_golden_gate.py` consumes this contract for the exact golden M3 resource.

## CLI

```bash
python shift_importer.py bmw-paint-asset-contract evidence/bmw_m3_e36_kit00_body_loda.golden.json bmw-paint-asset-contract.json
```

## Boundary

This is resource/material evidence only. It does not claim runtime execution or shader
object identity.