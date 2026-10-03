# BFF / corpus tooling

The project keeps archive inventory, raw payload parity, content-addressed reuse,
decoded physics profiling, and shader-corpus profiling as separate evidence layers.

## Offline resource pipeline

Use the fail-closed high-level resource pipeline to turn one or more retail BFFs,
ZIP corpora, or BFF directories into a unified catalog, semantic dependency graph,
coverage report, scene/vehicle bootstrap, typed resource closure, and explicit native
runtime admission record:

`python tools/shift_resource_pipeline.py all Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/offline-pipeline --track Silverstone_Era3_GrandPrix --vehicle Ford_Mustang_2010`

Inventory-only and parser-validation modes are available through the `catalog`
subcommand. Dependency admission uses exact semantic parser references only.
Source-backed SGB `NODE`/`SUMM`/`OCCL` resource fields are admissible only when
the SGB runtime decode is fully ready; remaining string-scan candidates stay
diagnostic-only. Missing resources remain explicit, and a resource-ready bootstrap
does not bypass the existing render/physics/runtime provenance gates. See
`docs/OFFLINE_RESOURCE_PIPELINE.md`.

For the strongest currently proven resource-to-native bootstrap:

`python tools/bootstrap_runtime.py Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/runtime-bootstrap --track Silverstone_Era3_GrandPrix --vehicle BMW_M3_E36`

This also writes `runtime_requirements.json`, which separates already-proven
physics/participant artifacts from runtime scene, camera, BODY-feedback, and input
gates that still require explicit evidence.

To continue through fail-closed vertical-slice profile preparation in one command:

`python tools/bootstrap_native_vertical_slice.py Vehicles.zip Silverstone_Era3_.zip RENDER.bff -o out/native-vertical-slice --track Silverstone_Era3_GrandPrix --vehicle BMW_M3_E36 --workspace-root . --participant-observation /path/to/native_physics_participant_observation.json --scene-set out/native-scene-vulkan --camera-state out/native-camera-state.json --solver-frame out/solver.sbfr --generated-body-constraint-frame out/generated.gbcf --constraint-sample-relation-frame out/relations.csrf --constraint-relation-reset-frame out/reset.crrf --post-solve-projection out/post.sbps --keyboard --frames 120 --validate-launch-plan`

The command never supplies defaults for missing runtime evidence. A blocked selected
offline bootstrap cannot be bypassed by later explicit runtime paths, and optional
launch-plan validation delegates to `tools/run_native_vertical_slice.py` without
executing the native runtime.

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
