# Phase 136 — BMW M3 paint material contract

`SHIFT.BMWM3PaintMaterialContract/1` is a machine-readable copy of the evidence-backed
BMW M3 E36 paint material chain documented in `BMW_M3_E36_MATERIAL_BINDING.md`.

## Contract

- material: `vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt`;
- shader: `bodywork.fx`;
- diffuse `diffuseMap` at s1 → `COMMON_PAINT.dds`;
- specular `specularMap` at s2 → `COMMON_PAINT_SPECULAR.dds`;
- scratch `scratchControlMap` at s4 → `COMMON_BLANK.dds`;
- external environment cube at s3;
- external shadow map at s0;
- specializations: `USE_FRESNEL`, `ALLOW_VINYLS`, `DIRT_SCRATCH`.

Sampler filtering/addressing and sRGB flags are preserved from the source document.

## Boundary

This is material-level evidence from the supplied BMW archive analysis. It does not
prove a specific runtime shader object, frame or draw; those are handled by the
runtime shader join and golden gate.

## CLI

```bash
python shift_importer.py bmw-paint-contract binding.json paint-contract.json
```

## Next

Resolve this exact paint contract into the actual M3 `MaterialBinding/1` produced by
the BMT/FX/FXO pipeline, then compare its permutation identity and RenderCommand
sampler state against the contract before the first golden image.