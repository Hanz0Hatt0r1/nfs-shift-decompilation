# Specialized provider status

## Current boundary

`SHIFT.exe.c` source-shape + dispatch/selector evidence + runtime provider capture
are joined by `SHIFT.SpecializedProviderCaptureHandoffRuntime/1`.

## Handoff contract

The handoff contract and Phase 501 mutation-correlation layer:

- keeps `observed_provider_id` runtime-authoritative;
- attaches a source-derived provider solver program only when provider ids match;
- preserves the full capture-bundle contract as a separate evidence layer;
- validates source-derived solver programs independently of the capture;
- remains blocked when the runtime provider id is absent or mismatched;
- correlates packed-workspace change addresses with source-derived factor edges while preserving alias sets.

Use:

`python tools/verify_specialized_provider_capture_handoff.py SHIFT.exe.c <capture-dir> --observed-provider-id <0|1> --reset-events scalar_reset_events.jsonl`

For pre/post mutation correlation:

`python tools/compare_specialized_provider_mutations.py --pre provider_pre_0_000001.json --post provider_post_0_000001.json --source SHIFT.exe.c --provider 0 -o mutation_correlation.json`

Optional `-o` writes the complete handoff manifest.

## Numeric boundary

This is a linkage contract, not numeric proof. Retail/provider numerical equivalence
still requires a real pre/post runtime frame and differential comparison of the
captured packed workspace/output vectors.

## Runtime capture preflight

`SHIFT.SDFRuntimeProbePreflight/1` now validates the retail PE/prologue targets,
probe script, Wine, GDB and GDB Python before an attach is attempted. It never
launches the game or guesses a PID.

CLI:

`python tools/preflight_specialized_provider_capture.py SHIFT.zip out/provider-capture --probe-script tools/gdb_sdf_solver_probe.py`

The preflight now also validates the probe source contract before an attach:
GDB import, `sdf-probe` command, provider pre/post capture outputs, scalar-reset
capture and the provider snapshot builder must all be present. The CLI exposes this
as `probe_script_valid`.

The supplied `shift.zip` contains a PE32/i386 `SHIFT.exe` whose SHA-256 is
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, matching
the retail executable fingerprint already enforced by the PE validator. The current
analysis environment still lacks Wine and GDB, so authentic runtime capture remains
externally gated.

## Pre-PhysX handoff

`SHIFT.PrePhysXProviderHandoffRuntime/1` now validates the shared construction,
pre-acceptance, provider-selection, storage-rebind and vtable-lifecycle offsets
across the existing static contracts. A same-dimension provider is only a
candidate; runtime `+0x14` acceptance remains authoritative.

CLI:

`python tools/build_prephysx_provider_handoff.py sdf_report.json -o prephysx_provider_handoff.json`

## Vehicle physics participant gate

Phase 505 adds `SHIFT.VehiclePhysicsParticipantGate/1`, capturing the source-backed
`IGPhaseVehicle → FUN_00410ef0 → wait/success → Pakfiles/Vehicles/%s.bff` boundary.
It records the participant pointer/index writeback slots and the observed candidate
eligibility condition without naming an engine/PhysX class. The runtime participant
instance is still capture-dependent.

## PhysicsParticipantManager event path

Phase 506 adds `SHIFT.PhysicsParticipantManagerEvent/1`, covering the source-backed
`FUN_0070e1c0 → opcode 0x20 → FUN_00714560(DAT_00c109e0)` path and the observed
manager-ready write at `+0x39c = 1`. This remains a separate evidence layer:
the decompilation does not yet prove that `DAT_00c109e0` is the exact registry
returned by `thunk_FUN_00453990` and consumed by `FUN_00410ef0`.

CLI:

`python tools/build_physics_participant_manager_event.py -o physics_participant_manager_event.json`

## Participant registry/update bridge

Phase 507 adds `SHIFT.PhysicsParticipantRegistryUpdate/1`, covering the concrete participant slot allocation, registration and refresh routines on `DAT_00c109e0`. `FUN_007146c0` allocates indexed slots at `+0x140` with `0x1fa0` stride; `FUN_00713f40` enables/records the descriptor index; `FUN_00713ec0` refreshes the indexed slot. `PhysicsParticipant.cpp` calls both for participant descriptor type `3`.

The selector-context identity from Phase 505 remains unproven.

CLI:

`python tools/build_physics_participant_registry_update.py -o physics_participant_registry_update.json`

## Selector-context separation

Phase 508 adds `SHIFT.VehiclePhysicsSelectorContext/1`. The source-backed accessor `thunk_FUN_00453990 → FUN_00402435` returns `DAT_00bbc600`; that global is initialized by `FUN_00410490`, its selector storage is at `+0x9fc`, and shutdown is handled by `FUN_00411430`.

This is separate from the `DAT_00c109e0` object used by the Phase 506-507 PhysicsParticipantManager event/registry APIs. No higher-level object identity is inferred between them.

CLI:

`python tools/build_physics_selector_context.py -o physics_selector_context.json`

## Participant process/reselection loop

Phase 509 adds `SHIFT.VehiclePhysicsParticipantProcessReselect/1`. `FUN_004d5f30` consumes the current pointer at `IGPhaseVehicle+0x450` through `FUN_00468ed0`, then directly calls `FUN_00410ef0(&DAT_00bbc600, &local_8)`. A successful next selection is loaded from `Pakfiles/Vehicles/%s.bff`, and only after that load succeeds are `+0x454` and `+0x450` overwritten with the new ordinal/pointer.

This directly closes the Phase 505 output slots against the Phase 508 selector object and preserves the distinction from `DAT_00c109e0`.

CLI:

`python tools/build_vehicle_physics_participant_process.py -o participant_process_reselect.json`

## Current next step

Capture a real provider frame, verify the bundle, then use the handoff and Phase 501
correlation report to classify observed packed-workspace mutations against the
source-derived execution program.


For low-stop capture, `preflight_specialized_provider_capture.py` and `run_sdf_solver_probe.py` accept `--provider-only`. This mode omits builtin/per-frame solver breakpoints and keeps provider solve/reset and scalar-reset hooks.
