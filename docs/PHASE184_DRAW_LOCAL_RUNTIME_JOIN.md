# Phase 184 — Draw-local runtime shader/state correlation

## Goal

Close the remaining correlation gap between the strict D3D9 same-instance gate and
the downstream BMW shader/material pipeline.

Phase 183 made the same-instance gate draw-local, but downstream shader selection
and parity still consumed frame-level state. A frame can contain multiple indexed
draws with different declarations, shaders, constants, streams or textures, so
frame-level joins were still capable of combining evidence from different draws.

## Contract

`SHIFT.D3D9RuntimeBindingEvidence/1` draw snapshots now include:

- `frame`;
- `draw_index`;
- draw parameters;
- vertex declaration;
- stream sources;
- index binding;
- vertex/pixel shader binding;
- draw-local shader permutation identity;
- constant writes observed before the draw;
- texture bindings observed before the draw.

The shader permutation identity is computed from the shader objects that are bound
at the exact `DrawIndexedPrimitive` boundary.

## Downstream consumers

The following components now consume the same `(frame, draw_index)` state:

- `bmw_runtime_shader_join.py`;
- `bmw_runtime_shader_select.py`;
- `bmw_runtime_parity.py`;
- `bmw_vertex_input_parity.py`;
- `bmw_runtime_render_contract.py`;
- `bmw_runtime_golden_gate.py`.

When a runtime report contains draw snapshots, frame-level shader identity is never
used as a fallback for a draw-local state in that same frame. Reports produced
before the snapshot contract remain readable through the explicit legacy
frame-aggregate path, including mixed reports where only some frames contain
snapshots.

## Regression coverage

The test suite now contains negative cases where:

1. one draw uses the BMW MEB resource but another draw uses the BMW shader;
2. the frame-level aggregate contains a matching BMW shader identity while no
   individual draw contains both identities;
3. the render contract is selected by an exact draw index and must use that draw's
   constants and texture bindings.

These cases must remain blocked or resolve only on the exact draw snapshot.

## Evidence boundary

This phase does not claim a retail runtime capture. The remaining external gate is
still one authentic Need for Speed: SHIFT D3D9 capture containing the target BMW M3
body draw. That capture must provide the exact MEB resource identity, declaration,
indexed draw, VS/PS identity, constants and sampler resources on the same draw
instance before a runtime golden render can become ready.

## Test status

Intermediate Phase 184 commits have passed the repository Python/native/capture
producer CI paths. The final branch head must still be rechecked after the latest
fallback-hardening commits; no green result is inferred from an earlier commit.
