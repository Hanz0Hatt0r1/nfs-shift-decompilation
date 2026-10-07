# Phase 742 scope

In scope:

- freeze the PC retail `FUN_007551e0 -> FUN_007aefb0 -> FUN_007baa70` query-response application sequence inside `FUN_00766510`;
- reuse the proven `HDVehicle+0x33a0 -> selected BMW BODY0` identity;
- freeze `HDVehicle+0x38f0` as the source-visible second argument to `FUN_007baa70` without assigning a physical name or unit;
- reuse the existing machine-backed `FUN_007aefb0` transform implementation;
- reuse the existing native `FUN_007baa70` BODY accumulator primitive;
- consume `WheelContactResponse.response_vector` from the existing native `FUN_007551e0` result contract;
- independently corroborate the call topology against Xbox recomp partition 220.

Out of scope:

- internalizing all of `FUN_00766510`;
- removing `NativeVehicleExternalProviderBundle.contact_response`;
- reducing the top-level external-provider count below seven;
- deriving or generalizing selected values for `HDVehicle+0x38f0`, `+0x3908`, `+0x3910`, `+0x3918`, or the response tables;
- closing earlier or optional response branches in `FUN_00766510`;
- claiming the already-native auxiliary pair is fully scheduled/owned by current persistent runtime state;
- dropping diagnostics or caller-visible writes not covered by this exact source sequence.
