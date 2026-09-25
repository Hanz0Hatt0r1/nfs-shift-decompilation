# BMW M3 E36 KIT00 test scene

The repository now contains a reproducible scene definition at
`tests/scenes/bmw_m3_e36_kit00_test_scene.json` and a renderer entry point at
`bmw_test_scene.py`.

## Scene

The scene is pinned to the supplied `BMW_M3_E36.bff` SHA-256:

`c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70`

Selection is the existing VHF geometry path:

- vehicle: `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`
- KIT: `00`
- LOD: `A`
- generic shared parts: enabled
- lightglows: disabled
- renderable parts observed in the generated scene: 27
- body MEB: `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`
- body MEB SHA-256: `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`

## Camera set

The scene has four fixed views:

| View | Yaw | Pitch |
|---|---:|---:|
| front_left | -28° | -15° |
| rear_right | 152° | -12° |
| side | -90° | -10° |
| front | 0° | -8° |

Generated screenshots are 1600×900 and use a neutral studio presentation layer around
the existing geometry-preview raster. The vehicle geometry itself is sourced from
the supplied BFF/VHF/MEB assets.

## Reproduction

With the real BFF available locally:

```bash
python bmw_test_scene.py \
  /path/to/BMW_M3_E36.bff \
  out/bmw_m3_e36_kit00_test_scene
```

The command emits deterministic PPM renders and a scene manifest containing source and
render hashes.

## Evidence boundary

This is a geometry-preview scene. It does not claim final `bodywork.fx` material
execution, authentic retail D3D9 runtime execution, or resolution of the remaining
COLOR0/COLOR1 runtime ABI questions.
