# SHIFT Decompilation Roadmap

This document tracks the current execution order. Detailed historical work is preserved in `docs/PHASE*.md`.

## Current milestone: specialized-provider runtime capture

**Current mainline: Phase 581.**



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
41. Orchestrate all canonical BMW body primitives independently, preserve partial ready evidence, group exact shader permutations and feed the admitted subset into the existing multi-draw adapter — Phase 533 implemented.
42. Collapse byte-identical duplicate BMW/Cockpit shader resources and scope retail FXO enumeration to the selected BMT shader family before permutation ranking — Phase 536 implemented.
43. Execute the normalized retail BMW_M3_E36/Cockpit/RENDER corpus, collapse identical top-ranked bytecode identities and persist exact remaining blockers — Phase 537 implemented.
44. Build a per-primitive runtime shader target set from every statically tied top-rank permutation/pair/hash without selecting one — Phase 538 implemented.
45. Match the Phase 538 target set against exact MEB identity, indexed draw ranges and same-instance D3D9 shader hashes — Phase 539 implemented.
46. Prefilter raw D3D9 JSONL by target shader byte hashes and canonical draw ranges before full runtime reconstruction — Phase 540 implemented.
47. Apply archive content-identity deduplication to downstream retail material-slice BMT/MEB/FX/DDS lookup — Phase 541 implemented.
48. Capture one real BMW M3 body frame with the existing D3D9 producer and close the concrete retail FXO permutation attribution.
49. Close enabled alpha-test, bias and stencil only from additional source/runtime evidence.
50. Expand the desktop reference renderer against real BMW material/shader permutations.
51. Map the source-backed SGB OCCL Name/Resource/PositionTL/TR/BL/BR record into its 0x120 concrete runtime object and the header-bit1 wrapper/batch admission modes — Phase 534 implemented.
52. Correct the PART binary layout and map its AABB, four child-partition ID/pointer slots, mask-driven tree insertion and one-based scene-wrapper references — Phase 535 implemented.
53. Normalize production FLAT signed terminal spans and map the proven +0x38 direct-object / +0x3c runtime-index consumer lifecycle — Phase 542 implemented.
54. Correct the production NODE/SUMM record to 0x1c metadata + inline payload, map LOD/HIERARCHY/OBJECT MATRIX/subobject recursion and keep DAMAGE on its alternate XML path — Phase 543 implemented.
55. Mark common object byte +0x21 as source-unconsumed/corpus-zero and map the proven XML-only DAMAGE wrapper fields — Phase 544 implemented.
56. Join FLAT leaf runtime indices to SUMM wrapper order and PART one-based child IDs to the NODE wrapper registry; record PART-to-FLAT runtime materialization — Phase 545 implemented.
57. Map source-backed FLAT include/exclude masks, bounding spheres and tree-node AABBs while retaining leaf +0x20..+0x34 only as a corpus-verified bounds candidate — Phase 546 implemented.
58. Normalize FLAT/SUMM and PART/NODE identity plus proven spatial geometry into fail-closed SHIFT.SGBScenePlacement/1 — Phase 547 implemented.
59. Prove OBJECT resource-descriptor → render-instance admission plus explicit/MatrixNumber transform selection — Phase 548 implemented.
60. Prove the direct FLAT `+0x20..+0x34` spatial-query consumer and promote the corpus candidate to source-backed leaf bounds — Phase 549 implemented.
61. Reconstruct the static MultiMatrix layout/update, including explicit root overwrite, low-byte parent selection and local*parent-world composition — Phase 550 implemented.
62. Prove constructor root state plus immediate/deferred SceneGraph 0x40-byte transform transport into LOD/HIERARCHY vfunc +0x2c — Phase 551 implemented.
63. Join SGB placement wrappers to recursive OBJECT resource/world-transform handoffs with independent fail-closed admission — Phase 552 implemented.
64. Feed admitted MEB scene instances into the existing generic RenderBinding pipeline without fabricating VHF nodes — Phase 553 implemented.
65. Recover the retail SGB OBJECT resource factory: default MeshType/type 0, `.imb/.imx` promotion to MeshInst/type 7, and the type-7 render-instance branch — Phase 554 implemented.
66. Map MeshInst inheritance/runtime layout, `.imx` XML versus `.imb` binary loaders, aligned 0x40-stride instance storage and category-10 lifecycle — Phase 555 implemented.
67. Decode the source-backed IMB fixed mesh header, optional bone block and Type/Usage/Channel stream table while keeping the variable prefix explicit — Phase 556 implemented.
68. Recover the packed IMB version/control/name prefix and auto-locate the fixed header/bone gate — Phase 557 implemented.
    Phase 558 corrects descriptor/vertex block sequencing, preserves supported raw vertex streams and derives the primitive section offset.
    Phase 559 adds optional source-backed v0.4 material/palette/index/bounds primitive records.
69. Recover full IMB vertex+primitive payload consumption and implement neutral IMB/IMX scene adapters; independently recover/capture blocked SceneGraph transform-update history. Phase 560 implements the fail-closed neutral IMB geometry adapter over the proven v0.4 stream/primitive payload. Phase 561 connects admitted `.imb` MeshInst resources through that adapter into the generic material/shader/RenderBinding pipeline. Phase 562 production-validates all 427 Silverstone Era3 IMBs. Phase 563 closes all 428 IMB primitive MTX→same-archive BMT references across 84 unique logical materials. Phase 564 decodes all 239 archive-local BMT occurrences, closes 563/563 same-archive DDS references, then resolves all five exact global FX source paths in retail `RENDER.bff`; all 239 Silverstone materials are source-dependency-ready. Phase 565 closes the compiled FXO family inventory: 1,280 cache copies collapse to 368 unique decoded payloads with zero parse failures, while material-specific permutation attribution remains fail-closed. Phase 566 implements concrete IMB-primitive/BMT/vertex-layout-aware ranking through the existing material linker and emits explicit unique/ambiguous/heuristic/runtime-target states. Phase 567 executes that gate over all 428 Silverstone primitive bindings: all 428 are statically ambiguous, with zero heuristic/missing rows, and the tied surface collapses to 51 distinct permutation identities. Phase 568 converts every complete top-rank set into capture-oriented runtime hash targets: all 428 bindings are capture-ready, the global whitelist is 51 pixel-shader byte hashes, and each primitive needs only 5–15 hashes while exact pair attribution remains runtime-gated. Phase 569 applies that target set directly to raw D3D9 JSONL, preserving shader-object/device/draw provenance and emitting only candidate draws whose active shader bytes intersect the whitelist. Phase 570 carries exact archive-local IMB path + decoded SHA-256 and source-backed primitive first/index counts into the ranking/target contracts; all 428 Silverstone bindings are statically ready for same-instance matching. Phase 571 adds source Type/Usage/Channel declaration descriptors, preserves every static VS/PS candidate variant behind deduplicated prefilter hashes, and emits `SHIFT.IMBRuntimeResourceEvidenceSet/1` for the existing D3D9 runtime evidence path without claiming IMB/MEB equivalence. Phase 572 implements the fail-closed per-resource `SHIFT.IMBRuntimeShaderVariantMatch/1`: exact IMB path/SHA, declaration-proven same-instance draw, exact primitive range and a unique strong permutation/pair/VS+PS variant are all required; pixel-only hits remain prefilter evidence. Phase 573 adds `SHIFT.IMBRuntimeCapturePipeline/1`, routing Phase 569 shader hits by exact source draw ranges, reconstructing full D3D9 binding evidence only for candidate IMB resources, and immediately applying the Phase 572 matcher. Phase 574 adds `SHIFT.IMBRuntimeShaderAdmission/1`, revalidating attributed runtime rows against exact IMB binding/resource/draw identity and preserved static variants before authorizing a shader-selection identity; render admission remains false. Phase 575 propagates exact vertex-program offsets through ranking/target/match/admission, expands ambiguous VS ties into explicit candidates, and lets `material_linker` rebuild a complete `SHIFT.MaterialBinding/1` from a strong runtime admission without falling back to static ranking. Phase 576 joins those admissions back to exact SGB/IMB scene primitives by archive/path/SHA + primitive/draw/material/BMT/shader identity, reuses one resource-level admission across repeated scene instances, and forwards the resulting runtime-proven MaterialBinding into the existing StaticDraw/RenderCommand path. Phase 577 preserves that proof as `SHIFT.RuntimeProvenDraw/1` through StaticDraw and RenderCommand, with fail-closed validation against exact IMB identity, runtime-admission source and the actual command draw range. Phase 578 adds `SHIFT.NativeSceneBundle/1`, retaining only ready runtime-proven IMB draws in deterministic scene order with exact world/resource/draw/shader identity, deterministic hashes and explicit partial-coverage exclusions. Phase 579 adds neutral `SHIFT.VulkanDrawBundle/1`: it accepts neutral/IMB geometry, requires RuntimeProvenDraw by default, reuses the existing native submission + geometry/constants/textures/sampler/pipeline gates and explicitly preserves-but-does-not-execute the SGB world matrix. Phase 580 adds `SHIFT.NativeSceneVulkanSet/1`, revalidating every Phase 578 scene hash/identity, resolving exact IMB primitive geometry plus ordinary 2D DDS resources from IR and building ordered Vulkan child bundles. Phase 581 executes each proven affine SGB world matrix during geometry preparation using the recovered row-vector convention, inverse-transpose normals and linear tangent transforms while preserving the legacy object-space path. External runtime resources and native scene-set admission remain separate gates. Authentic Silverstone runtime observation remains the next shader evidence gate. IMX adaptation and transform-update history remain.
70. Derive proven animation poses from the BAB runtime grammar.
71. Port the stable native render/runtime boundary to Android.
72. Integrate gameplay/input/audio/streaming only after the core data and render/runtime contracts stabilize.

## Workstream status

| Workstream | State | Exit condition |
|---|---|---|
| BFF/XMem-LZX | verified | broader uncommon-variant coverage |
| Resource IR | active | remaining format-specific joins |
| MEB / vertex ABI | strong static | more runtime same-instance proofs |
| Material/shader linking | raw/reconstructed BMW matchers + retail material-slice dedup implemented | one authentic D3D9 BMW body capture |
| Desktop renderer | active oracle | broader exact D3D9/material coverage |
| Skinning | contract implemented | runtime pose production |
| BAB animation | evidence-backed | resolve remaining semantic gaps |
| SGB scene | placement + OBJECT/MultiMatrix + RenderBinding bridge + MeshInst runtime + source-backed v0.4 IMB neutral geometry + admitted-IMB RenderBinding integration; Silverstone capture/matcher/admission, full MaterialBinding relink, exact primitive join, RuntimeProvenDraw, NativeSceneBundle, ordered Vulkan scene set and affine world-transform geometry execution implemented | authentic Silverstone D3D9 evidence + neutral scene-set admission into native_runtime + external runtime resources + IMX neutral adapter + per-instance SceneGraph update history + native scene loading |
| Camera | active | higher-level behavior |
| Vehicle physics | active | runtime graph, participant gate, manager event path, participant registry/update bridge, selector-context separation, participant process/reselection, selector candidate lifecycle, IGPhaseVehicle finalization, selector descriptor population, source-record admission scheduling and force-law boundaries; BFF-to-pre-PhysX handoff implemented |
| Builtin solver | source-backed | runtime frame parity |
| Specialized providers | capture-ready | real capture + numeric differential; source-mutation, pre-PhysX handoff, participant-manager event, selector-context separation, participant process/reselection and selector-candidate lifecycle layers implemented |
| D3D9 capture | mature | more real same-instance evidence |
| Track/path runtime correlation | active | `TrackDetails`/`TrackList` structural-load-selection core and waypoint queries/links are source-backed; exit still requires a complete/unambiguous AIW → runtime → concrete path graph capture |
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
