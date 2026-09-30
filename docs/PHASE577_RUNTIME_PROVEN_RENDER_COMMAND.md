# Phase 577 — runtime-proven RenderCommand provenance

Phase 576 joins a runtime-proven shader admission back to the exact IMB
resource primitive and rebuilds its complete MaterialBinding. Phase 577 carries
that proof across the renderer-neutral ABI so native-scene packaging can
distinguish genuinely runtime-proven draws from merely statically unique draws.

## Contract

The new per-submesh provenance contract is:

`SHIFT.RuntimeProvenDraw/1`.

It is emitted only when the source DrawPacket submesh contains an applied
Phase 576 runtime shader admission.

No provenance object is synthesized for ordinary MEB/IMB draws that happen to
have `selection_status=unique`.

## StaticDraw boundary

`build_static_draw_contract()` now preserves, for an admitted IMB primitive:

- Phase 574 binding index;
- IMB source kind;
- exact resolved resource path;
- source archive;
- decoded IMB SHA identity;
- primitive index;
- exact first/index/primitive counts;
- runtime material-selection source/status;
- Phase 575 runtime-selection readiness;
- the selected runtime variant evidence.

The contract explicitly keeps:

`render_backend_admission = false`.

It proves the origin of the shader/material selection, not Vulkan readiness.

## RenderCommand boundary

`build_render_command()` carries the same provenance unchanged into the
corresponding command submesh and records:

`runtime_proven_draw_count`.

The RenderCommand validator now fail-closes provenance when:

- the provenance format/status is wrong;
- source kind is not IMB;
- exact resource path/SHA identity is missing;
- the binding index is invalid;
- shader selection is not unique;
- selection source is not `runtime-admission`;
- Phase 575 runtime selection was not ready;
- provenance draw range differs from the actual RenderCommand draw range.

This prevents a stale/tampered provenance sidecar from converting an unrelated
draw into a runtime-proven native candidate.

## Why this phase exists

Before Phase 577, the renderer command contained the resulting exact shaders
but not the evidence chain that made those shaders admissible.

A later native scene bundle could therefore see only:

`unique shader + ready RenderCommand`

and could not distinguish:

- static uniqueness;
- runtime-proven Silverstone attribution.

Phase 577 makes that distinction explicit and machine-readable.

## Regression coverage

The regression suite proves:

- runtime admission produces `SHIFT.RuntimeProvenDraw/1`;
- ordinary unique material selection produces no runtime provenance;
- provenance survives StaticDraw → RenderCommand;
- exact IMB identity and primitive index survive;
- tampered draw ranges block RenderCommand;
- replacing `runtime-admission` with `static-ranking` blocks RenderCommand.

## Next

Build `SHIFT.NativeSceneBundle/1` from only ready RenderCommand submeshes whose
`runtime_provenance.format == "SHIFT.RuntimeProvenDraw/1"` and status is
`proven`.

The native scene bundle should preserve:

- scene draw order;
- world matrix;
- exact IMB resource/primitive identity;
- runtime shader admission identity;
- RenderCommand shader/provenance hashes;
- child Vulkan bundle path/hash.

Unproven scene primitives must remain outside the native bundle rather than
being silently promoted.

The future packager must also re-run the normal RenderCommand/native submission
gates; `RuntimeProvenDraw/1` is necessary evidence, not a substitute for
geometry, shader, texture, pipeline-state or SPIR-V readiness.
