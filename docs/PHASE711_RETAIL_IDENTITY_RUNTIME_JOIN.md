# Phase 711 — retail archive identity runtime join

## Playable-slice blocker removed

Process 3 already proves exact retail archive identity for the first playable
Silverstone + BMW target through:

```text
SHIFT.RetailArchiveIdentityAdmission/1
```

That gate requires exact archive name + retail SHA-256 + one unique catalog
occurrence before the offline native scene/vehicle path is admitted.

The remaining Process 2 gap was downstream consumption. A later runtime
requirements/profile path could still accept independently valid explicit scene,
physics or participant files without preserving the Process 3 admission that
made those resource-bound artifacts legal for this target.

Phase 711 closes that consumer-side gap:

```text
Process 3 exact retail archive admission
  -> SHIFT.OfflineRuntimeBootstrap/1
  -> SHIFT.OfflineNativeRuntimeRequirements/1
  -> SHIFT.NativeVerticalSliceProfile/1
  -> run_native_vertical_slice.py
  -> native runtime execution
```

No archive hash is recomputed by Process 2 and no parser/resource ownership is
moved out of Process 3.

## Requirements gate

`src/resources/offline_runtime_requirements.py` now consumes the existing
bootstrap admission and requires all of the following before resource-bound
runtime inputs can remain ready:

- `readiness.retail_archive_identity_ready == true`;
- a `stages.retail_archive_identity_admission` object exists;
- its format is `SHIFT.RetailArchiveIdentityAdmission/1`;
- it is `ready == true`;
- its `track` equals the bootstrap target;
- its `vehicle` equals the bootstrap target;
- the bootstrap exposes the persisted admission artifact path.

The gate applies to:

```text
scene_set
physics_manifest
participant_boundary
```

A validated explicit path cannot override a failed retail identity admission.
Camera/BODY-feedback evidence remains independently runtime-evidence-gated and is
not relabeled as archive-derived.

## Profile propagation

When runtime requirements state that retail identity is required,
`offline_vertical_slice_profile.py` refuses to build a profile unless the
admission is ready and its artifact exists inside `workspace_root`.

The generated profile carries only the Process 3 result and target labels:

```text
track
vehicle
retail_archive_identity_admission
```

It does not contain or derive retail SHA values.

Legacy/manual profiles that do not carry `retail_archive_identity_admission`
remain compatible. Phase 711 changes the generated playable path, not the
meaning of unrelated manual validation profiles.

## Launch-time fail-closed revalidation

`tools/run_native_vertical_slice.py` reopens the propagated admission immediately
before composing the launch plan and requires:

```text
format == SHIFT.RetailArchiveIdentityAdmission/1
ready == true
admission.track == profile.track
admission.vehicle == profile.vehicle
```

This catches stale or replaced admission artifacts between bootstrap/profile
creation and launch. Process 2 deliberately trusts the Process 3 `ready` result;
it does not reproduce the archive-name/SHA/occurrence algorithm.

The launch plan reports:

```text
checks.retail_archive_identity_admission
boundary.retail_archive_identity_revalidated = true
boundary.retail_archive_identity_rederived_by_process2 = false
```

for generated profiles carrying this contract.

## Deliberate non-claims

Phase 711 does not make any of these ready:

- `SHIFT.BMWBody0BindFrameProof/1`;
- persistent retail BMW world-transform production;
- provider-present dispatch;
- drivetrain/input semantics;
- retail outer-update cadence;
- missing renderer external sampler snapshots.

The latest Process 1 construction-store pass still leaves
`BODY0_bind_frame_proof_ready=false`, so no vehicle transform integration is
invented here.

## Regression coverage

The Phase 711 tests verify:

- a ready exact admission preserves resource-bound runtime requirements;
- a failed or target-mismatched admission clears scene/physics/participant
  readiness;
- validated explicit resource paths cannot bypass the failed gate;
- generated profiles propagate the admission and target labels;
- profile creation fails when the required admission is not ready;
- launcher validation succeeds for the exact propagated admission;
- launcher validation fails if the admission becomes not-ready or target-mismatched
  after profile creation;
- legacy profiles without the new field remain covered by the existing launcher
  regressions.
