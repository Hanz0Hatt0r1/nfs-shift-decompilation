# Need for Speed: SHIFT — Decompilation & Resource IR

Evidence-driven reconstruction of *Need for Speed: SHIFT* resource formats, runtime contracts and rendering/physics boundaries.

> **Current mainline: Phase 571**
>
> Phase 502 joins the source-backed SDF construction, provider selection/rebind and vtable lifecycle contracts. Phase 503 adds a direct BFF-to-pre-PhysX/provider handoff command. Phase 504 adds a runtime-capture preflight for the retail PE, Wine, GDB and GDB Python. Phase 505 closes the source-backed vehicle physics participant creation/load gate. Phase 506 adds the source-backed PhysicsParticipantManager event-0x20 ingestion path. Phase 507 adds the participant slot registry/update bridge used by PhysicsParticipant.cpp. Phase 508 resolves the selector global as DAT_00bbc600 and keeps it explicitly separate from the participant-manager global DAT_00c109e0. Phase 509 traces the saved participant pointer/ordinal through the subsequent process/reselection loop and vehicle-BFF load. Phase 510 closes the descriptor-level selector candidate lifecycle, including the observed +0x74 eligibility/exclusion state, +0x8c ordinal writeback, bounded batch reservation and distinct +0x1d post-load/process flag. Phase 511 closes the IGPhaseVehicle completion/finalization boundary, including per-container callbacks, guarded +0x160 cleanup, resource teardown and final object callback ordering. Phase 512 maps the selector descriptor population path exactly, including capacity/stride, packed token bits, source-to-descriptor copies, +0x74 initialization and conditional +0x70 population. Phase 513 closes the upstream source-record admission mask path through owner +0x4f0 and its reset/resynchronization calls. Exact retail numeric parity remains capture-gated.

Phase 515 adds a low-stop specialized-provider GDB probe mode for captures where per-frame debugger stops disturb simulation timing. Phase 516 adds deterministic AIW/runtime waypoint-edge validation, Phase 517 joins `Path.StartNode` to `AIPolylinePath.array`, and the current track/path pipeline now also validates concrete runtime instance graphs and emits an explicit capture-handoff readiness report. Phase 518/519 close FLAT runtime record/index-table links, Phase 520 maps the SGB NODE wrapper, Phase 521 records the HIERARCHY serialized-child → runtime-element copy layout, Phase 522 classifies the concrete OBJECT/HIERARCHY/DAMAGE runtime wrapper classes, Phase 523 maps the SUMM runtime wrapper, Phase 524 adds the ordered fail-closed multi-submesh Vulkan bundle-set boundary, Phase 525 composes SPIR-V/reflection/interface/provenance preparation across every ordered draw, Phase 526 executes that prepared set in one depth-tested native Vulkan render pass with per-draw pipelines, descriptors, constants, textures and geometry, Phase 527 adapts complete BMW material slices into that draw-set while preserving per-submesh DDS/provenance, Phase 528 removes the paint-only upstream restriction so every canonical BMW body primitive can enter the same fail-closed BMT → FX/FXO → RenderCommand path, Phase 529 combines independently proven primitive slices into one canonical, revalidated multi-submesh command for the Phase 527–526 Vulkan path, Phase 530 executes the source-backed BMT cull enum independently per draw, Phase 531 carries corpus-verified BMT depth/alpha state into typed neutral IR, Phase 532 executes the statically proven depth and alpha-blend subset per draw in Vulkan while keeping alpha-test and unresolved state fail-closed, Phase 533 adds canonical six-primitive BMW body material admission with independent blockers, permutation grouping and optional direct Vulkan multi-draw handoff, Phase 534 maps the SGB OCCL Name/Resource/PositionTL/TR/BL/BR record into its concrete 0x120-byte runtime object plus the header-bit1 wrapper/batch admission split, Phase 535 corrects the PART binary offsets and maps its AABB, child-partition IDs, one-based child-object lookup and mask-driven runtime partition tree, Phase 536 makes retail BMW shader admission archive-layout-safe by scoping FXOs to the selected shader family and collapsing byte-identical duplicate resources across primary/cockpit/RENDER BFFs, Phase 537 executes that retail corpus, collapses identical top-ranked bytecode identities and records the remaining genuine permutation blockers, Phase 538 turns those tied top-rank identities into a capture-oriented per-primitive shader target set without selecting a permutation, Phase 539 joins that set to exact MEB identity, indexed primitive ranges and same-instance D3D9 shader hashes, Phase 540 adds a raw JSONL shader/draw prefilter so short captures can be screened before full runtime reconstruction, Phase 541 applies content-identity deduplication to downstream retail material-slice resources, Phase 542 fixes production FLAT signed-terminal span normalization while mapping the proven +0x38/+0x3c leaf consumer lifecycle, and Phase 543 corrects the retail NODE layout to 0x1c metadata plus inline LOD/HIERARCHY/OBJECT payloads with SGB-relative references, MATRIX records and recursive subobjects.

Phase 544 closes the remaining common NODE control-byte boundary: byte `+0x21` has no consumer in the binary dispatcher and no XML counterpart, remains raw/unassigned, and is zero across 541 recursively decoded NODE objects from all four Silverstone Era3 visual variants. The XML-only DAMAGE wrapper now also carries its source-backed `matrices`, matrix-array, subobject-array and `MatrixNumber` runtime offsets without implying binary NODE admission.

Phase 545 closes the object-to-spatial placement identity join: FLAT leaf `+0x3c` indexes SUMM wrappers by source order, PART child IDs resolve one-based into the NODE wrapper registry, and the source-backed PART runtime builder explains generated FLAT-like `+0x38/+0x3c` records. The FLAT/SUMM join is production-verified across 21,580 Silverstone placements. Phase 546 maps source-backed FLAT include/exclude masks, bounding spheres and tree-node AABBs; leaf `+0x20..+0x34` remains source-unresolved but is retained as a corpus-verified bounds candidate whose midpoint matches the sphere centre across all 21,580 placements. Phase 547 normalizes FLAT/SUMM and PART/NODE identity plus proven spatial geometry into `SHIFT.SGBScenePlacement/1`, while keeping world transforms and draw admission explicitly unresolved. Phase 548 proves the binary OBJECT resource-descriptor → render-instance path and exact transform selector: explicit transforms are materialized source-equivalently, while parent `MatrixNumber` stays tied to a validated 0x40-byte MultiMatrix slot. Phase 549 closes the retail spatial-query consumer for FLAT leaf `+0x20..+0x34` and promotes that six-float min/max block from advisory corpus evidence to source-backed placement bounds. Phase 550 reconstructs the source-backed static `MultiMatrix` layout and numeric update: local/world 0x40-byte matrices plus 0x10-byte descriptors, low-byte parent selection and D3D row-vector `world[i] = local[i] * world[parent]` composition. Phase 551 closes the root transport itself: constructor world slot 0 starts as serialized local slot 0, while SceneGraph update type 4 copies an exact 0x40-byte matrix and forwards it to the owner vfunc +0x2c. Current root remains fail-closed whenever per-instance update history is unknown. Phase 552 joins `SGBScenePlacement/1` with recursive OBJECT handoffs as `SGBRenderBindingAdmission/1`, preserving one-wrapper-to-many-OBJECT identity and admitting only rows with proven spatial culling, resource identity and a numeric world matrix. Phase 553 resolves those admitted MEB resource instances through the existing MEB/BMT/FXO pipeline into a generic `SHIFT.RenderBinding/1` while preserving the SGB world matrix and keeping blocked scene rows fail-closed. Phase 554 closes the retail OBJECT resource-factory split: descriptors begin as MeshType/type 0, `.imb`/`.imx` are promoted by `FUN_00831940` to MeshInst/type 7, and the type-7 render-instance branch is preserved without asserting MeshType/MeshInst payload equivalence to MEB. Phase 555 follows MeshInst into its 0xb0-byte runtime layout, proves `.imx` XML versus `.imb` binary loading, and maps descriptor `+0x30` → runtime `+0x80` count plus aligned `0x40`-stride storage at `+0x84` and renderer category-10 lifecycle. Phase 556 follows `LoadBinaryMeshFromResource` into the IMB payload and decodes the fixed mesh header, optional bone block, Type/Usage/Channel stream descriptors and runtime primitive-record schema. Phase 557 closes the variable prefix itself: retail versions use a 4/6/11/11-bit packed value, `0.2.0.0` has a one-byte control form, `0.4.0.0` adds a raw u16 and 4-byte name alignment, and the parser now locates the fixed header and bone gate automatically. Phase 558 corrects IMB descriptor/vertex sequencing and consumes the raw stream payload; Phase 559 decodes the proven v0.4 primitive records. Phase 560 normalizes those streams/primitives into `SHIFT.IMBNeutralGeometry/1`, and Phase 561 feeds admitted `.imb` MeshInst resources into the generic RenderBinding path without relabeling them as MEB. Phases 562–564 production-close the supplied Silverstone Era3 path through all 427 IMBs, all 428 primitive material references, 239 BMT occurrences, 563 same-archive DDS references and the five exact global FX source dependencies. Phase 565 inventories the corresponding compiled shader caches: 1,280 FXO copies collapse to 368 distinct decoded payloads with zero parse failures. Phase 566 implements per-primitive material/geometry-aware ranking through the existing material linker. Phase 567 executes it over all 428 Silverstone primitive bindings: all 428 are valid but statically ambiguous, with zero heuristic/missing rows, and the surviving tied surface collapses to 51 distinct permutation identities. Phase 568 converts those complete top-rank sets into capture-oriented runtime targets: all 428 bindings are capture-ready, the global whitelist is 51 pixel-shader byte hashes, and each primitive requires only 5–15 hashes before same-instance attribution. Phase 569 adds a raw D3D9 JSONL prefilter that tracks created/active shaders per device and keeps only indexed draws whose active shader bytes intersect that whitelist, without claiming resource/draw/same-instance identity. Phase 570 carries exact archive-local IMB path + decoded payload SHA-256 and source-backed primitive draw ranges into the target set; all 428 Silverstone bindings are statically ready for runtime same-instance matching. Phase 571 adds source Type/Usage/Channel declaration descriptors, preserves every static VS/PS candidate variant behind deduplicated prefilter hashes, and emits an IMB runtime-resource evidence handoff compatible with the existing D3D9 binding pipeline without treating IMB as MEB.

The offline Linux runtime is now on main under `native_runtime/`: XCB/Vulkan swapchain execution, depth-tested prepared BMW material bundle submission, the fixed 60 Hz native state boundary, and the 40-scalar physics workspace admission path are covered by Linux Vulkan CI. Phase 524 keeps the proven single-draw bundle ABI intact while preparing ordered per-submesh bundles; Phase 525 requires every child to pass its existing SPIR-V/reflection/interface/provenance gates; Phase 526 consumes only that prepared set and submits all draws in one native frame; Phase 527 lets the existing BMW material-slice/DDS bridge populate each child independently before the set is indexed.

## Mission

Reconstruct observable formats, binary layouts, dependencies and runtime boundaries as deterministic, machine-readable intermediate representations.

Canonical render path:

`BFF → IR → VHF/MEB/BMT/DDS → FX/FXO → DrawBinding → RenderCommand → native renderer`

Linux/Vulkan is the native renderer direction. The desktop software renderer is the deterministic reference oracle.

## Evidence policy

Static source/PE evidence, runtime observations and neutral renderer contracts are separate layers.

Use explicit states such as `proven`, `verified`, `inferred`, `ambiguous`, `unknown`, `unsupported` and `blocked`. Missing evidence is never replaced with a plausible value.

## Current status

| Area | State | Current boundary |
|---|---|---|
| BFF/XMem-LZX | verified | Type 0/1/2 paths and X12d=2 covered; Type 3 uses an external Oodle-compatible runtime |
| Resource IR | active/verified | typed parsing, hashes and provenance |
| MEB / vertex ABI | strong static coverage | BMW descriptor triples and D3D9 Type/Usage evidence are source-backed |
| BMW COLOR0 | statically resolved | 460 → [4,6,0] → Type 4 / D3D9 COLOR |
| BMW COLOR1 | statically described, corpus-limited | 461 → [4,6,1]; no positive 1.02 corpus instance |
| Material/shader linking | retail BMW matcher + raw capture prefilter + material-slice dedup ready | exact permutation attribution now requires only one authentic BMW body D3D9 capture |
| Desktop reference renderer | active oracle | geometry, DDS, multi-sampler, samplerCube, VS→PS, explicit semantics, skinned command path |
| Skinning | contract implemented | MEB 310/580, explicit SkinPose, CPU reference, GLES parity |
| BAB animation | evidence-backed | bank/channel grammar reconstructed; remaining axis/order/trailing semantics explicit |
| SGB / scene | placement → OBJECT → MeshInst/IMB neutral geometry → generic RenderBinding active; Silverstone IMB/BMT/DDS/FX/FXO inventory, 428-primitive ranking, 51-hash target set, raw D3D9 prefilter, 428/428 exact IMB resource/draw identities, declaration descriptors and lossless shader-variant/runtime-resource handoff implemented | execute candidate-draw D3D9 binding evidence and same-instance shader-variant attribution, IMX neutral adapter, unresolved per-instance MatrixNumber update history and native scene loading remain |
| Camera | active | loader/state/event/control primitives reconstructed |
| AI database | source-backed structural/load/query core | retail `AIDatabase` singleton identity, AIW load/meta-section lifecycle and exact `WayPointBase` 0x1bc layout reconstructed; simple Branch-ID 0/1 queries plus retail `FUN_007189a0` Branch-filtered non-Euclidean nearest-path query implemented; parser internals and linked/local path search remain open |
| Track metadata | source-backed structural/load/selection core | retail `TrackDetails` plus `TrackList` singleton are recovered: exact 0x1d4/0xe4 sizes, property/post-load tokenization, ASCII source-path hash parity, source-backed `ScenegraphFile` → normalized scenegraph stem at +0x10, `tracklist.lst` CRLF/@ request grammar, recursive .trd fallback, taxonomy indices, owned TrackDetails lifecycle, scenegraph-stem lookup and `All`/`!exclude` Class filtering are source-backed; internal container ABI, non-ASCII CRT normalization and higher-level event selection remain open |
| Vehicle physics | active | CDF/EDF/GDF/SDF and wheel/contact/solver boundaries |
| Builtin solver | source-backed | sparse-solver lifecycle and matrix/kernel layers |
| Specialized providers | capture-ready | 40/34 scalar domains, structural solver IR, reset/selector provenance |
| Provider numeric parity | blocked on capture | requires an authentic runtime frame |
| Vulkan | active native backend | canonical BMW primitive-slice aggregation → typed BMT cull/depth/blend state → DDS bundles → prepared multi-draw |
| Android | deferred | waits on stable desktop/native runtime boundary |

## BMW M3 E36 vertical slice

The render slice is:

`VHF → MEB → BMT → FX/FXO → DrawPacket → RenderCommand`

The physics asset slice is:

`CDF + EDF + GDF + SDF → SHIFT.VehiclePhysicsAssetGraph/1`

### BMW paint bindings

| Material | FX sampler | D3D9 slot | Resource |
|---|---|---:|---|
| diffuseTexture | diffuseMap | s1 | COMMON_PAINT.dds |
| specularTexture | specularMap | s2 | COMMON_PAINT_SPECULAR.dds |
| scratchControlTexture | scratchControlMap | s4 | COMMON_BLANK.dds |
| environmentMap | environmentMap | s3 | external cube |
| shadow map | sShadowMap_f1_0 | s0 | external renderer resource |

## D3D9 / vertex ABI

MEB property descriptors are `[Type ordinal, Usage ordinal, Channel]`.

For BMW:

- 460 → `[4,6,0]`
- 461 → `[4,6,1]`
- Type 4 → `D3DDECLTYPE_D3DCOLOR`
- Usage ordinal 6 → D3D9 Usage 10 (`COLOR`)

This closes the static declaration mapping. It does **not** close same-instance runtime attribution.

Runtime closure requires correlation of MEB identity, declaration, vertex/index buffers, shaders and the exact `DrawIndexedPrimitive` boundary.

## Runtime capture

The D3D9 producer captures declaration/buffer/shader/constant/texture state and exact draws. Optional payload capture records texture mip data and VB/IB bytes. Draw-local snapshots are keyed by `(frame, draw_index)`.

Linux/apitrace tooling provides an alternate path for extracting unique BMW draw/resource instances and trimming large traces.

The retail BMW v1.02 corpus has been executed through the static admission path using `BMW_M3_E36.bff`, `BMW_M3_E36_Cockpit.bff` and `RENDER.bff`. BMT/FX/DDS resolution is complete for the five unique body materials; the remaining render blocker is concrete same-instance FXO permutation attribution from one authentic BMW body D3D9 capture.

The capture-side path is already implemented:

```text
retail body admission
  → BMWRuntimeShaderTargetSet/1
  → raw JSONL shader/draw prefilter
  → D3D9RuntimeBindingEvidence/1
  → BMWRuntimeShaderTargetMatch/1
  → exact static FXO selection
```

## Specialized-provider physics track

Current provider boundary:

`FUN_007b3f40 → FUN_007b2210(selector) → provider vtable +0x1c(selector) → provider +0x18 solve`

The repository now models:

- 40- and 34-scalar provider domains;
- row-pointer/workspace topology;
- pivot and acceptance structure;
- factor/write/dependency/update/operator IR;
- execution schedules and output-vector flow;
- read-before-write boundaries;
- provider vtable/reset lifecycle;
- scalar selector/reset provenance;
- live reset-effect and callsite evidence;
- reset→solve ordering;
- capture-session and capture-bundle verification;
- source-mutation correlation against source-derived factor edges;
- pre-PhysX/provider handoff cross-contract validation;
- BFF-to-pre-PhysX/provider handoff orchestration;
- runtime-capture preflight for retail PE/Wine/GDB/GDB Python;
- the source-backed vehicle physics participant creation/load gate;
- the PhysicsParticipantManager event-0x20 ingestion contract;
- the PhysicsParticipantManager participant slot registry/update contract;
- the vehicle physics selector-context separation contract;
- the vehicle physics participant process/reselection contract;
- the vehicle physics selector candidate lifecycle contract;
- the IGPhaseVehicle completion/finalization contract;
- the selector descriptor population contract;
- the selector source admission contract.

### Phase 499–500 capture bundle

`tools/verify_specialized_provider_capture_bundle.py` indexes:

```text
provider_pre_<provider>_<hit>.json
provider_post_<provider>_<hit>.json
scalar_reset_events.jsonl
```

A bundle is structurally ready only when its required pre snapshot exists and integrated validation passes. A post snapshot is optional for pre-only diagnostics.

The bundle layer performs provenance/orchestration; it does not infer matrix semantics or claim numeric equivalence.

## Useful commands

```bash
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR \
  --reset-events CAPTURE_DIR/scalar_reset_events.jsonl \
  -o provider_bundle_manifest.json

python tools/extract_trace_tail.py SHIFT.trace SHIFT_tail_500MiB.trace

python tools/extract_apitrace_unique_bmw.py \
  --target-runtime-geometry evidence/bmw_m3_e36_kit00_body_loda.runtime_geometry.json \
  capture.trace

python shift_importer.py bmw-body-material-admission \
  BMW_M3_E36.bff out/bmw-admission \
  --supplemental-bff BMW_M3_E36_Cockpit.bff \
  --supplemental-bff RENDER.bff

python shift_importer.py bmw-runtime-shader-target-set \
  out/bmw-admission/admission.json \
  out/bmw-runtime-shader-targets.json

python shift_importer.py bmw-raw-capture-shader-prefilter \
  out/bmw-runtime-shader-targets.json \
  shift_d3d9_capture.jsonl \
  out/bmw-raw-prefilter.json

python shift_importer.py bmw-runtime-shader-target-match \
  out/bmw-runtime-shader-targets.json \
  runtime-binding.json \
  out/bmw-runtime-shader-target-match.json

python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json
python shift_importer.py sgb-placement-join \
  out/sgb-runtime.json out/placement-join.json
python shift_importer.py sgb-scene-placement \
  out/placement-join.json out/scene-placement.json

python shift_importer.py sgb-object-render-handoff \
  out/sgb-runtime.json out/object-render-handoff.json
python shift_importer.py sgb-render-binding-admission \
  out/scene-placement.json out/object-render-handoff.json \
  out/scene-render-admission.json
python shift_importer.py sgb-render-binding-bridge \
  out/scene-render-admission.json out/ir \
  out/scene-render-binding.json

python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json
python shift_importer.py sgb-placement-join \
  out/sgb-runtime.json \
  out/sgb-placement.json

python vehicle_physics_bundle.py BMW_M3_E36.bff out/bmw_physics
python tools/build_vehicle_physics_handoff.py BMW_M3_E36.bff out/bmw_handoff
python tools/build_vehicle_physics_participant_gate.py -o participant_gate.json
python tools/build_physics_participant_manager_event.py -o physics_participant_manager_event.json
python tools/build_vehicle_physics_participant_process.py -o participant_process_reselect.json
python tools/build_vehicle_physics_selector_candidate_lifecycle.py -o selector_candidate_lifecycle.json
python tools/build_igphasevehicle_finalization.py -o igphasevehicle_finalization.json
python tools/build_vehicle_physics_selector_descriptor_population.py -o selector_descriptor_population.json
python tools/build_vehicle_physics_selector_source_admission.py -o selector_source_admission.json
python tools/preflight_specialized_provider_capture.py SHIFT.zip out/provider-capture --probe-script tools/gdb_sdf_solver_probe.py

./shift-bff-viewer /path/to/BMW_M3_E36.bff
```

## Physics participant registry/update

Phase 505 records the `IGPhaseVehicle → FUN_00410ef0 → wait/success → Pakfiles/Vehicles/%s.bff` control flow without assigning a PhysX class identity. See `docs/PHASE505_VEHICLE_PHYSICS_PARTICIPANT_GATE.md`.

Phase 506 records `FUN_0070e1c0 → opcode 0x20 → FUN_00714560(DAT_00c109e0) → manager +0x39c = 1` as a separate source-backed evidence layer. It intentionally does not assert that this manager object is the exact registry consumed by `FUN_00410ef0`. See `docs/PHASE506_PHYSICS_PARTICIPANT_MANAGER_EVENT.md`.

Phase 507 records the concrete participant slot array (`DAT_00c109e0+0x140`, stride `0x1fa0`) and the `FUN_00713f40`/`FUN_00713ec0` calls from `PhysicsParticipant.cpp`. Phase 508 establishes that `thunk_FUN_00453990` returns `DAT_00bbc600`, leaving the selector object separate from `DAT_00c109e0`. Phase 509 then proves that `IGPhaseVehicle+0x450/+0x454` are consumed by `FUN_004d5f30`, which processes the current pointer, reselects from `DAT_00bbc600`, loads the next vehicle BFF and writes back the new pointer/ordinal only after successful load. Phase 510 closes the repeated descriptor record lifecycle at `context+0xb8` with `0x90` stride: `FUN_0040eec0` initializes `+0x74 = 1`, `FUN_00410ef0`/`FUN_0043af50` select only `+0x74 == 0` entries, `FUN_0043af50` writes `+0x8c` ordinals, and `FUN_004d69d0` temporarily reasserts `+0x74 = 1` during bounded batch collection before resetting it. `FUN_00465860` separately writes `+0x1d = 1` after its observed load/process step.

## Current validation and blockers

Phase 548 is on main with OBJECT resource/transform handoff, Phase 549 closes the direct FLAT `+0x20..+0x34` query consumer, Phase 550 reconstructs static MultiMatrix arithmetic, Phase 551 reconstructs constructor/root SceneGraph transport state, Phase 552 joins placement to numeric OBJECT handoffs, Phase 553 feeds admitted MEB instances into generic `SHIFT.RenderBinding/1`, and Phase 554 maps the retail MeshType/type-0 versus MeshInst/type-7 resource factory plus the `.imb/.imx` promotion and type-7 render branch. MatrixNumber rows with unknown per-instance update history remain fail-closed before the resource bridge.

The main evidence blockers are independent:

- **BMW rendering:** one authentic BMW M3 E36 D3D9 body capture is required to select the concrete retail FXO permutations from the Phase 538–540 target/match pipeline;
- **specialized vehicle physics:** one authentic provider frame is required for numeric parity beyond the source-backed 40/34-scalar structural reconstruction;
- **track/path runtime:** one complete non-stopping runtime graph capture is required to close the AIW → runtime → `AIPolylinePath` instance graph;
- **scene:** admitted MEB and v0.4 IMB rows enter generic `SHIFT.RenderBinding/1`; the complete supplied Silverstone IMB/BMT/DDS/FX/FXO dependency surface and all 428 primitive shader-ranking contexts are production-validated. All 428 remain statically ambiguous, but Phase 568 reduces the runtime search surface to a complete 51-pixel-hash whitelist, Phase 569 prefilters raw D3D9 draws by that whitelist, Phase 570 supplies exact IMB SHA + indexed draw ranges for every binding, and Phase 571 preserves declaration descriptors plus every collapsed VS/PS candidate variant; the remaining shader blocker is an authentic runtime same-instance observation; per-instance SceneGraph update history, native scene loading and the non-Silverstone IMX adapter remain separate.

Missing runtime evidence remains a blocker rather than a reason to choose a plausible value.

## Repository map

| Path | Purpose |
|---|---|
| `shift_importer.py` | importer and analysis CLI |
| `src/formats/` | BFF-adjacent resource, material, geometry and collision parsers |
| `src/render/` | neutral DrawPacket/StaticDraw/RenderCommand contracts and reference rendering |
| `src/bmw/` | BMW retail admission, shader attribution, Vulkan bundle and capture evidence |
| `src/scene/` | SGB NODE/SUMM/PART/OCCL/FLAT runtime reconstruction |
| `src/track/` | TrackDetails/TrackList metadata, loading, taxonomy and lookup runtime contracts |
| physics runtime modules | vehicle/constraint/solver evidence |
| `native_capture/` | Windows D3D9 capture producer |
| `native_vulkan/` | Linux Vulkan backend |
| `tools/` | capture/evidence utilities |
| `tests/` | regression suite |
| `docs/PHASE*.md` | historical phase records |

Historical phase records are intentionally not rewritten retroactively. Current status belongs in the operational documents.

Phase 558 corrects IMB stream storage to descriptor-then-vertices blocks, preserves supported raw vertex payloads and locates the primitive section. See `docs/PHASE558_IMB_STREAM_PAYLOAD.md`.

Phase 559 optionally decodes proven v0.4 IMB material/palette/index/bounds primitive records through `--decode-primitives`. See `docs/PHASE559_IMB_PRIMITIVES.md`.
