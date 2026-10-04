# Phase 707 — retail global vehicle BODY-owner identity producer

## Playable-slice blocker removed

Process 1 #1208 makes `SHIFT.GlobalVehicleBodyOwnerIdentity/1` positive for the
retail BMW. Before this phase, Process 2 still reconstructed that positive state
manually in tests/callers as a `GlobalVehicleBodyOwnerIdentityHandoff`.

Phase 707 removes that injected identity input from the retail transform path.

```text
Process 1 #1208 retail proof
  -> native retail identity producer
  -> Phase 703 validation
  -> Phase 698 BODY 0 selection
  -> Phase 700 persistent BODY pose
  -> Phase 705/706 world-transform path
```

No original game execution and no new runtime capture are used.

## Native contract

```text
SHIFT.NativeRetailGlobalVehicleBodyOwnerIdentity/1
```

Files:

```text
native_runtime/include/shift_retail_global_vehicle_body_owner_identity.hpp
native_runtime/src/retail_global_vehicle_body_owner_identity.cpp
```

The producer freezes only values already committed by Process 1 #1208:

```text
global_vehicle_address                         = 0x00c13700
BODY_owner_pointer_field_offset                = 0x339c
BODY_array_owner_is_global_vehicle_base        = false
BODY_array_owner_pointer_loaded_from_vehicle   = true
selected_BODY_index                            = 0
phase698_positive_selection_admissible         = true
phase700_runtime_handoff_admissible            = true
obsolete update-child equality gate            = false
```

The distinction between the global vehicle base and the BODY-array owner pointer
is preserved. Phase 707 does not collapse the pointer loaded from `+0x339c` into
the base object.

## Deeper retail wrappers

Phase 707 adds wrappers whose signatures no longer accept a caller-supplied
identity handoff:

```text
build_retail_bmw_vehicle_world_matrix_runtime_handoff(
    runtime,
    vhf_bind,
    body0_bind)

commit_retail_bmw_vehicle_world_transform(
    state,
    runtime,
    vhf_bind,
    body0_bind)
```

Both internally consume the native #1208 producer and reuse the existing Phase
705/706 implementation. This removes one injected boundary without creating a
second transform implementation.

## Remaining fail-closed boundary

Retail BODY-owner identity is now positive, but the retail transform is still
blocked by the independent source-backed `SHIFT.BMWBody0BindFrameProof/1`.

Phase 707 therefore preserves this ordering:

```text
retail BODY owner identity     proven
Phase 700 BODY0 pose           available when runtime BODY state exists
Phase 645 VHF bind             proven
BODY0 bind frame               BLOCKED
Phase 704 composition          waits for BODY0 bind proof
Phase 706 commit               explicit only
Phase 649 Vulkan upload        freshness-gated consumer ready
```

Tests may use a synthetic proven BODY0 bind solely to verify that the newly
promoted retail identity reaches the existing Phase 705/706 path. That fixture
is explicitly not retail proof.

## Scheduling and physics providers

Phase 707 does not attach the explicit outer-update chain to `fixed_step()` and
does not replace any of the nine Phase 699/701 physics producer boundaries.
Machine scalar sqrt/trig/x87 inputs remain evidence-gated.

## Regressions

Python reference coverage:

- checks `evidence/global_vehicle_body_owner_identity_retail.json` against the
  reference producer;
- proves BODY 0 selection is now the current retail path;
- keeps malformed/blocked/obsolete-gate fixtures fail-closed.

Native coverage:

- validates exact `0x00c13700` / `+0x339c` / BODY 0 constants;
- transports the retail identity through Phase 700 without mutating runtime
  BODY state;
- proves missing BODY0 bind fails after identity admission;
- with a test-only bind fixture, reaches Phase 705 and Phase 706 without a manual
  identity argument.

## Next blocker

The next transform-semantic blocker is now exactly:

```text
source-backed BODY0 bind initialization/writer provenance
-> positive SHIFT.BMWBody0BindFrameProof/1
-> retail Phase 704 composition
-> retail Phase 706 persistent matrix
-> Phase 649 live Vulkan upload
```

Exact deep-physics scheduling and unresolved provider producers remain separate
parallel blockers.
