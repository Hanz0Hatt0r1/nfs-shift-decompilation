# Phase 642 — runtime requirement admission ledger

## Playable-slice blocker reduced

After Phase 640/641, the Process 3 one-command path can materialize a prepared
runtime-proven scene set and can exhaust existing capture snapshots before
leaving a renderer-resource blocker.

The remaining requirements report still had a diagnostic defect: explicit
runtime artifacts and input choices were always listed as missing even when the
same files would pass `tools/run_native_vertical_slice.py`.

Phase 642 separates three states that were previously collapsed:

```text
path supplied
  != admitted runtime evidence
  != pipeline-proven artifact
```

and exposes the requirement ledger as:

```text
READY
MISSING
AMBIGUOUS
RUNTIME-EVIDENCE REQUIRED
```

## Exact admission boundary

`src/resources/runtime_input_validation.py` reuses the launcher validators for:

- prepared `NativeSceneVulkanSet` directories;
- JSON runtime contracts, including the participant identity gate;
- `SBFR`, `GBCF`, `CSRF`, `CRRF`, and `SBPS` binary packets;
- `SHIFT.NativeRuntimeInputScript/1`;
- explicit keyboard / interactive input mode selection.

The validator emits `SHIFT.OfflineValidatedRuntimeInput/1` rows. File existence
alone is never enough to produce `ready=true`.

`tools/validate_native_vertical_slice_runtime_inputs.py` remains a compatibility
entrypoint and routes through the shared validator.

## Requirements semantics

`SHIFT.OfflineNativeRuntimeRequirements/1` now accepts only prevalidated explicit
rows. A valid explicit artifact can satisfy a requirement, but it retains:

```text
artifact_origin = explicit-validated
```

so profile preparation does not relabel it as resource-pipeline proof.

If a pipeline-proven artifact already exists, a different validated explicit
artifact cannot override it. The requirement becomes `AMBIGUOUS` and remains a
launch blocker.

Absent camera / participant / BODY-feedback runtime evidence is reported as
`RUNTIME-EVIDENCE REQUIRED`, not as generic resource absence. Missing scene or
input selection remains `MISSING` unless another exact classifier applies.

## Offline bootstrap integration

`build_offline_vertical_slice_bootstrap()` now validates explicit inputs before
building the requirements ledger. The selected offline resource bootstrap remains
a hard gate: even fully valid explicit runtime artifacts cannot bypass a blocked
track/vehicle resource bootstrap.

The report carries the validation rows under:

```text
stages.validated_runtime_inputs
```

and preserves launcher validation as a separate final gate.

## Process 1 / Process 2 boundaries preserved

Phase 642 does **not** close the current physics identity/scheduling blockers.
In particular, Process 1 PR #1176 proves that the update-child, global outer
receiver, BODY-array owner, and persistent lifetime vehicle pointer are distinct
pointer domains whose exact joins are still evidence-gated.

Therefore Phase 642 does not:

- select a BODY for the concrete retail vehicle;
- infer BODY-to-render-object identity;
- infer vehicle world-transform convention;
- schedule the Phase 697 explicit outer-update path from fixed-step cadence;
- synthesize machine scalar producers;
- generate camera or BODY-feedback packets.

It only makes the blocker ledger truthful about evidence already supplied and
accepted by the native launcher contracts.

## Regression coverage

New tests cover:

- validated explicit runtime evidence -> `READY`;
- missing camera/BODY evidence -> `RUNTIME-EVIDENCE REQUIRED`;
- conflicting proven/explicit scene artifacts -> `AMBIGUOUS`;
- invalid explicit artifacts never become ready;
- keyboard and input-script admission through launcher-equivalent validation;
- participant identity requirements identical to the launcher gate;
- workspace escape rejection;
- blocked offline bootstrap cannot be bypassed by explicit runtime inputs.

No original game execution and no new runtime capture are introduced.
