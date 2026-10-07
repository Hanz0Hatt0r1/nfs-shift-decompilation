# Phase 741 scope

In scope:

- prove the PC retail setup writer for `HDVehicle+0x38e8`;
- trace its source to `FRONTWING.FWMaxHeight` at setup `+0x6a4`;
- preserve the explicit PC f32 spill before widening to f64;
- bind the selected BMW M3 E36 retail CDF value `0.10` bit-exactly;
- expose that selected setup value to the residual `FUN_00765c40` provider before execution;
- reject a selected-BMW query witness that consumed a different fallback;
- preserve generic historical fixture compatibility;
- corroborate the setup shape against Xbox recomp without substituting Xbox semantics for PC authority.

Out of scope:

- generalizing the BMW value to other vehicles/configurations;
- naming physical meaning or units for `+0x38e8`;
- internalizing the collision/world lookup provider under `FUN_007b0710`;
- internalizing `FUN_00766510` contact-response behavior merely because it reads the same `+0x38e8` setup state;
- internalizing the four `FUN_00765c40` load terms or residual side effects;
- reducing the top-level external provider count below seven.
