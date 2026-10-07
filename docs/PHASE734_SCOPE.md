# Phase 734 scope

Phase 734 is limited to source ownership of the `FUN_007675f0` third scalar argument (`param_3`).

In scope:

- prove the PC `FUN_00769ef0` producer formula from four typed `FUN_00765c40` load terms and current `BODY0+0x120`;
- preserve exact f64 `9.81` bits from `0x00b09148` and the source f32 spill before clamp;
- materialize the scalar natively after `FUN_00765c40` and before `FUN_007675f0` in each recovered pass;
- remove `param_3` from production `ContactOuterSessionInput`;
- preserve historical lower-chain and compatibility `param_3` paths;
- keep seven top-level external provider boundaries.

Out of scope:

- assigning physical meaning or units to `BODY0+0x120` or the four load terms;
- changing the separate `FUN_007595d0` f64 constant at `0x00b04858`;
- internalizing `surface_probe_node`, `base_scalar`, `projected_scalar`, or `alignment_scalar`;
- reducing the top-level provider count;
- guessing `FUN_00759c90` physical semantics.
