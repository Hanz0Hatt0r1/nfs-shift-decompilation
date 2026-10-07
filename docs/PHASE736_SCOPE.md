# Phase 736 scope

Phase 736 is limited to source-backed ownership of the `FUN_007675f0` scalar previously called `projected_scalar`.

Included:

- use PC retail `FUN_007675f0` and `FUN_00759c90` machine code as authority;
- expose the exact three-record weighted-vector first output already present in native Phase660;
- preserve record base `HDVehicle+0x7f0`, count 3, and `0xa80` byte stride;
- preserve caller f64→f32 narrowing of first-output X/Z and the final f32 projection spill;
- replace production `projected_scalar` with the earlier fixed `FUN_00759c90` record boundary;
- retain an explicit compatibility scalar only for historical lower-chain fixtures;
- use Xbox recomp `sub_825939F0 -> sub_825899C0` only as corroboration/navigation;
- keep the active top-level external-provider count at seven.

Excluded:

- physical semantic names or units for the records/aggregate/projection;
- ownership of the producers that refresh the three records;
- treating Xbox floating-point behavior as authoritative for PC;
- changing already-closed surface-probe, distance-state, filter-cap, BODY-motion, `param_3`, base-scalar, or alignment-scalar boundaries;
- closing the second `FUN_00759c90` output or later `FUN_00753810`/`FUN_007ba9e0` contribution-vector path.
