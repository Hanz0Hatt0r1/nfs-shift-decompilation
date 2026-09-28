# SHIFT Decompilation Roadmap

This document tracks the current execution order. Detailed historical work is preserved in `docs/PHASE*.md`.

## Current milestone: specialized-provider runtime capture

**Mainline: Phase 500.**

Phases 499–500 make the specialized-provider capture directory self-describing:

- pre/post snapshots are indexed by provider id and hit;
- duplicate and missing stages are detected;
- pre snapshots define structural readiness;
- optional post snapshots enable reset→solve order analysis;
- scalar-reset events can be scoped by frame index;
- results are emitted as `SHIFT.SpecializedProviderCaptureBundleRuntime/1`;
- the verification CLI returns 0 for ready evidence and 2 for blocked evidence.

Exact retail/provider numeric parity remains open until a real runtime frame is captured.

## Immediate execution order

1. Restore a clean Python CI baseline by fixing the syntax error in `tools/run_specialized_provider_differential.py:131`.
2. Capture a real provider frame with the SDF/runtime probe.
3. Verify the provider bundle together with `scalar_reset_events.jsonl`.
4. Compare retail packed-workspace/output mutations with the source-derived provider programs.
5. Continue closing pre-PhysX construction boundaries without inventing SDK/provider class identities.
6. Expand the desktop reference renderer against real BMW material/shader permutations.
7. Complete Vulkan RenderCommand execution using the same neutral contract.
8. Continue SGB/FLAT and camera runtime reconstruction.
9. Derive proven animation poses from the BAB runtime grammar.
10. Port the stable native render/runtime boundary to Android.
11. Integrate gameplay/input/audio/streaming only after the core data and render/runtime contracts stabilize.

## Workstream status

| Workstream | State | Exit condition |
|---|---|---|
| BFF/XMem-LZX | verified | broader uncommon-variant coverage |
| Resource IR | active | remaining format-specific joins |
| MEB / vertex ABI | strong static | more runtime same-instance proofs |
| Material/shader linking | implemented | broader real permutation validation |
| Desktop renderer | active oracle | broader exact D3D9/material coverage |
| Skinning | contract implemented | runtime pose production |
| BAB animation | evidence-backed | resolve remaining semantic gaps |
| SGB scene | partial | deeper object/leaf consumers |
| Camera | active | higher-level behavior |
| Vehicle physics | active | runtime graph and force-law boundaries |
| Builtin solver | source-backed | runtime frame parity |
| Specialized providers | capture-ready | real capture + numeric differential |
| D3D9 capture | mature | more real same-instance evidence |
| Vulkan | active | full RenderCommand/material submission |
| Android | deferred | stable native renderer/runtime boundary |

## Canonical render path

`BFF → IR → VHF/MEB/BMT/DDS → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

The reference renderer and Vulkan backend consume the same neutral command/data contract.

## Runtime evidence path

`D3D9 producer → JSONL → draw-local snapshot → identity correlation → same-instance gate → parity`

For large captures:

`apitrace → unique BMW extraction → optional trim → payload proof`

## Physics path

`CDF/EDF/GDF/SDF → VehiclePhysicsAssetGraph/1 → construction → solver frame → provider/builtin → post-solve`

The provider branch is currently structurally reconstructed but numerically capture-gated.

## First native vehicle-slice definition

The first reproducible native slice requires:

- exact resource identity;
- deterministic material/shader selection;
- validated RenderCommand;
- deterministic reference output;
- Vulkan execution of the same command;
- explicit external renderer-global resources;
- no runtime dependency on original BFF parsing.

Physics equivalence is a separate workstream.
