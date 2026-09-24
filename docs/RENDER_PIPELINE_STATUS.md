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


## Phase 48-51: shader-backed reference progression

The desktop reference path now executes embedded pixel `SHIFT.ShaderProgram/1` IR for a bounded opcode subset, accepts multiple D3D9 sampler registers through explicit reference images, and maps `TEXCOORD0..4` by semantic index onto MEB UV properties `130..134`. This closes the texture/sampler/UV gaps without assuming file order or sampler 0.

## Phase 52: material constant payload

`RenderCommand/1` now carries `SHIFT.MaterialConstantPayload/1` whenever a material has reflected numeric constants. The payload preserves 16-byte c-register slots and upload offsets in one deterministic contract; the shader-reference path reads the same serialized slots rather than rebuilding material values from higher-level metadata.

The project still does not claim a complete real BMW material render. Remaining blockers include exact COLOR0/COLOR1 declaration and byte order, renderer-global external samplers (notably environment/shadow), unsupported D3D9 relative addressing/control flow and the complete lighting/blend model.


## Phase 54: vertex-shader reference execution

The reference renderer can now execute an embedded vertex ShaderProgram/1 before the pixel stage. POSITION0/POSITIONT0 and the currently proven MEB semantics are sourced into declared D3D9 vertex registers; outputs are linked to pixel inputs by semantic (usage,index), not physical register number; and VS-produced varyings use perspective-correct interpolation.

This closes the architectural VS->PS gap while keeping the reference ABI explicit. COLOR0/1 channel type/order, TEXCOORD5+, blend indices/weights, renderer-global resources and the remaining D3D9 control-flow/addressing cases stay outside the claimed deterministic material-render surface.


## Phase 55: alternate MEB TEXCOORD family

The desktop reference renderer and standalone vertex-reference adapter now accept either MEB UV family `130..134` (FLOAT32x2) or `230..234` (FLOAT32x3) for semantic `TEXCOORD0..4`. The 230-family is passed through with its third component available to shader code. When both families for the same semantic are present, rendering is blocked to avoid guessing the source declaration.


## Phase 56: skin input semantics

The desktop VS reference boundary now consumes MEB 310/580 as `BLENDWEIGHT0`/`BLENDINDICES0` inputs when a vertex ShaderProgram declares them. Both are passed through unchanged at semantic level (indices widened to numeric float4 for the shader register), with missing attributes treated as hard errors. No skin deformation is performed yet.


## Phase 57: explicit external sampler resources

Renderer-global/specialized sampler requirements are now a first-class RenderCommand field. The deterministic reference path can bind external `sampler2D` resources by D3D9 sampler register and validates the declared sampler type before execution. The CLI exposes repeatable `--external-texture-binding SLOT=PATH` inputs. Environment `samplerCube` resources remain a dedicated future milestone.


## Phase 58: cube-map external resources

`environmentMap → s3` can now be supplied to the deterministic reference renderer as an explicit six-face cube resource. The resource contract validates all six faces and identical dimensions before lookup; the embedded shader sampler type must agree with the RenderCommand external sampler declaration. This removes the previous need to treat samplerCube as an automatic blocker while still keeping source DDS cubemap ingestion as a separate task.


## Phase 59: native DDS cubemap decode

The texture reference layer can now ingest complete six-face DDS cubemaps directly. Base-level images are decoded with the same DXT1/DXT3/DXT5 or 32-bit uncompressed path already used for 2D textures, while mip levels are skipped deterministically to reach each next cube face. The result feeds the phase-58 samplerCube contract without inventing per-face source files.


## Phase 60: skinned mesh CPU reference

The skinning stack now has an explicit mesh-level reference contract: `SHIFT.SkinnedDraw/1` + `SHIFT.SkinPose/1` → `SHIFT.SkinnedMeshReference/1`. Four-influence POSITION deformation and direction-stream transformation are covered independently from BAB animation decoding. The next integration step is to feed this transformed mesh into the same VS→PS reference raster path used by static DrawCommand execution.


## Phase 61: skinned reference render

The desktop renderer now has a dedicated `render_skinned_draw_reference()` entry point. It consumes a ready SkinnedDraw, materializes `SHIFT.SkinnedMeshReference/1`, then uses the same geometry/raster contract as StaticDraw. This is the bridge needed before adding skinned VS/PS shader execution on top of the transformed mesh.


## Phase 62: skinned VS→PS reference

The desktop reference pipeline now supports `SkinPose → SkinnedMeshReference → embedded VS → semantic varying linkage → PS → raster`. This is the first combined skin/material reference surface. RenderCommand serialization and production material permutation selection remain separate next steps.


StaticDraw and SkinnedDraw now converge on the same RenderCommand/1 resource/shader validation boundary; skinned commands additionally carry an explicit SkinPose/palette payload. This keeps future GLES skinning upload logic independent from the importer and consistent with the desktop reference.


## Phase 64: RenderCommand to GLES skinning

The common submission ABI now reaches the GLES skinning contract directly: `SkinnedDraw → RenderCommand/1 → GLES31Skinning/1`. This removes the need for Android runtime code to reconstruct skin attributes or pose metadata from higher-level packets.


## Phase 65: explicit extended semantic streams

The reference pipeline now distinguishes two states: fixed MEB-backed semantics (for example TEXCOORD0..4) and explicit semantic streams supplied by an evidence producer. This allows shader-proven `TEXCOORD5` to be tested end-to-end without claiming that an unknown MEB property id has been decoded.


## Phase 66: COLOR evidence

The render pipeline now has a reproducible command for COLOR0/1 candidate comparison. This is intentionally upstream of RenderCommand readiness: the evidence report can demonstrate a candidate match, while the runtime ABI remains ambiguous until the project records a verified declaration/order.


## Phase 67: COLOR evidence ingestion

The render investigation now has a canonical MEB JSON → ColorABIEvidence/1 path. This keeps the evidence workflow tied to the same decoder output consumed by RenderCommand rather than a separately prepared byte dump.


## Phase 68: direct COLOR evidence ingestion

COLOR ABI analysis is now anchored to the decoded `.meb` resource itself instead of a manually extracted binary stream. The resulting evidence report preserves both channel-order candidates and the source resource identity, but does not alter RenderCommand readiness.


## Phase 69: COLOR corpus gate

COLOR evidence can now be aggregated across decoded MEB samples. The corpus layer is intentionally upstream of RenderCommand readiness: it reports stability but does not promote a declaration or channel order.


## Phase 70: corpus COLOR evidence

The evidence pipeline now supports BFF-directory scale ingestion: `.bff` → `.meb` → 460/461 → `ColorABIEvidence/1` → `ColorABICorpusEvidence/1`. Runtime readiness remains unaffected until an external declaration/order proof is established.
