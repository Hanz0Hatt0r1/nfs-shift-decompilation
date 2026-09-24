# Render pipeline stage: VHF -> MEB -> BMT -> FX/FXO

Добавлен `render_pipeline.py`, который строит `SHIFT.RenderBinding/1` поверх Android IR.

Пайплайн:
1. VHF node resource -> MEB.
2. MEB primitive material reference.
3. Legacy `.mtx` автоматически разрешается как `.bmt`.
4. BMT -> FX source -> все соответствующие FXO cache permutations.
5. `material_linker.py` выбирает совместимую FXO permutation по sampler set и восстанавливает D3D9 sampler registers.
6. VHF Matrix/parent hierarchy превращается в world 4x4 transform.
7. Результат сохраняет unresolved references вместо удаления.

На реальном BMW M3 E36 установлено: 162 MEB, 21 уникальный material alias и VHF содержит 162 render-resource references. Для bodywork FXO реальные CTAB sampler registers восстанавливаются (diffuse s1, specular s2, scratch s4); остальные renderer-global samplers остаются external/specialised.

Следующий критический слой: доказать точный vertex ABI и затем довести реальный material/shader render на golden BMW mesh. VS/PS semantic pairing и SHIFT.StaticDraw/1 уже реализованы.

## Vertex layout layer

MEB parsing now preserves exact `payload_offset`, `stride` and payload byte count for every vertex property. `vertex_layout.py` converts those properties into `SHIFT.VertexLayout/1` Android-neutral attributes. FLOAT3/FLOAT2/FLOAT4 and UBYTE4 storage are established from the decoder; MEB color properties 460/461 remain explicitly ambiguous between D3D9 `D3DCOLOR` and `UBYTE4N` until byte-order behavior is proven.

`render_pipeline.py` now places this vertex layout beside every draw packet and passes the MEB properties into VS selection.

## Phase 11: vertex ABI evidence

SHIFT.VertexLayout/1 now carries an explicit abi_status per attribute (proven, inferred, ambiguous, unknown) plus a human-readable evidence basis. The layout also reports semantic collisions instead of silently collapsing multiple MEB properties onto one semantic key.

StaticDraw/1 now blocks an ambiguous vertex ABI only when the selected shader actually consumes that property. This prevents an unused ambiguous color field from blocking unrelated draws while preventing a renderer from silently choosing RGBA/BGRA or another unresolved declaration form.

## Phase 18: RenderBinding -> StaticDraw

`render_pipeline.py` now normalizes every VHF/MEB packet into the same mesh shape consumed by `SHIFT.StaticDraw/1`, including `SHIFT.VertexLayout/1`. It also emits a parallel `static_draws` array with explicit `ready` and `blocking_reasons` state.

This makes the render-link stage an actual renderer contract boundary instead of a separate diagnostic report.
## Phase 32: RenderResources integration

`SHIFT.RenderBinding/1` now includes `SHIFT.RenderResources/1` built from the same manifest rows and material texture bindings used by the render-link stage. Texture identity, sampler state, capability blockers and binding readiness therefore come from one shared resource plan.
## Phase 33: neutral RenderCommand

`render_command.py` converts validated `SHIFT.StaticDraw/1` plus `SHIFT.RenderResources/1` into `SHIFT.RenderCommand/1`: vertex attribute locations, index ranges, linked GLSL stages, uniform bindings and per-texture resource IDs are preserved without calling GLES.
## Phase 34: RenderCommand validation gate

`render_command.py` now exposes `SHIFT.RenderCommandValidation/1` and uses it as the final submission gate. Vertex attribute locations/ranges, index ranges, linked GLSL sources, resource-plan shape, material uniform bindings and constant register ranges are validated before `ready=true` is emitted.

## Phase 35: RenderCommand -> reference renderer

The desktop oracle can now execute `SHIFT.RenderCommand/1` directly. The execution path performs final command validation and cross-checks vertex/index metadata against the supplied neutral mesh before rasterization, closing the neutral submission chain without introducing BFF/runtime dependencies.

## Phase 37: explicit GLES vertex attribute ABI

`SHIFT.RenderCommand/1` now includes `attribute_setup` metadata for the future GLES backend. FLOAT32x2/3/4 uses `glVertexAttribPointer`; property 580 / BLENDINDICES0 uses integer `glVertexAttribIPointer` with `UNSIGNED_BYTE`; color 460/461 remains normalized byte input with its unresolved channel-order evidence preserved.

## Phase 39: RenderCommand shader validation

`RenderCommand/1` can now optionally run the linked VS/PS compiler validator. The result is preserved as `SHIFT.RenderCommandShaderValidation/1`; a proven `invalid` result blocks submission, while `unavailable` keeps the command usable for environments without the compiler toolchain.


## Phase 45: current renderer baseline

The neutral render pipeline now includes RenderResources/1, RenderCommand/1 validation, explicit GLES vertex-attribute setup, optional GLES shader compile/link evidence, direct desktop RenderCommand execution, DDS texture reference sampling, embedded sampler state and multi-texture sampler-register validation. The remaining material-render gap is shader operation execution, not resource discovery or command construction.


## Phase 46: shader execution reference

The project now has a deterministic software execution oracle for a bounded set of D3D9 shader IR operations. The reference renderer can therefore advance from texture sampling toward material evaluation without inventing unsupported shader behavior; full BMW shader coverage still requires expanding the supported opcode/control-flow set and validating against real FXO programs.


## Phase 47: shader IR carried into RenderCommand

`SHIFT.RenderCommand/1` now preserves the already-recovered `SHIFT.ShaderProgram/1` IR for both vertex and pixel stages when available, alongside the generated GLSL and linkage metadata. Backend implementations can therefore execute or inspect the same instruction IR without reparsing GLSL text.


## Phase 50: material execution contract

`SHIFT.MaterialConstantPayload/1` is now part of `SHIFT.RenderCommand/1` when numeric material constants are present. The payload is packed into deterministic 16-byte D3D9-style c-register slots at GLES UBO binding 14; unproven matrix orientation, non-float types, register conflicts and overflow remain explicit blockers.

The desktop shader reference consumes the same payload instead of reconstructing values from the higher-level uniform binding. The CLI now accepts repeatable `--texture-binding SLOT=PATH` arguments, so multi-sampler shader evidence can be reproduced from files without Python-only setup. The legacy single `--texture` path maps to the first material/shader sampler rather than assuming s0.
