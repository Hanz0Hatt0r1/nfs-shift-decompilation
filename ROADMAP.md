# SHIFT Decompilation Roadmap

This document tracks the current execution order. Detailed historical work is preserved in `docs/PHASE*.md`.

## Current milestone: specialized-provider runtime capture

**Current mainline: Phase 620.**



Phases 499–500 make the specialized-provider capture directory self-describing:

- pre/post snapshots are indexed by provider id and hit;
- duplicate and missing stages are detected;
- pre snapshots define structural readiness;
- optional post snapshots enable reset→solve order analysis;
- scalar-reset events can be scoped by frame index;
- results are emitted as `SHIFT.SpecializedProviderCaptureBundleRuntime/1`;
- the verification CLI returns 0 for ready evidence and 2 for blocked evidence.

Exact retail/provider numeric parity remains open until a real runtime frame is captured.

Phase 599 connects the already-recovered CameraManager six-word snapshot and guarded double-buffer swap into `SHIFT.NativeRuntimeState/1`. The native fixed-step scheduler exercises that boundary and exposes telemetry, while retail camera timestamp frequency, suppression timing and controller semantics remain explicitly unassigned.


Phase 601 adds `SHIFT.NativeRuntimeInputScript/1`, a fail-closed deterministic per-fixed-step throttle/brake/steer source. The same `PhysicsTickBoundary::tick()` that receives live keyboard intent records script-driven activity counters in CI, without assigning retail gamepad curves, filters or vehicle-force semantics.

Phase 602 adds `SHIFT.NativePhysicsParticipantBoundary/1`, joining the source-backed participant gate, `DAT_00c109e0` registry ABI, separate `DAT_00bbc600` selector context and IGPhaseVehicle writeback slots. Native runtime admits only this structural ABI; concrete participant/provider identity remains capture-gated.


Phase 603 ports the source-backed builtin sparse numeric kernel `FUN_007b0f20` into native C++, with deterministic 3×3/4×4 parity and fail-closed graph/zero-pivot tests. It does not execute a complete BMW frame; matrix/RHS assembly, runtime diagonal-reset flags, provider-present dispatch and body-state application remain separate gates.


Phase 604 ports the exact source-backed `FUN_007b2210` diagonal reset mutation into native C++. The reset operation is executable and parity-tested, but reset-node selection remains gated by the runtime `sample+0x70 & 1` evidence rather than inferred statically.

Phase 605 keeps the PhysicsParticipantManager registry index and IGPhaseVehicle selector ordinal as separate runtime identity domains until an independent join is observed.

Phase 606 adds `SHIFT.NativeBuiltinSolverFrame/1`: an explicit provider-absent matrix/RHS/reset/graph packet, Python oracle and native loader/executor for the exact `FUN_007b2210 → FUN_007b0f20` sequence. It does not derive any of those runtime-only inputs.

Phase 611 adds an explicit persistent BODY accumulator mode on top of the Phase 610 solve→post-solve chain. It carries only the six opaque FUN_007b4110 BODY channels between fixed steps, verifies the same prepared one-step delta on every step, and deliberately keeps persistent vehicle transform/motion state false.

Phase 612 ports the source-backed `FUN_007ba570` per-BODY additive solver-vector/matrix export to native C++ with deterministic multi-BODY accumulation parity. Contribution generation (`FUN_007bc680`/runtime sampled state) remains evidence-gated, so this is a pre-solve primitive rather than complete retail matrix/RHS assembly.

Phase 613 wraps that primitive in `SHIFT.NativeBodySolverExportFrame/1`: explicit proof-gated per-BODY `+0x150/+0x154` contributions are replayed in exact BODY order into zero-initialized complete solver destinations and checked against a Python oracle. Contribution generation remains external evidence, and the result is not yet joined to the prepared builtin solver frame.

Phase 614 adds an exact pre-reset SBEX→SBFR join: the complete FUN_007ba570 global vector must equal the prepared RHS and every N² matrix double must equal the prepared solver matrix before FUN_007b2210/FUN_007b0f20 execution is admitted. A valid but mismatched SBEX remains fail-closed. Phase 615 moves that verification into each admitted native fixed step through `--body-solver-export-frame`, so prepared SBFR execution is gated by supplied BODY export evidence before every reset/solve. Phase 616 ports the deterministic front of `FUN_007bc680`: exact residual construction, retail `FUN_007aefb0` float boundary and +0x90 linear scaling. Phase 617 ports the source-backed single-JOINT `FUN_007bac60` three-lane projection and corrects the older Python JOINT oracle so all cross/coupling terms use BODY +0x18/+0x20/+0x28 exactly. Phase 618 ports both branches of the source-backed `FUN_007bae40` HINGE two-lane projection, including its body-frame transform, cross correction, sign rule and bounded solver-vector write.

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
69. Recover full IMB vertex+primitive payload consumption and implement neutral IMB/IMX scene adapters; independently recover/capture blocked SceneGraph transform-update history. Phase 560 implements the fail-closed neutral IMB geometry adapter over the proven v0.4 stream/primitive payload. Phase 561 connects admitted `.imb` MeshInst resources through that adapter into the generic material/shader/RenderBinding pipeline. Phase 562 production-validates all 427 Silverstone Era3 IMBs. Phase 563 closes all 428 IMB primitive MTX→same-archive BMT references across 84 unique logical materials. Phase 564 decodes all 239 archive-local BMT occurrences, closes 563/563 same-archive DDS references, then resolves all five exact global FX source paths in retail `RENDER.bff`; all 239 Silverstone materials are source-dependency-ready. Phase 565 closes the compiled FXO family inventory: 1,280 cache copies collapse to 368 unique decoded payloads with zero parse failures, while material-specific permutation attribution remains fail-closed. Phase 566 implements concrete IMB-primitive/BMT/vertex-layout-aware ranking through the existing material linker and emits explicit unique/ambiguous/heuristic/runtime-target states. Phase 567 executes that gate over all 428 Silverstone primitive bindings: all 428 are statically ambiguous, with zero heuristic/missing rows, and the tied surface collapses to 51 distinct permutation identities. Phase 568 converts every complete top-rank set into capture-oriented runtime hash targets: all 428 bindings are capture-ready, the global whitelist is 51 pixel-shader byte hashes, and each primitive needs only 5–15 hashes while exact pair attribution remains runtime-gated. Phase 569 applies that target set directly to raw D3D9 JSONL, preserving shader-object/device/draw provenance and emitting only candidate draws whose active shader bytes intersect the whitelist. Phase 570 carries exact archive-local IMB path + decoded SHA-256 and source-backed primitive first/index counts into the ranking/target contracts; all 428 Silverstone bindings are statically ready for same-instance matching. Phase 571 adds source Type/Usage/Channel declaration descriptors, preserves every static VS/PS candidate variant behind deduplicated prefilter hashes, and emits `SHIFT.IMBRuntimeResourceEvidenceSet/1` for the existing D3D9 runtime evidence path without claiming IMB/MEB equivalence. Phase 572 implements the fail-closed per-resource `SHIFT.IMBRuntimeShaderVariantMatch/1`: exact IMB path/SHA, declaration-proven same-instance draw, exact primitive range and a unique strong permutation/pair/VS+PS variant are all required; pixel-only hits remain prefilter evidence. Phase 573 adds `SHIFT.IMBRuntimeCapturePipeline/1`, routing Phase 569 shader hits by exact source draw ranges, reconstructing full D3D9 binding evidence only for candidate IMB resources, and immediately applying the Phase 572 matcher. Phase 574 adds `SHIFT.IMBRuntimeShaderAdmission/1`, revalidating attributed runtime rows against exact IMB binding/resource/draw identity and preserved static variants before authorizing a shader-selection identity; render admission remains false. Phase 575 propagates exact vertex-program offsets through ranking/target/match/admission, expands ambiguous VS ties into explicit candidates, and lets `material_linker` rebuild a complete `SHIFT.MaterialBinding/1` from a strong runtime admission without falling back to static ranking. Phase 576 joins those admissions back to exact SGB/IMB scene primitives by archive/path/SHA + primitive/draw/material/BMT/shader identity, reuses one resource-level admission across repeated scene instances, and forwards the resulting runtime-proven MaterialBinding into the existing StaticDraw/RenderCommand path. Phase 577 preserves that proof as `SHIFT.RuntimeProvenDraw/1` through StaticDraw and RenderCommand, with fail-closed validation against exact IMB identity, runtime-admission source and the actual command draw range. Phase 578 adds `SHIFT.NativeSceneBundle/1`, retaining only ready runtime-proven IMB draws in deterministic scene order with exact world/resource/draw/shader identity, deterministic hashes and explicit partial-coverage exclusions. Phase 579 adds neutral `SHIFT.VulkanDrawBundle/1`: it accepts neutral/IMB geometry, requires RuntimeProvenDraw by default, reuses the existing native submission + geometry/constants/textures/sampler/pipeline gates and explicitly preserves-but-does-not-execute the SGB world matrix. Phase 580 adds `SHIFT.NativeSceneVulkanSet/1`, revalidating every Phase 578 scene hash/identity, resolving exact IMB primitive geometry plus ordinary 2D DDS resources from IR, building ordered Vulkan child bundles and keeping world-transform/external-runtime-resource execution as explicit native submission blockers. Phase 581 adds `SHIFT.VulkanWorldTransformPacket/1` (`SVWT`), preserves the exact source-backed row-major D3D matrix bytes, proves their GLSL column-matrix interpretation and native C++ row-vector behavior, and emits one transform packet per scene child without assigning a retail shader register. Phase 582 consumes that sidecar in the native material executor for translation-only matrices, mutating only proven FLOAT3 POSITION0 before GPU upload. Phase 583 upgrades SVGP to binary version 3 with exact SHIFT property IDs in each native vertex attribute, updates all native readers with v1/v2 compatibility and removes the semantic-identity blocker. Phase 584 executes non-singular affine SVWT matrices in the native material path with affine POSITION, inverse-transpose NORMAL and normalized linear TANGENT/TANGENT2 transforms; singular matrices and legacy multi-attribute affine packets remain fail-closed. Phase 585 adds neutral `SHIFT.VulkanDrawBundlePrepare/1` + `SHIFT.NativeSceneVulkanSetPrepare/1`, compiles/reflects and interface-validates every ordered runtime-proven scene child, validates SVWT/hash/provenance gates, and fixes `bundle_set.paths` to be strictly set-root-relative without BMW relabeling. Phase 586 adds the neutral `native_runtime --scene-set` loader and Phase 587 makes its SVWT execution observable through bootstrap counters for total and general-affine transformed draws. Phase 588 adds an explicit fail-closed external `sampler2D` snapshot channel to SVTP/VulkanDrawBundle/DDS bridging without promoting unresolved scene resources. Phase 589 adds `SHIFT.NativeSceneExternalSamplerSnapshots/1` and admits an external `sampler2D` only when exact scene draw hash, IMB archive/path/SHA, primitive, register/type, texture hash and provenance all match; unresolved or mismatched resources remain fail-closed. Phase 590 carries only strong-attributed draw-local D3D9 texture observations out of the Phase 573 pipeline and converts one unambiguous observed `CreateTexture` + captured PPM into the exact Phase 589 contract. Phase 591 additionally retains strong-attributed draw-local VS constant state and resolves repeated world-space scene instances only when exact float32 4x4 constant windows uniquely match one SGB world matrix; no retail world-register semantic is assigned. Phase 592 adds source-backed IMX neutral geometry and renderer integration without conflating IMX with IMB/MEB. Phase 593 closes exact external `samplerCube` transport at the already-proven s3 boundary: six captured cube-face PPMs become one scene-bound `ReferenceCubeTexture/1`, are revalidated against exact draw/resource/primitive identity, and enter the existing Vulkan cube packet without generalizing cube registers. Phase 594 adds `SHIFT.SGBMultiMatrixRootSolve/1`: for a runtime-observed MatrixNumber slot world matrix it inverts only the source-backed root-connected local chain, solves the current root, and accepts it only when the existing MultiMatrix evaluator reproduces the observation. Phase 595 adds `SHIFT.SGBRuntimeObjectCandidateJoin/1`: exact runtime IMB archive/path/SHA is revalidated against IR and then narrows pre-admission SGB placement/wrapper/object candidates by logical resource path without using RenderBinding `binding_index`. Phase 596 adds `SHIFT.SGBMultiMatrixRootConsensus/1`: all contiguous strong-attributed VS constant windows are tested without assigning register semantics, and one exact MultiMatrix owner root (`wrapper + owner_path`) is authorized only when at least two distinct exact runtime resources with at least two distinct cumulative local chains independently solve to the same exact float32 root through the Phase 594 round-trip gate. Phase 597 applies only ready owner-scoped roots back into `SHIFT.SGBObjectRenderHandoffSet/1`, recomputing MatrixNumber world matrices through the existing evaluator before scene admission while preserving runtime-consensus provenance. Phase 598 adds `SHIFT.SGBMultiMatrixRuntimeCoverage/1`, orchestrating Phases 595–597 plus ordinary scene admission and measuring baseline/promoted numeric MatrixNumber rows plus newly admitted bindings on supplied runtime evidence. Authentic Silverstone runtime capture content remains the external evidence gate; historical SceneGraph update sequence remains separate.
70. Derive proven animation poses from the BAB runtime grammar.
71. Port the stable native render/runtime boundary to Android.
72. Integrate gameplay/input/audio/streaming only after the core data and render/runtime contracts stabilize.
73. Execute the recovered CameraManager six-word snapshot plus guarded double-buffer flip/copy inside the native fixed-step scheduler without claiming retail timing — Phase 599 implemented.
74. Seed that live Phase 599 camera scheduler from fail-closed recovered CameraManager snapshot/swap evidence without transporting the opaque camera-source token — Phase 600 implemented as SHIFT.NativeCameraStateBridge/1 plus --camera-state.
75. Make native vehicle-control input deterministic without inventing retail controller semantics — Phase 601 implemented as SHIFT.NativeRuntimeInputScript/1.
76. Admit the source-backed participant registry/selector structural ABI into native state while preserving manager/selector separation and unresolved runtime participant identity — Phase 602 implemented as SHIFT.NativePhysicsParticipantBoundary/1.
77. Port the exact source-backed builtin sparse solver kernel to native C++ and verify deterministic numerical parity independently of full-frame assembly — Phase 603 implemented for FUN_007b0f20.
78. Port the exact builtin diagonal-reset mutation while keeping reset-node selection runtime-evidence-gated — Phase 604 implemented for FUN_007b2210.
79. Preserve participant-manager registry identity and IGPhaseVehicle selector identity as separate native domains until an independent runtime join exists — Phase 605 implemented.
80. Add a fail-closed prepared builtin solver-frame contract containing explicit provider-absent proof, matrix/RHS, reset nodes and exact sparse graph, then execute FUN_007b2210 → FUN_007b0f20 with Python/native oracle parity — Phase 606 implemented.
81. Promote one concrete native participant only from independent manager-registry and IGPhaseVehicle selected-pointer runtime observations while retaining selector ordinal as a separate identity domain — Phase 607 implemented as SHIFT.NativePhysicsParticipantRuntimeEvidence/1.
82. Execute an exact Phase 606 provider-absent solver frame on the native fixed-step scheduler only when Phase 607 participant evidence is ready and solver/workspace scalar cardinality matches — Phase 608 implemented.
83. Port the exact source-backed `FUN_007b4110` JOINT/HINGE/BAR post-solve BODY projection to native C++ with an explicit proof-gated SBPS packet and Python/native oracle parity, independently of fixed-step integration — Phase 609 implemented.
84. Join the actual Phase 608 native solver result into the Phase 609 `FUN_007b4110` projection on each fixed step, requiring participant/workspace cardinality and solved-vector identity before BODY projection — Phase 610 implemented.
85. Port the complete source-backed `FUN_007bae40` HINGE projection to native C++, including zero/nonzero branches, exact transform/cross boundaries and bounded two-lane BODY solver-vector application — Phase 618 implemented.
86. Port the complete source-backed `FUN_007bb090` BAR projection to native C++, including the inline three-component basis, weighted one-lane reduction, nonzero-side bias correction and bounded BODY solver-vector application — Phase 619 implemented.
87. Port the source-backed `FUN_007bbb80` JOINT matrix block algebra to native C++, covering self, JOINT↔JOINT, JOINT↔HINGE and JOINT↔BAR blocks with exact lower-triangle orientation/sign policy — Phase 620 implemented.

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
| SGB scene | placement + OBJECT/MultiMatrix + RenderBinding bridge + MeshInst runtime + source-backed IMB/IMX neutral geometry; Silverstone capture/matcher/admission, native scene execution, external sampler admission, Phase 594 root solve, Phase 595 candidate join, Phase 596 owner-scoped cross-resource root consensus and Phase 597 consensus→handoff application implemented | authentic Silverstone D3D9 capture content + renderer-owned resource types beyond sampler2D/samplerCube-s3 + runtime IMX same-instance proof + authentic Phase 598 production coverage numbers + historical SceneGraph update sequence |
| Camera | source-backed manager/state primitives + native snapshot/double-buffer handoff | retail timing/controller/view-selection behavior and exact render integration |
| Native input | live keyboard intent + deterministic fixed-step input-script path | gamepad/analog normalization and retail input filtering |
| Vehicle physics | active; Phase 607 runtime participant promotion + Phase 608 fixed-step prepared builtin solver + Phase 609 native post-solve parity + Phase 610 solve→BODY projection + Phase 615 fixed-step SBEX→SBFR evidence gate + Phase 616 preprojection + Phase 617 JOINT + Phase 618 HINGE + Phase 619 BAR projection + Phase 620 JOINT matrix block algebra implemented | HINGE/BAR matrix coupling, BODY sample-array orchestration/sparse writes, authentic sampled-state/matrix-RHS/reset observations, provider dispatch and persistent vehicle-state integration |
| Builtin solver | source-backed + native FUN_007b0f20/FUN_007b2210/FUN_007b4110 + Phase 606/609 packets + Phase 610 fixed-step reset→solve→projection chain | authentic per-step matrix/RHS/reset/constraint-row evidence and persistent BODY integration |
| Specialized providers | capture-ready | real capture + numeric differential; source-mutation, pre-PhysX handoff, participant-manager event, selector-context separation, participant process/reselection and selector-candidate lifecycle layers implemented |
| D3D9 capture | mature | more real same-instance evidence |
| Track/path runtime correlation | active | `TrackDetails`/`TrackList` structural-load-selection core and waypoint queries/links are source-backed; exit still requires a complete/unambiguous AIW → runtime → concrete path graph capture |
| Vulkan | active; BMW material multi-draw + source-backed cull/depth/blend + exact external sampler2D and samplerCube-s3 transport/admission | authentic capture content/resource types beyond proven 2D/cube-s3 channels, retail non-paint permutations, alpha-test/bias/stencil evidence |
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
