# Phase 362 — tyre thermal-state runtime

Phase 362 follows the TBC/curve initialization into the per-frame thermal state update
for each of the four wheel objects.

## Exact function boundary

The recovered retail source identifies `FUN_00760b50` in
`./Source/Vehicle/hdvehicle.cpp` (source line 756009). `FUN_00770e80` calls this
function once for each wheel object after the main physics passes.

The wheel runtime object stride is `0xA80`.

## Recovered arithmetic

The function first forms a primary heat term:

`abs(+0x350) * +0x858 * +0x898`

It transforms the wheel-state vector at `+0x78` into vehicle space and keeps the
positive magnitude of the negative longitudinal component.

The ambient transfer term is:

`(+0x8A8 * abs_longitudinal + +0x8A0) * (ambient_average_kelvin - +0x888)`

where the source adds `273.16` to both ambient temperature inputs before averaging.

The two terms are added to form the thermal rate numerator.

When `+0x8B0 <= +0x8C8`, the source uses the reserve-floor normalization directly:

`rate = net_heat / +0x8C8`

When the reserve is above the floor, the source computes a cubic depletion term:

`+0x8C0 * source_heat * (+0x888)^3`

multiplies it by the global overheat scale returned by `FUN_00749340` and
`DAT_00c12f38), and subtracts the result times `dt` from `+0x8B0`.

If the reserve remains at or above the floor, the source uses the new reserve as the
rate denominator. It also updates `+0x868`: inside the `+0x878` temperature
tolerance around `+0x890`, the source uses a random blend
`(0.25*rng + 0.75) * +0x870`; outside that tolerance it uses `0.5 * +0x870`.

If the reserve falls below the floor, the source zeros `+0x8B0` and `+0x868` and
sets the thermal rate to zero.

Finally:

`+0x888 += rate * dt`

## Runtime ordering

`FUN_00770e80` executes two `FUN_0076d100` physics passes with half-timestep helper
work between them, then invokes `FUN_00760b50` once per wheel. This establishes the
thermal update as a distinct post-pass in the observed frame path.

## Scope boundary

This phase is not the complete tyre traction/contact law. The coefficients governing
lateral/longitudinal force response are still being traced through their wheel-state
consumers. No physical units are assigned where the source does not prove them.

## Phase 361 correction

The TBC top-level loader is `FUN_007a32a0`; `FUN_007a10f0` is the compound-record
parser. The Phase 362 branch corrects the Phase 361 contract and regression expectation
to the actual loader boundary.

## Verification

This phase adds a versioned thermal contract, source evidence, deterministic branch tests,
and keeps renderer code plus `RENDER.bff` untouched.
