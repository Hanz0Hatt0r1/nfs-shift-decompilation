# Phase 734 — FUN_007675f0 param_3 ownership

Phase 734 removes `param_3` from the production `FUN_007675f0` per-pass provider payload.

## PC retail producer

The only direct caller, `FUN_00769ef0`, produces the third stack argument passed to `FUN_007675f0` from state that is already available earlier in the same recovered pass:

1. read the four `FUN_00765c40` load terms at `HDVehicle+0xb38/+0x15b8/+0x2038/+0x2ab8`;
2. sum them in source order, including the exact f64 `+0.0` term at `0x00aadd68`;
3. read current chassis `BODY0+0x120` as f64;
4. multiply that field by the exact f64 constant at `0x00b09148`, bits `0x40239eb851eb851f` (`9.81`);
5. divide the load sum by that denominator;
6. spill the quotient to f32;
7. clamp the f32 value to `[0,1]`;
8. pass the clamped f32 as the third stack argument to `FUN_007675f0`.

`FUN_007675f0` consumes that argument at `0x00767a60` as its final visible scalar multiplier. The repository keeps the neutral name `param_3`; no physical meaning or units are promoted for `BODY0+0x120` or the load terms.

## Precision correction

This producer uses a different PC constant from the nested `FUN_007595d0` response helper:

- `FUN_00769ef0 param_3`: `0x00b09148`, f64 bits `0x40239eb851eb851f`;
- `FUN_007595d0`: `0x00b04858`, f64 bits `0x40239eb860000000` (`9.810000419616699`).

An older `FUN_007682c0` evidence string reused the second value for its duplicate caller-scale description. Phase 734 supersedes that precision claim only for the `FUN_00769ef0` caller-scale/`param_3` producer; it does not alter the independently recovered `FUN_007595d0` constant.

The native regression includes a one-ULP witness that distinguishes the two constants.

## Native join

`SHIFT.Fun00769ef0Param3/1` derives the value from:

- typed same-pass `Fun00765c40LoadTerms`;
- current persistent BODY0 `+0x120`.

The existing source order is sufficient: `FUN_0076d100` executes the `FUN_00765c40` anchor before the `FUN_00769ef0/FUN_007675f0` contact-outer anchor. `NativeVehicleProviderSession` therefore injects the already-produced load terms into the internal contact-outer payload, while `execute_fun_00770e80_contact_outer_provider_chain` reads current BODY0 `+0x120` from the same pass snapshot used for BODY motion and the surface-probe query.

Pass 1 consequently sees the BODY state after pass 0's half-step exactly as the surrounding native chain already guarantees.

## Boundary narrowing

Production `ContactOuterSessionInput` now contains four unresolved fields:

- `surface_probe_node`;
- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`.

Historical lower arithmetic payloads retain `param_3`, and compatibility conversion can still preserve old fixtures. The seven top-level external provider boundaries remain unchanged.

## Fail-closed behavior

The native producer rejects:

- non-finite load terms;
- non-finite `BODY0+0x120`;
- zero `BODY0+0x120` / zero denominator;
- non-finite intermediate quotient or f32 spill.

## Next target

The next bounded source task is to map the already-native `FUN_00759c90` aggregate and nearby `FUN_00769ef0` intermediates into `base_scalar`, `projected_scalar`, and `alignment_scalar`, without assigning undocumented physical names.
