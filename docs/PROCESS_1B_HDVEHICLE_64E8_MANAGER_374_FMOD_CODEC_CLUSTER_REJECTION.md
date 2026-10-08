# Process 1B — manager+0x374 FMOD codec cluster rejection

## Scope

This slice classifies the three remaining literal `+0x374` stores inside `FUN_0097d8c4`: `0x0097da09`, `0x0097daf8`, and `0x0097dc63`. The question is receiver identity, not numeric offset equality.

## Exact machine provenance

`FUN_0097dd0b` initializes descriptor `0x00b9ca20`, names it `FMOD DSP Codec`, and installs `0x0097d855` at slot `0x00b9ca48`, `FUN_0097dce4` at slot `0x00b9ca54`, and `0x0097d86a` at slot `0x00b9ca58`.

`FUN_0097dce4` transforms callback argument 1 to `arg1 - 0x1c`, null-masks that value, and calls `FUN_0097d8c4` with the result in ECX. `FUN_0097d8c4` captures that exact receiver in ESI at `0x0097d8d3`; all three target stores use `[ESI+0x374]`.

The sibling callbacks in the same descriptor independently apply the same `arg1 - 0x1c`/null-mask transform before entering the same state family (`0x0097d855 -> FUN_0097d725`, `0x0097d86a -> FUN_0097d83c`). The descriptor string is supporting context only; exact descriptor slots and machine receiver transfer adjudicate identity.

## Result

The three `FUN_0097d8c4` literal `+0x374` sites do not target Participants Manager root/subobject and cannot be used as `manager+0x374` producers.

Still open: `0x00865013` / `FUN_00864c10` first-argument provenance, computed-address writer forms, the final `manager+0x374 == HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completeness and provider removal. Provider count remains 7.
