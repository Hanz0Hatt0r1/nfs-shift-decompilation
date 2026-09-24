# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 52. Latest documented full CI baseline: **193 passed, 2 skipped** in Python, plus successful native IR regression.

The immediate target is a deterministic pipeline:

`BFF -> IR -> VHF/MEB/BMT/DDS -> shader permutation -> DrawPacket -> renderer`

The milestone is complete when a real BMW M3 asset can be rendered without reading
the original BFF archives at runtime.

### Workstream status

| Workstream | State | Exit criterion |
|---|---|---|
| BFF/XMem-LZX | verified | native and Python paths agree on regression fixtures |
| Resource IR | active/verified | manifest + content-addressed blobs + typed analysis |
| BAS skeleton | verified parser | hierarchy/transforms covered by fixtures |
| BAB bone table | verified parser | bone table + conservative opaque animation tail |
| BAB <-> BAS linkage | implemented | deterministic bone mapping and diagnostics |
| MEB vertex semantics | verified for known BMW samples | semantic usage/index mappings covered by tests |
| Exact vertex packing | mostly proven | deterministic locations/stride/ABI evidence and collision guards; color 460/461 declaration/channel order remains explicitly ambiguous with candidate tooling |
| BMT -> FX -> FXO | implemented selection path | deterministic permutation selection, CTAB sampler/uniform linkage, linked GLSL payload |
| Shader backend | active/validated | selected LinkedShaderPair stages can be compile/link-checked with `glslangValidator`; unsupported toolchains report `unavailable` |
| DrawPacket | implemented contract | canonical DrawPacket carries StaticDraw readiness and explicit blockers |
| Desktop reference renderer | geometry + shader-reference oracle | DrawPacket/RenderCommand execution, DDS DXT/uncompressed decode, multi-sampler textures, TEXCOORD0..4 plus normal/tangent/binormal inputs, and bounded VS/PS IR execution; shader/global-resource coverage remains incomplete |
| Skinning | bind-pose verified contract | explicit SkinPose, CPU reference, GLES ABI, bind-pose equivalence check; animated pose decoding remains |
| BAB animation payload | evidence tooling | corpus fingerprints and byte-level differential analysis; keyframe grammar still unproven |
| SGB scene graph | later | one track section assembles from IR |
| Android runtime | later | renderer consumes IR without importer dependencies |

## Execution order

1. Keep CI green and preserve explicit evidence/regression coverage.
2. Finish exact MEB vertex declaration details, especially COLOR0/1 type and channel byte order, using real BMW bytes and runtime-equivalent references.
3. Validate selected generated shader permutations with an actual GLES compiler where the toolchain is available, then use the result as the RenderCommand submission gate.
4. Finish the material execution boundary: serialize CTAB float/vector constants into deterministic RenderCommand payloads and make the reference renderer consume that exact payload.
5. Execute the embedded VS before PS in the desktop reference path and link varyings by semantic key while preserving explicit blockers for unresolved vertex ABI.
6. Expand reference execution toward real BMW permutations: COLOR0/1 exact packing, TEXCOORD5+ families, blend indices/weights, renderer-global samplers, remaining D3D9 relative addressing/control flow and exact shader math must be evidence-backed, not guessed.
7. Resolve the remaining COLOR0/COLOR1 byte-order/type ambiguity and prove the exact MEB vertex declaration for real BMW meshes.
7. Complete deterministic static BMW reference rendering with real lighting/blend semantics and all required external resources.
8. Use explicit SkinPose + bind-pose checks to validate real skinned vehicle geometry.
9. Reverse engineer BAB animation payload from multiple clips sharing one skeleton, using the corpus and byte-diff evidence tools.
10. Implement SGB scene semantics and track assembly after the vehicle path is stable.
11. Port the proven IR/render boundary to Android.
12. Only then expand into physics, input, camera, audio and gameplay systems.

## Evidence rules

- A parser result is not considered verified merely because it is syntactically
  plausible.
- Ambiguous fields remain explicitly marked as unknown/inferred until supported by
  multiple samples or runtime-equivalent evidence.
- Candidate shader permutations must not be selected by incidental file order.
- Regression fixtures should cover both positive resolution and unresolved/ambiguous
  cases.


## Phase 44: renderer submission baseline

The neutral renderer path now spans `RenderBinding/1 -> StaticDraw/1 -> RenderResources/1 -> RenderCommand/1 -> desktop reference renderer`. RenderCommand validates vertex ABI, index ranges, shader-source presence, uniform/constant ranges and multi-texture sampler-register/state integrity. The desktop oracle can execute geometry-only and UV0 texture reference paths, while the shader backend can compile/link selected GLES shader pairs when the validator is installed.

## Current blocker for the BMW milestone

The project does **not** yet claim a full real BMW M3 material render. Remaining work is the semantic execution of generated shader code: material constants, multiple texture reads and shader operations must be mapped into a deterministic reference evaluator (and later GLES/Vulkan execution) without inventing undocumented behavior.


## Phase 50-51 baseline

Phases 50 and 51 are already merged on `main`: the shader-backed reference renderer accepts multiple sampler-register texture images and maps `TEXCOORD0..4` to MEB UV layers 130..134. Missing sampler images and missing required UV layers remain explicit execution errors.

## Phase 52: material constant payload

Phase 52 adds `SHIFT.MaterialConstantPayload/1` as the deterministic bridge from `SHIFT.MaterialUniformBinding/1` into the renderer submission contract. Proven float/vector values are packed into 16-byte D3D9-style c-register slots; matrix orientation, non-float types, register conflicts and overflow remain blocking rather than guessed.

The reference shader executor consumes the serialized payload when it is present, keeping the software oracle aligned with the exact RenderCommand data that a future GLES backend will upload.


## Phase 54: vertex-shader reference execution

The desktop reference path now has an explicit VS->PS execution boundary: the embedded vertex ShaderProgram/1 executes against the known MEB semantic inputs, its POSITION output drives clip-space rasterization, and VS outputs are matched to pixel inputs by semantic key before perspective-correct interpolation. The next rendering gap is expanding the proven vertex/material ABI without guessing unresolved MEB COLOR bytes, additional TEXCOORD families or renderer-global resources.


## Phase 55: alternate MEB TEXCOORD family

Phase 55 closes the known 230..234 UVW semantic gap across the desktop renderer and standalone vertex adapter. The next execution milestone is the proven skin-input path (`BLENDWEIGHT0`/`BLENDINDICES0`) or the unresolved COLOR0/1 channel-order/type evidence, followed by renderer-global samplers and the remaining shader control-flow/lighting surface.


## Phase 56: proven skin input semantics

Phase 56 wires MEB 310/580 into the integrated VS reference path. The next rendering/vehicle step is to resolve COLOR0/1 exact type/channel order and then prove the minimal SkinPose adapter that can transform a vertex using known bone weights/indices without conflating that with BAB animation decoding.
