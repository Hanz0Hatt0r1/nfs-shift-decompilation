# Process 1B — HDVehicle+0x4330 external caller tranche 2

This P1.3B slice closes two more caller functions from the exact incoming direct-call frontier after `SHIFT.P1B.HDVehicle4330ExternalCallerTranche1/1`.

## FUN_0074da70

The only exact-carrier call is `0x0074dadf -> FUN_0076df50`. Retail machine code loads literal `ECX = 0x00c13700` immediately before the call, so this is an exact HDVehicle-root entry into the already-proven root carrier. It is not a pre-existing `HDVehicle+0x4330` pointer path.

## FUN_00795d60

`FUN_00795d60` has one exact-carrier call, `0x007973fe -> FUN_00771db0`. The merged large-consumer closure establishes that the exact `HDVehicle+0x4330` pointer reaches `FUN_00771db0` through `ECX` on the root-derived path.

Retail machine flow for the external path is different:

- the only direct caller of `FUN_00795d60` is `FUN_00798df0` at `0x007990ed`;
- `FUN_00798df0` materializes `LEA EAX,[EBP-0x238c]` and pushes it as `FUN_00795d60.param3`;
- inside `FUN_00795d60`, `MOV ESI,[EBP+8]` reloads that same `param3`;
- `MOV ECX,ESI` forwards it into `FUN_00771db0`.

Therefore the receiver at `0x007973fe` is the caller stack local `EBP-0x238c`, not `HDVehicle+0x4330`.

## Result

Cumulative direct external closure is now 4 of 7 caller functions and 8 of 11 callsites. Remaining callers:

- `FUN_00aa2850`
- `Unwind@00a7063f`
- `Unwind@00a72322`

The two unwind funclets are not rejected by name. Their enclosing frame/local provenance must be established from retail machine evidence before the direct external receiver gate can close.

Indirect entry, runtime-generated/copied pointer paths, global runtime-derived `+0x4330` alias exhaustion, the `manager+0x374 -> HDVehicle+0x4330` join, final `0x004b86cf`, aggregate P1.3 and provider removal remain fail-closed. Provider count remains 7.
