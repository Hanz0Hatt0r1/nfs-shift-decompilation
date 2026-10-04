# Phase 706 — persistent BMW vehicle world-transform state

## Purpose

Phase 706 persists the Phase 705 `VehicleWorldMatrix` together with the exact
persistent BODY0 provenance that produced it.

```text
Phase 705 admitted world matrix
-> transactional commit
-> persistent vehicle transform + source BODY0 provenance
-> freshness check against current NativeRuntimeState
```

No original `SHIFT.exe` execution or new runtime capture is used.

## Contract

```text
SHIFT.PersistentBMWVehicleWorldTransform/1
```

The state records:

```text
ready
BODY index
source runtime BODY count
source pose snapshot generation
source explicit-update count
source BODY0 origin
source BODY0 basis
transform commit generation
Phase 646 VehicleWorldMatrix
```

## Transactional commit and freshness

`commit_bmw_vehicle_world_transform(...)` executes the complete Phase 705 path
before publishing a new state. A failure leaves the previous commit unchanged.
Commit-generation overflow fails closed.

`read_current_bmw_vehicle_world_transform(...)` accepts the state only when the
current runtime still matches:

- BODY index 0;
- BODY cardinality;
- pose snapshot generation;
- explicit-update count;
- exact BODY0 origin;
- exact BODY0 basis.

The exact origin/basis comparison is required because reinitialization can reuse
zero generations with different BODY bytes.

## Retail identity after Process 1 #1208

Retail BODY-owner identity is now positive. Phase 707 adds:

```text
commit_retail_bmw_vehicle_world_transform(
    state,
    runtime,
    vhf_bind,
    body0_bind)
```

which consumes the committed `SHIFT.GlobalVehicleBodyOwnerIdentity/1` producer
internally. A retail caller therefore no longer injects BODY identity flags.

The remaining transform-semantic blocker is the independent
`SHIFT.BMWBody0BindFrameProof/1`. Until that proof is positive, retail code still
cannot publish a world matrix. Tests may use a synthetic bind only to regress
transport and transactional behavior; it is not retail evidence.

## Renderer side

Process 3 Phases 647/648/649 are already merged. In particular Phase 649 consumes
this exact persistent state through:

```text
read_current_bmw_vehicle_world_transform(...)
-> wait in-flight Vulkan fences
-> Phase 647 live vehicle vertex upload
```

Stale Phase 706 state therefore fails before GPU memory mutation.

## Scheduling boundary

Phase 706/707 do not automatically commit a transform from
`NativeRuntimeState::fixed_step()`. The deep explicit outer-update cadence owner
remains evidence-gated. After any future explicit physics update, the old
transform becomes stale until an explicit recommit succeeds.

## Regression coverage

Python and native regressions now use the Phase 707 retail identity wrapper and
verify:

- retail identity passes without a caller-supplied handoff;
- missing BODY0 bind stops publication transactionally;
- successful test-only bind commit/read;
- stale generation/count rejection;
- changed pose with reused generations rejection;
- failed recommit preservation;
- transform-generation overflow rejection.

## Next blocker

The shortest transform path to visible retail movement is now:

```text
source-backed BODY0 bind initialization/writer provenance
-> positive SHIFT.BMWBody0BindFrameProof/1
-> Phase 704/705 composition
-> Phase 706 retail persistent matrix
-> Phase 649 live Vulkan upload
```

Exact outer-update scheduling and unresolved Phase 699/701 physics producers are
separate blockers and remain fail-closed.
