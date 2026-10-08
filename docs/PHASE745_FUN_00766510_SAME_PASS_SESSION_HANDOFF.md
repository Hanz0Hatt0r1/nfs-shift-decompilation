# Phase 745 — `FUN_00766510` same-pass session handoff

Phase 745 wires the already-proven selected BMW collision result and primary application-point owner into the still-external `FUN_00766510` contact-response boundary at the recovered per-pass anchor order.

## Reused proofs

No new collision or physical semantics are introduced.

The phase reuses:

- Phase744 `CollisionQueryOutput` exported from the same `FUN_00765c40` pass;
- `SHIFT.Fun00766510QueryScalarHandoff/1`, which produces the source-visible `+0x38e0` scalar, shares the selected `+0x38e8` limit and performs the first `[0,+0x38e8]` clamp;
- Phase743 selected BMW ownership of `HDVehicle+0x38f0` as the existing Phase727 `body_rotated_local` scratch.

## Session wiring

`SHIFT.Fun00766510ExternalPassInput/1` carries:

- `selected_bmw_domain`;
- optional same-pass `Fun00766510QueryScalarHandoff`;
- optional primary application point.

Within each recovered `FUN_0076d100` pass, `NativeVehicleProviderSession` now performs:

```text
current BODY observer
  -> selected BMW world-position/application-point owner
FUN_00765c40 residual provider
  -> typed CollisionQueryOutput
  -> same-pass query-scalar handoff
FUN_00758b50
FUN_00766510 residual provider
  <- typed same-pass handoff + selected +0x38f0 application point
```

The selected BMW path fails closed if the collision output, scalar handoff or application point is unavailable. Historical synthetic two-BODY fixtures are not reclassified as the selected BMW domain; their pass-only callbacks are adapted to the typed provider signature for compatibility.

## Scope

The `contact_response` provider is **not removed** in this phase. `FUN_00766510` still contains source-visible work beyond the Phase742 primary response application, including caller accumulator updates, auxiliary scheduling and additional conditional response branches.

The active top-level provider count therefore remains **7**.

## Next target

Phase746 should close the primary caller-accumulator delta immediately after the Phase742 BODY application: the source calls `FUN_00753650(application_point, transformed_response)` and accumulates the resulting vec3 into `HDVehicle+0x40a0/+0x40a8/+0x40b0`.
