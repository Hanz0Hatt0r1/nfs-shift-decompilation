# Phase 118 — BMW golden render gate

Phase 118 turns the selected BMW M3 MEB manifest into an executable acceptance
contract. `SHIFT.BMWGoldenRenderGate/1` compares the real resource identity, mesh
counts, primitive ranges, proven COLOR0 descriptor and shader-selection state before
the desktop renderer is allowed to be treated as a golden result.

## Contract

`bmw_golden_gate.py` accepts:

- a `SHIFT.BMWGoldenAssetManifest/1` JSON;
- a `SHIFT.DrawPacket/1` JSON;
- optionally a `SHIFT.MaterialBinding/1` JSON.

The gate is fail-closed on missing or mismatched SHA-256 resource identity, resource
path mismatch, mesh-count mismatch, primitive mismatch, non-unique shader selection,
missing linked GLSL, or missing COLOR0 evidence.

## CLI

```bash
python bmw_golden_gate.py evidence/bmw_m3_e36_kit00_body_loda.golden.json draw_packets.json
```

## Next target

`BMW M3 MEB -> exact material record -> FX source -> unique FXO program -> linked
shader pair -> RenderCommand -> deterministic PPM golden hash`.

The runtime D3D9 capture bridge remains a separate evidence track and is not replaced
by this offline gate.
