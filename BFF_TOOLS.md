# BFF / corpus tooling

The project keeps archive inventory, raw payload parity, content-addressed reuse,
decoded physics profiling, and shader-corpus profiling as separate evidence layers.

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
