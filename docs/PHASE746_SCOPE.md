# Phase 746 scope

In scope:

- expose exact PC `FUN_00753650` three-lane cross-product arithmetic as a native primitive;
- reuse that primitive inside existing `FUN_007baa70` accumulation;
- extend the active Phase742 primary-response result with the immediately-following `HDVehicle+0x40a0/+0x40a8/+0x40b0` delta;
- freeze PC source lines and machine spans for the Phase742 primary block through the caller accumulator stores;
- inventory, but not internalize, the remaining accumulator contributions in complete `FUN_00766510`;
- preserve the top-level provider count at seven.

Out of scope:

- claiming all `+0x40a0/+0x40a8/+0x40b0` writes native;
- scheduling the auxiliary pair in the selected session;
- internalizing the other direct response blocks;
- internalizing the final transformed-vector addition;
- removing `NativeVehicleContactResponseProvider`;
- assigning physical names or units to the caller accumulator state.
