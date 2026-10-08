# Phase 745 scope

In scope:

- consume merged Phase744 typed `CollisionQueryOutput` in `NativeVehicleProviderSession`;
- derive the Phase744 query-scalar handoff from that same pass;
- reuse Phase743 selected BMW `HDVehicle+0x38f0` application-point ownership;
- pass both values into the still-external `FUN_00766510` callback after the per-pass wheel update;
- fail closed on the selected BMW path if either input is missing;
- preserve pass-only historical test fixtures through an explicit compatibility adapter.

Out of scope:

- removing the complete `contact_response` provider;
- reducing the active provider count below seven;
- internalizing all `FUN_00766510` conditional branches;
- internalizing the primary caller-accumulator delta at `+0x40a0/+0x40a8/+0x40b0`;
- internalizing the collision/world lookup provider beneath `FUN_007b0710`;
- assigning physical meaning or units to the caller fields.
