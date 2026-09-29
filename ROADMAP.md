# SHIFT Decompilation Roadmap

This document tracks the current execution order. Detailed historical work is preserved in `docs/PHASE*.md`.

## Current milestone: specialized-provider runtime capture

**Current mainline: Phase 532.**



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

1. Python CI baseline after the `src` reorganization — complete; Phase 504 mainline CI is green; Phase 505 is the current source/control-flow extension.
2. Capture a real provider frame with the SDF/runtime probe — preflight implemented; live capture remains the next evidence gate.
3. Verify the provider bundle together with `scalar_reset_events.jsonl`.
4. Cross-vehicle raw BFF payload parity and deduplicated FXO shader profiling — complete.
5. Corpus-driven shader opcode gap analysis — complete.
6. Cross-path content-addressed raw payload reuse audit — implemented as `SHIFT.BFFRawPayloadReuseAudit/1`.
7. Propagate FXO/resource provenance into `RenderCommand/1` and add `SHIFT.NativeSubmissionGate/1` for native execution — complete, including persisted gate enforcement in Python/C++.
8. Extend runtime BMW shader join/render contracts with explicit VS/PS/pair byte-hash differentials — implemented.
9. Join provider dispatch/selector/execution/source-shape evidence into the capture handoff contract — implemented as `SHIFT.SpecializedProviderCaptureHandoffRuntime/1`.
10. Compare retail packed-workspace/output mutations with the source-derived provider programs — implemented as `SHIFT.SpecializedProviderCaptureSourceMutationCorrelation/1`.
11. Continue closing pre-PhysX construction boundaries without inventing SDK/provider class identities — Phase 502 cross-contract validator and Phase 503 BFF-to-handoff orchestration are complete.
12. Validate the runtime capture host before attempting GDB attachment — Phase 504 preflight implemented.
13. Close the IGPhaseVehicle participant creation/load gate before runtime capture — Phase 505 implemented.
14. Map the PhysicsParticipantManager event-0x20 ingestion path without overclaiming its join to the selector registry — Phase 506 implemented.
15. Map the PhysicsParticipantManager participant slot allocation/registration/update bridge used by PhysicsParticipant.cpp — Phase 507 implemented.
16. Resolve the IGPhaseVehicle selector object and keep its global identity separate from DAT_00c109e0 until a join is proven — Phase 508 implemented.
17. Trace the selected participant pointer/ordinal through IGPhaseVehicle processing, reselection and vehicle-BFF writeback — Phase 509 implemented.
18. Close the selector descriptor/candidate lifecycle: constructor defaults, +0x74 eligibility/exclusion state, +0x8c ordinal writeback, bounded batch reservation and distinct +0x1d post-load/process state — Phase 510 implemented.
19. Close the IGPhaseVehicle completion/finalization boundary: per-container callbacks, guarded +0x160 cleanup, resource teardown and post-finalizer object callback ordering — Phase 511 implemented.
20. Map selector descriptor population exactly: 16-entry capacity, 0x90 stride, packed token bitfields, source-to-descriptor string/block copies, +0x74 initialization and conditional +0x70 population — Phase 512 implemented.
21. Close selector source-record admission scheduling: owner +0x4f0 mask, low-nibble routing key, descriptor-population handoff and reset/resynchronization paths — Phase 513 implemented.
22. Validate the low-stop specialized-provider capture contract — Phase 515 implemented.
23. Validate concrete AIW runtime edge coverage, stride and ambiguity without collapsing candidate mappings — Phase 516 implemented.
24. Join recovered `Path.StartNode` pointers directly to `AIPolylinePath.array` and compare node counts/sequences — Phase 517 implemented.
25. Decode proven FLAT direct-record object handle/index links — Phase 518 implemented.
26. Map proven FLAT runtime index-table geometry — Phase 519 implemented.
27. Map the SGB NODE runtime wrapper created by `FUN_006a4b40` — Phase 520 implemented.
28. Record the source-backed SGB HIERARCHY serialized-child → runtime-element copy layout — Phase 521 implemented.
29. Classify the concrete SGB OBJECT/HIERARCHY/DAMAGE runtime wrappers — Phase 522 implemented.
30. Map the SGB SUMM runtime wrapper and exact source/runtime field copies — Phase 523 implemented.
31. Stabilize and merge the offline Linux native runtime frame loop/material boundary — complete; `native_runtime/` is on main, depth-tested and covered by Linux Vulkan CI.
32. Represent one multi-submesh RenderCommand as an ordered set of independently gated Vulkan bundles — Phase 524 implemented.
33. Compile, reflect and interface-validate every ordered draw bundle before native admission — Phase 525 implemented.
34. Execute the prepared draw set in one native render pass with per-draw pipelines, constants, descriptors, textures and geometry — Phase 526 implemented.
35. Adapt complete BMW material slices into the multi-draw set with independent per-submesh DDS/resource provenance — Phase 527 implemented.
36. Remove the paint-only BMW material-slice restriction and gate every selected primitive through a generic exact FXO/pair/permutation contract — Phase 528 implemented.
37. Join independently ready BMW primitive slices into one canonical revalidated multi-submesh RenderCommand and feed it into the material/DDS multi-draw adapter — Phase 529 implemented.
38. Propagate the retail BMT cull enum through RenderCommand and atomic bundle sidecars into both native Vulkan consumers — Phase 530 implemented.
39. Recover stable real-BMT depth/alpha group and field IDs, enum indices, alpha-test normalization, and carry them through the neutral render IR without enabling unproven native state — Phase 531 implemented.
40. Map proven retail depth/default/blend semantics into one fail-closed pipeline-state sidecar and execute them independently per draw in both native Vulkan consumers — Phase 532 implemented.
41. Run the canonical non-paint BMW body primitives against the retail BMW/RENDER corpus and admit the first distinct fully-ready permutations into the native multi-draw set.
42. Close enabled alpha-test, bias and stencil only from additional source/runtime evidence.
43. Expand the desktop reference renderer against real BMW material/shader permutations.
43. Continue SGB/FLAT and camera runtime reconstruction.
44. Derive proven animation poses from the BAB runtime grammar.
45. Port the stable native render/runtime boundary to Android.
46. Integrate gameplay/input/audio/streaming only after the core data and render/runtime contracts stabilize.

## Workstream status

| Workstream | State | Exit condition |
|---|---|---|
| BFF/XMem-LZX | verified | broader uncommon-variant coverage |
| Resource IR | active | remaining format-specific joins |
| MEB / vertex ABI | strong static | more runtime same-instance proofs |
| Material/shader linking | generalized BMW intake + typed BMT depth/alpha/cull IR | retail non-paint permutation validation and proven native state mapping |
| Desktop renderer | active oracle | broader exact D3D9/material coverage |
| Skinning | contract implemented | runtime pose production |
| BAB animation | evidence-backed | resolve remaining semantic gaps |
| SGB scene | partial | deeper OBJECT/HIERARCHY/FLAT leaf consumers |
| Camera | active | higher-level behavior |
| Vehicle physics | active | runtime graph, participant gate, manager event path, participant registry/update bridge, selector-context separation, participant process/reselection, selector candidate lifecycle, IGPhaseVehicle finalization, selector descriptor population, source-record admission scheduling and force-law boundaries; BFF-to-pre-PhysX handoff implemented |
| Builtin solver | source-backed | runtime frame parity |
| Specialized providers | capture-ready | real capture + numeric differential; source-mutation, pre-PhysX handoff, participant-manager event, selector-context separation, participant process/reselection and selector-candidate lifecycle layers implemented |
| D3D9 capture | mature | more real same-instance evidence |
| Track/path runtime correlation | active | runtime graph capture with complete/unambiguous edge evidence |
| Vulkan | active; BMW material multi-draw + source-backed cull/depth/blend | retail non-paint permutations, alpha-test/bias/stencil evidence |
| Android | deferred | stable native renderer/runtime boundary |

## Canonical render path

`BFF → IR → VHF/MEB/BMT/DDS → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

The reference renderer and Vulkan backend consume the same neutral command/data contract.

## Runtime evidence path

`D3D9 producer → JSONL → draw-local snapshot → identity correlation → same-instance gate → parity`

For large captures:

`apitrace → unique BMW extraction → optional trim → payload proof`

## Physics path

`CDF/EDF/GDF/SDF → VehiclePhysicsAssetGraph/1 → participant gate → construction → solver frame → provider/builtin → post-solve`

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
