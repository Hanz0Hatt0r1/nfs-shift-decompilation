# Phase 137 — BMW paint binding adapter

Phase 137 aligns `SHIFT.BMWM3PaintMaterialContract/1` with the actual material shape
emitted by `draw_packets.compile_material()`.

The normalizer accepts:

- nested shader references (`shader.ref`);
- texture references stored as `ref` instead of `texture`;
- sampler names/registers from the emitted texture bindings;
- specialization flags from the selected FXO candidate (`specialization_matched`);
- emitted `external_samplers`.

`validate_material_binding()` normalizes the input before checking the documented M3
paint contract. This keeps the evidence contract independent of transient internal
field layout while preserving exact register/texture identity.

## Boundary

This still does not resolve BFFs or select an FXO permutation. It validates the output
of the existing BMT/FXO linker against the already documented BMW M3 paint evidence.

## Next

Run the real M3 material record through `compile_material()` and compare its emitted
sampler registers, specialization flags and texture refs against the contract. Any
missing material field becomes an explicit blocker instead of a synthetic fallback.