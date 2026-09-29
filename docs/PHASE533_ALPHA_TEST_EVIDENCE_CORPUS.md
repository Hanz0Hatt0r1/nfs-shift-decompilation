# Phase 533 — exact alpha-test evidence and BMT state corpus

Phase 533 closes the D3D9 side of fixed-function alpha testing and makes the
real material-state corpus reproducible. It deliberately does **not** enable a
Vulkan shader discard yet.

## Exact retail alpha-test state

The retail material loader and device application form a complete chain:

```text
BMT alphatestparams
  -> FUN_0083f960
  -> enabled
  -> D3DCMP lookup
  -> ROUND((BMT value / 255.0) * 255.0)
  -> FUN_00863500
  -> SetRenderState(15, enabled)
  -> SetRenderState(25, function)
  -> SetRenderState(24, reference_u8)
```

The D3D9 state IDs are therefore proven:

| State | ID |
|---|---:|
| D3DRS_ALPHATESTENABLE | 15 |
| D3DRS_ALPHAREF | 24 |
| D3DRS_ALPHAFUNC | 25 |

`SHIFT.MaterialAlphaTestContract/1` records the engine enum, exact D3D9
compare value, 8-bit reference and normalized reference. For the supplied
corpus, all observed alpha references are integral, so the recovered
round-to-u8 path is unambiguous.

## Why native execution is still blocked

D3D9 compares the incoming fragment alpha against an 8-bit reference before
subsequent framebuffer processing. The translated Vulkan GLSL exposes the final
pixel result as `fragColor0.a`, so a shader `discard` is mechanically
possible.

What is not yet proven is the exact D3D9 incoming-alpha quantization/comparison
behavior relative to the floating-point shader output. Phase 533 therefore
records the candidate output and threshold, but keeps
`alpha-test:fragment-alpha-quantization-unproven` as the only execution
blocker for otherwise-valid alpha-test state.

## Reproducible corpus scanner

The new command scans decoded BMTs directly from BFF archives:

```bash
python shift_importer.py bmt-render-state-corpus \
  path/to/vehicle_or_track_bffs ... out/bmt-render-state-corpus.json
```

It deduplicates by decoded payload SHA-256, aggregates render-state values, runs
each unique material through the current pipeline-state translator and reports
native blocking reasons without embedding raw game payloads.

## Attached-corpus observation

The supplied vehicle and Silverstone archives produced:

| Observation | Count |
|---|---:|
| render BFFs containing the scanned material corpus | 16 |
| BMT instances | 1,714 |
| unique decoded BMT payloads | 854 |
| duplicate instances | 860 |
| depth groups | 848 |
| alpha-blend groups | 848 |
| alpha-test groups / enabled alpha-test | 86 |
| depth test disabled | 6 |
| depth write disabled | 113 |
| blend enabled | 130 |
| decode errors | 0 |

Every observed alpha-test material uses `ETF_GREATER_THAN_OR_EQUAL`; 75 use
reference 64 and 11 use reference 128. This makes alpha-test the dominant
remaining fixed-function state blocker after Phase 532.

The machine-readable aggregate is
`evidence/bmt_render_state_corpus_summary.json`.

## Boundary

Phase 533 does not claim bit-exact Vulkan alpha-test parity, does not infer the
remaining unknown root BMT group, and does not assign stencil/bias semantics
without positive corpus/source evidence.
