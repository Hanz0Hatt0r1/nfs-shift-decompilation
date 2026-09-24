# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 49. Latest merged CI baseline: **193 passed, 2 skipped** in Python, plus successful native IR regression; the post-merge `main` CI is also green.

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
| Desktop reference renderer | geometry + material reference | DrawPacket/RenderCommand execution, DDS DXT/uncompressed decode, multi-sampler texture execution, deterministic shader IR subset and material constant payloads; full BMW shader coverage remains |
| Skinning | bind-pose verified contract | explicit SkinPose, CPU reference, GLES ABI, bind-pose equivalence check; animated pose decoding remains |
| BAB animation payload | evidence tooling | corpus fingerprints and byte-level differential analysis; keyframe grammar still unproven |
| SGB scene graph | later | one track section assembles from IR |
| Android runtime | later | renderer consumes IR without importer dependencies |

## Execution order

1. Keep CI green and preserve explicit evidence/regression coverage.
2. Finish exact MEB vertex declaration details, especially COLOR0/1 type and channel byte order, using real BMW bytes and runtime-equivalent references.
3. Validate selected generated shader permutations with an actual GLES compiler where the toolchain is available, then use the result as the RenderCommand submission gate.
4. Stabilize deterministic material execution: RenderCommand constant payloads, multi-sampler file/IR inputs, explicit external sampler requirements and reproducible shader-reference outputs.
5. Expand pixel-shader varying inputs beyond TEXCOORD0 using the already-recovered (usage,index) linkage, while preserving blockers for unsupported interpolation/semantic cases.
6. Complete deterministic static BMW reference rendering with real lighting/blend semantics and the external environment/shadow resources that the selected permutations actually consume.
7. Use explicit SkinPose + bind-pose checks to validate real skinned vehicle geometry, then connect proven animated data when BAB decoding is ready.
8. Reverse engineer BAB animation payload from multiple clips sharing one skeleton, using the corpus and byte-diff evidence tools.
9. Implement SGB scene semantics and track assembly after the vehicle path is stable.
10. Port the proven IR/render boundary to Android.
11. Only then expand into physics, input, camera, audio and gameplay systems.

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


## Phase 50 status

Phase 50 closes the stale phase-45 constant-payload change on the current phase-49 baseline and makes the payload authoritative for the deterministic shader-reference path. It also adds a reproducible CLI mechanism for supplying multiple DDS textures by D3D9 sampler register.

### Current milestone blocker

The project still does not claim a full real BMW M3 material render. The remaining gap is shader coverage and semantic inputs/resources: more pixel varyings, unsupported D3D9 opcodes/control flow, renderer-global samplers (such as environment/shadow), exact COLOR0/1 byte order, and eventually the complete lighting/blend model.
