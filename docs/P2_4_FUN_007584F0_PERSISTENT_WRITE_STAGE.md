# Process 2 P2.4 — `FUN_007584f0` persistent-write stage

This slice consumes the persistent-write portion of `SHIFT.Fun007584f0MachineSideEffectProof/1` without pretending the underlying x87/vector arithmetic has already been recovered.

PC retail proves exactly three persistent HDVehicle destinations for `FUN_007584f0`:

- wheel 0: `HDVehicle+0x0d40`;
- wheel 1: `HDVehicle+0x17c0` (`+0x0d40 + 0x0a80`);
- filtered float state: `HDVehicle+0x3420`.

For wheel indices 0 and 1, retail checks the matching per-wheel `+0x738` load term. A non-positive load writes a zero qword. A positive load writes the qword produced by the still-uninternalized transform/vector arithmetic. The final `+0x3420` write stores the scalar returned by `FUN_00783a30`.

`shift_fun_007584f0_persistent_write_stage.hpp` therefore accepts the two positive-branch qwords and the interpolation result explicitly, validates them, and owns only the proven branch/write behavior. This prevents Process 2 from inventing x87 stack provenance while still moving persistent-state mutation out of an opaque top-level callback.

This slice does not make `FUN_007584f0` fully native, does not remove `NativeVehicleExternalProviderBundle.fun_00765c40`, and does not change the seven-provider frontier.
