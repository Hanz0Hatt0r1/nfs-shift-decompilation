# Phase 743 next blocker

Phase743 makes the selected BMW `FUN_007b0710` result explicit and validates the source-visible cache/output relationship. It also provides the native `HDVehicle+0x38e0` projection plus the first `FUN_00766510` clamp, but deliberately does not change session/provider wiring.

## Phase744 target

Thread the selected per-pass `CollisionQueryOutput` through `NativeVehicleProviderSession` at the recovered anchor order and pass a typed `Fun00766510QueryScalarHandoff` into the still-external `FUN_00766510` contact-response remainder.

The safe contract should preserve generic historical fixtures while requiring the selected BMW path to consume:

- the exact `CollisionQueryOutput` returned by the preceding residual `FUN_00765c40` pass;
- native `HDVehicle+0x38e0` hit/miss projection;
- the same selected native `HDVehicle+0x38e8` value as the upper clamp bound;
- the exact first `[0,+0x38e8]` clamp before external remainder execution.

Do **not** reduce the provider count in Phase744 unless the entire residual `FUN_00766510` callback is removed. Phase742 already closes the primary BODY application, but caller configuration, `+0x40a0/+0x40a8/+0x40b0` accumulation, auxiliary scheduling and additional conditional branches remain separate source-backed targets.

Separately, the collision/world provider below `FUN_007b0710` remains external and can be pursued through `FUN_0074f560` / the PhysX scene boundary without conflating that work with the contact-response handoff.
