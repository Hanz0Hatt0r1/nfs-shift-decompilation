# Phase 705 — BMW vehicle world-matrix runtime handoff

## Purpose

Phase 705 joins the existing selected persistent BODY pose to the exact Phase 704
BODY0/VHF composition and returns the Phase 646 `VehicleWorldMatrix` ABI.

```text
Phase 703 identity admission
-> Phase 700 persistent BODY0 pose
-> Phase 704 VHF_bind * inverse(BODY0_bind) * BODY0_runtime
-> Phase 646 VehicleWorldMatrix
```

The generic Phase 705 operation still accepts an explicit
`GlobalVehicleBodyOwnerIdentityHandoff` so malformed/alternative contracts can be
regressed. Phase 707 adds the retail wrapper that removes that injected argument.

No original `SHIFT.exe` execution or new runtime capture is used.

## Contract

```text
SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1
```

The handoff transports:

```text
SelectedVehicleBodyPose
BODY0 runtime row matrix
VehicleWorldMatrix
runtime BODY count
explicit outer-update count
```

It contains no new matrix arithmetic, trig, sqrt, or machine-scalar producer.

## Retail identity after Process 1 #1208

The BODY-owner identity is now positive:

```text
global vehicle 0x00c13700
-> pointer field +0x339c
-> BODY-array owner
-> BMW chassis BODY 0
```

Phase 707 exposes:

```text
build_retail_bmw_vehicle_world_matrix_runtime_handoff(
    runtime,
    vhf_bind,
    body0_bind)
```

so a retail caller no longer supplies identity flags manually.

Phase 703/700 validation is still reused unchanged. In particular the owner
pointer loaded from `+0x339c` is not treated as equal to the global vehicle base,
and the obsolete update-child equality gate remains forbidden.

## Remaining fail-closed transform input

The retail path is **not** yet a positive world-matrix producer because the
source-backed `SHIFT.BMWBody0BindFrameProof/1` remains unresolved.

Phase 705 therefore preserves the order:

```text
retail identity (positive)
-> Phase 700 runtime pose admission
-> BODY0 bind proof (currently blocked)
-> Phase 704 composition
```

A missing BODY0 bind is rejected before any matrix is returned. No identity bind
or axis-remap assumption is allowed.

## Regression coverage

Python and native regressions now use the Phase 707 retail identity wrapper.
They verify:

- retail BODY 0 is selected without a caller-supplied identity handoff;
- uninitialized persistent runtime state remains rejected by Phase 700;
- missing BODY0 bind proof remains rejected by Phase 704;
- a test-only bind fixture reaches the existing exact composition;
- successful and failed reads do not mutate persistent BODY state.

The test-only bind fixture is not retail proof.

## Downstream state

Process 3 Phases 647/648/649 already provide live Vulkan upload and a
freshness-gated consumer of Phase 706 persistent matrices. Renderer transport is
therefore no longer the semantic blocker.

The next transform blocker is exactly:

```text
source-backed BODY0 bind initialization/writer provenance
-> positive SHIFT.BMWBody0BindFrameProof/1
```

Exact deep-physics scheduling and the remaining Phase 699/701 provider producers
remain separate blockers.
