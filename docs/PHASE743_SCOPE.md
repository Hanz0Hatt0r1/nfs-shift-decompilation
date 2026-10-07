# Phase 743 scope

In scope:

- freeze PC retail `FUN_00766510` source lines 759689–759695;
- reproduce exact `FUN_00753650(left, right)` left-cross-right ordering;
- preserve the PC x87 `0x027f` control word and `DE E9` subtract opcode;
- add the cross result into `HDVehicle+0x40a0/+0x40a8/+0x40b0`;
- add the current `FUN_007551e0` auxiliary output into the incoming local auxiliary accumulator;
- consume Phase742's transformed response without duplicating its BODY transform/application;
- corroborate topology against Xbox recomp partition 220.

Out of scope:

- internalizing all of `FUN_00766510`;
- removing the top-level `contact_response` provider;
- reducing the external-provider count below seven;
- internalizing the producer/refresh ownership of `HDVehicle+0x3b08`;
- internalizing the earlier response branch that seeds the local auxiliary accumulator;
- assigning physical names or units to any accumulator lane;
- closing the later response branch, final accumulated auxiliary application, diagnostics, or other source-visible writes.
