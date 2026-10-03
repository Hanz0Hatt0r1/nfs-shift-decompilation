# BFF / corpus tooling

The project keeps archive inventory, raw payload parity, content-addressed reuse,
decoded physics profiling, renderer evidence and native bootstrap admission as
separate evidence layers.

## Offline resource pipeline

Use the fail-closed high-level resource pipeline to turn one or more retail BFFs,
ZIP corpora, or BFF directories into a unified catalog, semantic dependency graph,
coverage report, scene/vehicle bootstrap, typed resource closure, corpus target
readiness report and explicit native resource admission record:

`python tools/shift_resource_pipeline.py all Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/offline-pipeline --track Silverstone_Era3_GrandPrix --vehicle BMW_M3_E36`

Inventory-only and parser-validation modes are available through the `catalog`
subcommand. Dependency admission uses exact semantic parser references only.
Source-backed SGB `NODE`/`SUMM`/`OCCL` resource fields are admissible only when
the SGB runtime decoder is ready; arbitrary SGB string-scan candidates remain
diagnostic-only. Missing resources stay explicit and a resource-ready bootstrap
does not bypass render/physics/runtime provenance gates.

`all` also writes `bootstrap_corpus_validation.json`. That report validates every
exactly discovered track/vehicle target through the normal fail-closed loaders,
but blocked unrelated targets do not change the admission state of the explicitly
selected pair.

See `docs/OFFLINE_RESOURCE_PIPELINE.md` for the full contracts and boundary.

## One-command Process 3 bootstrap

The highest-level offline entry point is:

`python tools/bootstrap_runtime.py Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/runtime-bootstrap --track Silverstone_Era3_GrandPrix --vehicle BMW_M3_E36`

It composes the resource pipeline, exact track/vehicle loaders, scene IR
materialization, selected SGB scene build, vehicle physics resource manifest and
source-backed participant structural boundary into
`SHIFT.OfflineRuntimeBootstrap/1`.

`offline_build_ready` means the currently provable offline/native resource stages
are complete. It does not mean the game runtime is ready. Use
`--require-runtime-ready` only when a strict exit gate on future proven runtime
scene + vehicle admission is desired; the tool never invents those proofs.

## High-level target validation

After catalog generation:

`python tools/validate_bootstrap_corpus.py out/offline-pipeline/resource_catalog.json out/offline-pipeline/dependency_graph.json -o out/offline-pipeline/bootstrap_corpus_validation.json`

Track candidates require an exact `<stem>.bff + <stem>_Physics.bff` pair. Vehicle
candidates use the existing CDF+EDF physics-corpus admission convention. Every
candidate still passes through `load_track` / `load_vehicle`; discovery alone is
not readiness.

## Scene IR and scene/vehicle builders

Materialize renderer IR from the original corpus:

`python tools/build_scene_ir.py Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/scene-ir`

Build the static/native scene resource chain from one selected raw SGB:

`python tools/build_native_scene.py path/to/scene.sgb out/scene-ir -o out/native-scene`

This uses an exact IR closure for SGB resource → IMB/IMX/MEB → BMT → FX/DDS.
Legacy basename fallback is not accepted as identity proof and tied FXO candidates
are not selected without exact evidence. Static RenderBinding is not promoted to
runtime draw admission.

Build vehicle resources from Process 3 outputs:

`python tools/build_native_vehicle.py out/offline-pipeline/resource_catalog.json out/offline-pipeline/scene_vehicle_bootstrap.json out/offline-pipeline/vehicle_physics_bundle_report.json -o out/native-vehicle`

The output includes `SHIFT.NativePhysicsParticipantBoundary/1`, which proves the
current participant registry/selector/process structure but deliberately does not
invent a concrete participant instance, registry index, selector ordinal or
provider identity.

## Vehicle corpus inventory

`python tools/audit_vehicle_bff_corpus.py Vehicles.zip -o vehicle_corpus.json`

This reads BFF headers and entry tables without decoding resource payloads.

## Raw payload parity

`python tools/audit_bff_payload_parity.py BMW_M3_E36.bff BMW_M3_E36_Cockpit.bff Vehicles.zip -o payload_parity.json`

A matching SHA-256 proves equality of the stored payload bytes for the compared
logical path. It does not prove decoded-resource or runtime-material equivalence.

## Raw payload reuse

`python tools/audit_bff_content_reuse.py BMW_M3_E36.bff BMW_M3_E36_Cockpit.bff Vehicles.zip -o payload_reuse.json`

This groups exact stored payload SHA-256 values across archives even when logical
paths differ. It is intended to find resource-deduplication candidates without
collapsing logical resource identity.

## Vehicle physics corpus

`python tools/profile_vehicle_physics_corpus.py Vehicles.zip -o physics_corpus.json`

Only archives containing both a base-physics CDF and EDF are selected. The command
delegates target resolution and all downstream parsing to `vehicle_physics_bundle.py`.

## FXO shader corpus

`python tools/audit_fxo_shader_corpus.py Vehicles.zip --summary-only -o fxo_corpus.json`

The profiler deduplicates exact raw FXO payloads before decoding them through the
canonical D3D9 parser.

Then:

`python tools/analyze_shader_opcode_gaps.py fxo_corpus.json -o shader_gaps.json`

The gap report lists only opcode operations actually observed in the corpus that
are not currently executable by the software shader oracle.

## Provider capture preflight

Before launching or attaching to a retail process, validate the executable and host:

`python tools/preflight_specialized_provider_capture.py SHIFT.zip out/provider-capture --probe-script tools/gdb_sdf_solver_probe.py`

The preflight checks the retail PE/prologues, probe script, Wine, GDB and GDB Python without starting or attaching to the game.

## Provider capture handoff

After a real runtime provider capture exists:

`python tools/verify_specialized_provider_capture_handoff.py SHIFT.exe.c <capture-dir> --observed-provider-id <0|1> --reset-events scalar_reset_events.jsonl -o provider_handoff.json`

The observed provider id is runtime evidence. The handoff attaches the corresponding
source-derived solver program only when ids match.

## Physics participant creation gate

The Phase 505 source-backed gate records the `IGPhaseVehicle` participant selection, the `-1` wait path, and the successful transition into `Pakfiles/Vehicles/%s.bff` loading:

`python tools/build_vehicle_physics_participant_gate.py -o participant_gate.json`

The gate intentionally does not assign a PhysX/provider class identity or a runtime participant instance.

## Physics participant registry/update

The Phase 507 contract records the participant slot allocation, registration and refresh routines used by `PhysicsParticipant.cpp`:

`python tools/build_physics_participant_registry_update.py -o physics_participant_registry_update.json`

The registry remains separate from the `FUN_00410ef0` selector context until object identity is proven.

## Participant process/reselection

The Phase 509 contract records the first concrete consumer of the participant pointer/ordinal saved by `IGPhaseVehicle`: current-pointer processing, direct reuse of selector global `DAT_00bbc600`, next vehicle-BFF loading, and successful `+0x450/+0x454` writeback:

`python tools/build_vehicle_physics_participant_process.py -o participant_process_reselect.json`

The contract does not name the selected object as a PhysX/engine class.

## Pre-PhysX/provider handoff

Build a cross-contract construction/selection/rebind validation from a parsed SDF report:

`python tools/build_prephysx_provider_handoff.py sdf_report.json -o prephysx_provider_handoff.json`

For a vehicle BFF, the complete extraction-to-handoff pipeline is:

`python tools/build_vehicle_physics_handoff.py BMW_M3_E36.bff out/bmw_handoff`

This produces the vehicle physics asset graph, the pre-PhysX/provider handoff and a top-level `SHIFT.VehiclePhysicsPrePhysXHandoff/1` manifest.

The result checks shared offsets and scalar dimensions while keeping runtime provider acceptance explicit.

## Provider mutation correlation

For a real pre/post provider capture, compare observed packed-workspace mutations
with source-derived factor edges without collapsing storage aliases:

`python tools/compare_specialized_provider_mutations.py --pre provider_pre_0_000001.json --post provider_post_0_000001.json --source SHIFT.exe.c --provider 0 -o mutation_correlation.json`

`status=correlated` means all observed workspace mutation addresses are covered by
at least one source-derived factor edge. `status=partial` preserves uncovered
observations without treating them as a source mismatch. No numeric parity is claimed.

## Native submission gate

`python tools/validate_native_submission.py render_command.json -o native_gate.json`

The same gate is available through `python shift_importer.py validate-native-submission ...`.
Native execution is blocked unless every submesh has complete FXO payload and permutation identity provenance.

## Resource manifest identity

Decoded resource manifests keep the legacy `sha256` field and add
`decoded_sha256` plus `raw_sha256`. The latter is the SHA-256 of the bytes
stored in the BFF entry before decryption/decompression.

This identity split is propagated by `extract`, `analyze-dir`, and `build-ir`
so downstream renderer/resource tooling can distinguish container-byte reuse from
decoded-resource identity.