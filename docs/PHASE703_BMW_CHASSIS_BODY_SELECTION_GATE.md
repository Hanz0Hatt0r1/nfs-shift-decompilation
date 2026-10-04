# Phase 703 — global vehicle BODY-owner selection handoff

## Purpose

Phase 703 consumes `SHIFT.GlobalVehicleBodyOwnerIdentity/1` and translates it to
the existing Phase 698/700 BODY-pose selection path. It deliberately does not
infer a vehicle BODY from names, callgraph adjacency, or historical
`*record+0x340` pointer equality.

Native contract:

```text
SHIFT.NativeGlobalVehicleBodyOwnerSelection/1
```

Implementation:

```text
native_runtime/include/shift_global_vehicle_body_owner_selection.hpp
native_runtime/src/global_vehicle_body_owner_selection.cpp
```

## Retail status after Process 1 #1208

Process 1 #1208 closes the BODY-owner identity blocker with the committed retail
contract:

```text
global vehicle base 0x00c13700
  -> pointer field +0x339c
  -> BODY-array owner domain
  -> BMW chassis BODY 0
```

The owner object is **not** asserted to equal the global vehicle base. The proven
relation is a pointer load from `global_vehicle_base + 0x339c`.

The authoritative handoff is now positive:

```text
outer_receiver_to_BODY_owner_continuity_proven = true
vehicle_BODY_selection_ready = true
selected_BODY_index = 0
phase698_positive_selection_admissible = true
phase700_runtime_handoff_admissible = true
phase703_update_child_equality_gate_required = false
phase703_gate_rewrite_ready = true
```

Committed evidence:

```text
evidence/global_vehicle_body_owner_identity_retail.json
```

Phase 707 adds the native retail producer so callers no longer have to inject
these fields manually.

## Fail-closed validation retained

Phase 703 still rejects:

- a reintroduced update-child equality gate;
- readiness flags that do not move together;
- a blocked handoff that preclaims a BODY index;
- any positive selection other than retail BMW chassis BODY 0.

A successful handoff reuses:

```text
Phase 698 VehicleBodyIdentitySelection(BODY 0)
-> Phase 700 NativeRuntimeState persistent pose handoff
-> SelectedVehicleBodyPose(BODY 0)
```

No BODY bytes, snapshot generation, or explicit-update counters are mutated by
selection.

## Current downstream blocker

Retail identity is no longer the transform blocker. Process 2 already has:

```text
BODY0 selection/handoff        Phases 698/700/703
BODY0 -> vehicle matrix core   Phases 704/705
persistent matrix state        Phase 706
live Vulkan transport          Process 3 Phases 647/648/649
```

The remaining semantic transform input is the independent positive
`SHIFT.BMWBody0BindFrameProof/1` witness. Until that proof exists, Process 2 must
not assume an identity bind matrix or synthesize BODY0/VHF axes.

Exact outer-update scheduling also remains separate: this phase does not attach
the explicit deep physics path to `NativeRuntimeState::fixed_step()`.

## Regression coverage

Python and native regressions now consume the #1208 retail handoff and verify
BODY 0 selection through Phase 700. Separate malformed fixtures continue to
exercise blocked, contradictory, and obsolete-gate rejection.

No original `SHIFT.exe` execution or new runtime capture is used.
