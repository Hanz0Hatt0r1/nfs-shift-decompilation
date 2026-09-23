# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 10. The current CI baseline is 107 passed, 2 skipped in Python, plus successful native IR regression.

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
| BAB <-> BAS linkage | active | deterministic bone mapping and diagnostics |
| MEB vertex semantics | verified for known BMW samples | semantic usage/index mappings covered by tests |
| Exact vertex packing | active | deterministic storage/stride plus explicit evidence states; remaining ambiguity is isolated and render-blocking when consumed |
| BMT -> FX -> FXO | active | deterministic VS/PS + sampler permutation per material |
| Shader backend | active | target BMW permutations compile in the selected GLES profile |
| DrawPacket | active | all target packets carry proven layout/material/shader bindings |
| Desktop reference renderer | geometry oracle | neutral geometry renderer exists; full material/shader render remains the milestone |
| Skinning | foundation | explicit skin pose + CPU reference + GLES contract exist; bind-pose/animation evaluation remains |
| BAB animation payload | later | clip/keyframe grammar proven on multiple samples |
| SGB scene graph | later | one track section assembles from IR |
| Android runtime | later | renderer consumes IR without importer dependencies |

## Execution order

1. Keep CI green and add regression fixtures before changing semantics.
2. Finish exact vertex stream packing, especially ambiguous MEB property types.
3. Make FXO permutation selection deterministic and evidence-producing.
4. Validate generated shaders with an actual GLES compiler.
5. Build a minimal desktop reference renderer for the BMW M3.
6. Connect MEB blend weights/indices to BAS/BAB skeletons and verify bind pose.
7. Reverse engineer BAB animation payload using several clips sharing one skeleton.
8. Implement SGB scene assembly after vehicle rendering is stable.
9. Port the proven renderer/IR boundary to Android.
10. Only then expand into physics, input, camera, audio and gameplay systems.

## Evidence rules

- A parser result is not considered verified merely because it is syntactically
  plausible.
- Ambiguous fields remain explicitly marked as unknown/inferred until supported by
  multiple samples or runtime-equivalent evidence.
- Candidate shader permutations must not be selected by incidental file order.
- Regression fixtures should cover both positive resolution and unresolved/ambiguous
  cases.
