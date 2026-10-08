# Process 1B — HDVehicle +0x4330 constant reconstruction surface

## Scope

This slice extends the static exact-pointer scan for `HDVehicle+0x4330 = 0x00c17a30` to constant-only arithmetic synthesis across general-purpose registers.

## Result

The retail `.text` scan uses the same bounded constant propagation as the Participants Manager reconstruction audit. It sees four exact literal productions, all in the already-known wrapper block. It then evaluates 499 same-register arithmetic transitions and 834 constant multi-register transitions through register moves, add/sub, and constant indexed LEA.

Zero non-literal chains produce `0x00c17a30`.

## Adjudication

Constant-only reconstruction cannot introduce a new exact `HDVehicle+0x4330` alias. Combined with the whole-PE static pointer-cell scan, the remaining alias risk is runtime-derived: memory loads, opaque helper returns, copied/external initialization, indirect dataflow, or unrecognized transforms.

Global non-literal `HDVehicle+0x64e8` writer closure and the manager `+0x374` join remain fail-closed. Provider count remains 7.
