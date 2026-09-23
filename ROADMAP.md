# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 31. Latest full CI baseline: **150 passed, 2 skipped** in Python, plus successful native IR regression.

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
| Exact vertex packing | mostly proven | deterministic locations/stride/ABI evidence and collision guards; color 460/461 declaration/channel order remains ambiguous |
| BMT -> FX -> FXO | implemented selection path | deterministic permutation selection, CTAB sampler/uniform linkage, linked GLSL payload |
| Shader backend | active | target BMW permutations compile in the selected GLES profile |
| DrawPacket | implemented contract | canonical DrawPacket carries StaticDraw readiness and explicit blockers |
| Desktop reference renderer | deterministic geometry oracle | DrawPacket→StaticDraw path, submesh ranges, golden SHA-256 baseline; full material/shader rendering remains |
| Skinning | bind-pose verified contract | explicit SkinPose, CPU reference, GLES ABI, bind-pose equivalence check; animated pose decoding remains |
| BAB animation payload | evidence tooling | corpus fingerprints and byte-level differential analysis; keyframe grammar still unproven |
| SGB scene graph | later | one track section assembles from IR |
| Android runtime | later | renderer consumes IR without importer dependencies |

## Execution order

1. Keep CI green and preserve explicit evidence/regression coverage.
2. Finish exact MEB vertex declaration details, especially COLOR0/1 type and channel byte order.
3. Validate selected generated shader permutations with an actual GLES compiler where the toolchain is available.
4. Complete deterministic static BMW reference rendering with real material/texture execution.
5. Use explicit SkinPose + bind-pose checks to validate real skinned vehicle geometry.
6. Reverse engineer BAB animation payload from multiple clips sharing one skeleton, using the corpus and byte-diff evidence tools.
7. Implement SGB scene semantics and track assembly after the vehicle path is stable.
8. Port the proven IR/render boundary to Android.
9. Only then expand into physics, input, camera, audio and gameplay systems.

## Evidence rules

- A parser result is not considered verified merely because it is syntactically
  plausible.
- Ambiguous fields remain explicitly marked as unknown/inferred until supported by
  multiple samples or runtime-equivalent evidence.
- Candidate shader permutations must not be selected by incidental file order.
- Regression fixtures should cover both positive resolution and unresolved/ambiguous
  cases.
