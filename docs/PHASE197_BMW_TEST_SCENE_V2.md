# BMW M3 E36 KIT00 test scene V2

The repository now has a second deterministic BMW scene definition at
`tests/scenes/bmw_m3_e36_kit00_test_scene_v2.json`.

## Source

The scene is pinned to the supplied retail archive:

- `BMW_M3_E36.bff`
- SHA-256: `c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70`
- VHF: `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`
- KIT00 / LODA
- 27 renderable parts
- target body MEB:
  `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`
- body MEB SHA-256:
  `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`

## V2 camera set

| View | Yaw | Pitch |
|---|---:|---:|
| front_three_quarter_low | -32° | -21° |
| rear_three_quarter_low | 148° | -18° |
| high_front_three_quarter | -18° | -32° |
| driver_side_low | -88° | -16° |

## Screenshot boundary

The new PNGs associated with this request are **presentation mockups**, not renderer
artifacts. They are based on the real BMW scene identity above, but they must not be
used as evidence for geometry equivalence, material execution, shader parity or retail
D3D9 runtime proof.

The repository's reproducible renderer remains `bmw_test_scene.py` and produces
geometry-only PPM output from the real BFF/VHF/MEB chain.

## Current proof boundary

This V2 scene changes the camera coverage only. It does not claim final
`bodywork.fx` execution and does not replace the authentic retail D3D9 capture
required by the runtime proof gate.
