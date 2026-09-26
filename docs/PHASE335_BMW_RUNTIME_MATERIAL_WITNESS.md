# Phase 335: BMW M3 draw-local BMT material witness

This phase connects decoded BMW M3 BMT parameter values to the state visible at the
exact `DrawIndexedPrimitive` boundary in the supplied D3D9 frame dump.

## Verified facts

The source material set is the five unique BMTs already closed in Phase 334:

| BMT | Shader | Runtime witness draws |
|---|---|---:|
| `BMW_M3_E36_PAINT` | `render/shaders/bodywork.fx` | 4 |
| `BMW_M3_E36_BADGING` | `render/shaders/vehicles_basic.fx` | 2 |
| `GENERIC_WINDOWS` | `render/shaders/glass.fx` | 2 |
| `GENERIC_GLOSS_BLACK` | `render/shaders/vehicles_basic.fx` | 2 |
| `BMW_M3_E36_LIGHTSGLASS` | `render/shaders/glass.fx` | 2 |

Frame 30444 contains 28 draws using the exact runtime BMW body vertex stream
`0x27b39460`, stride 76 and `NumVertices=3550`. Twelve of those 28 draws carry a
unique set of BMT numeric parameter witnesses at the draw boundary:

| Material | PrimCount | VS / PS objects | Distinctive witnesses |
|---|---:|---|---|
| `GENERIC_GLOSS_BLACK` | 192 | `0x363f6288` / `0x363f5f88` | `fresnelFactor=0.42`, `maxSpecPower=8192` |
| `BMW_M3_E36_PAINT` | 2098, 2462 | `0x38105708` / `0x38105408` | `primerBasis`, `metalBasis`, `dirtBasis` exact vectors |
| `BMW_M3_E36_BADGING` | 50 | `0x379d0798` / `0x379d0498` | `fresnelFactor=0.15`, `maxSpecPower=100`, `globalSpecularFactor=1.5`, `globalEMapFactor=0.75` |
| `GENERIC_WINDOWS` | 204 | `0x368dcb00` / `0x368dc800` | `crackColour`, `dirtBasis`, `(0,0,3,5)`, `4`, `0.18`, `50`, `0.98` |
| `BMW_M3_E36_LIGHTSGLASS` | 28 | `0x368da700` / `0x368da400` | `crackColour`, `dirtBasis`, `(0,0,7,14)`, `25`, `0.01`, `100` |

Each witness is found in the vertex or pixel c-register bank reconstructed from
state immediately before the draw. The report records the observed register for
each witness; values which are not discriminative enough to identify a register
uniquely are intentionally omitted from the witness profile.

The paint material also has an exact static D3D9 sampler contract from the existing
material evidence: `diffuseTexture=s1`, `specularTexture=s2`,
`scratchControlTexture=s4`, with renderer-global `sShadowMap_f1_0=s0` and
`environmentMap=s3`. In the matched paint draws all five named slots have a
non-null runtime texture object pointer at the same draw boundary, and their
sampler state is preserved in the evidence.

## Gate

`bmw_m3_runtime_material_witness.py` emits
`SHIFT.BMWM3RuntimeMaterialWitness/1`.

The gate requires:

- 28 target draws for the exact BMW body stream;
- the expected six primitive triangle-count/index-buffer signatures;
- exactly 12 draw-local BMT matches with the expected per-material multiplicity;
- all recorded numeric witnesses present in the same draw state as the geometry;
- no substitution of frame-level state for the target draw;
- explicit separation of observed shader/texture object pointers from exact resource
  identity.

## Evidence boundary

This phase closes the **draw-local numeric material witness**. It does not claim:

- exact VS/PS byte or FXO permutation identity, because the text frame dump contains
  shader object pointers but not the raw created shader bytes;
- exact DDS identity for a runtime texture pointer, because the frame dump does not
  expose the backing resource path/hash for those objects;
- raw runtime VB/IB byte capture.

The phase is therefore a strict state-correlation checkpoint, not a final pixel-parity
claim.

## Regression coverage

The test suite checks frame-state parsing, per-material witness matching, rejection of
cross-draw correlation and hard failure of incomplete target-draw evidence.
