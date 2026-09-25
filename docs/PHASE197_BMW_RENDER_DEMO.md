# Phase 197 — BMW M3 E36 render checkpoint

This checkpoint makes the first repository-visible render artifact for the BMW M3 E36 vertical slice.

## Provenance

```text
BMW_M3_E36.bff
  ↓ Type-2 XMem/LZX
vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb
  ↓ MEB parser
neutral mesh (3550 vertices / 5034 triangles / 6 primitives)
  ↓ deterministic reference rasterizer
800×450 repository screenshot
```

Source archive SHA-256: `c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70`  
Target MEB SHA-256: `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`

## Screenshot

![BMW M3 E36 render checkpoint](artifacts/render/bmw_m3_e36_render_demo.png)

Repository display PNG SHA-256: `e0c47436f45102846660361e66952f4198d09cb5feff5f3bc37592d72039a8f6`

The repository image is an 800×450 display derivative of the 1600×900 master render. Master SHA-256: `842123e3a55faadfc7d7fa8271105b00969b82ffc89a722772945e58c26b4099`.

## Readiness boundary

**Proven by this checkpoint:** real BFF extraction, Type-2 XMem/LZX decoding, exact target-MEB identity, MEB geometry recovery, and deterministic triangle rasterization.

**Not claimed:** final `bodywork.fx` material execution, retail backbuffer parity, or strict same-instance D3D9 runtime proof. Those remain the next evidence gate.

## Scene manifest

The machine-readable scene manifest is `tests/scenes/bmw_m3_e36_render_demo_scene.json`. It pins the exact source resource, render configuration, screenshot hash, and the explicit readiness limitations above.
