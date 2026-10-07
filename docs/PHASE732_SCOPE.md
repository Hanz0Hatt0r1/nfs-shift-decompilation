# Phase 732 scope

Phase 732 is limited to the source-backed `FUN_007675f0 -> FUN_00759210` join and one directly adjacent machine-code correction.

In scope:

- derive the `FUN_00759210` query point from current chassis BODY origin `+0x00/+0x08/+0x10` with the source-visible f64-to-f32 spill;
- consume a typed external `SurfaceProbeNode*` equivalent to the PC `FUN_007675f0` first argument / `HDVehicle+0x120` value;
- execute the already-native `FUN_00759210` implementation;
- derive `planar_delta` from returned point minus BODY query point;
- derive `surface_scalar` from the probe's returned scalar;
- correct active gap arithmetic to use filtered `HDVehicle+0x4080` state;
- keep historical precomputed planar/scalar fixtures compatible;
- preserve seven top-level external provider boundaries.

Out of scope:

- implementing or naming `FUN_00717cd0`;
- claiming the native owner/provider for `HDVehicle+0x120`;
- guessing refresh cadence beyond source-visible stale/null behavior;
- assigning class/type names to the node;
- assigning physical names/units to the four remaining scalar inputs;
- rewriting immutable historical Phase 379 evidence.
