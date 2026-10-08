# Process 1 — exact `manager+0x2a0` selector machine proof

## Result

`FUN_0045da80` is now proven to operate on the exact singleton returned by `FUN_00489ad0()`.

Retail machine code:

- `0x0045da84`: calls `FUN_00489ad0`;
- `0x0045da8c`: copies the returned manager pointer into `ESI`;
- `0x0045da8e`: compares the requested index against `manager+0x2c4`;
- out of range: zeroes `manager+0x378`;
- in range: forms `ECX = manager+0x2a0` at `0x0045daa3`;
- `0x0045daa9`: calls read-only index accessor `FUN_0054ed00`;
- `0x0045daae`: stores the returned entry address to `manager+0x378`.

Therefore `manager+0x378` is an exact selected-entry cache for the `manager+0x2a0` collection (or null when the index is out of range).

## What this closes

The selector root is no longer ambiguous: this path is explicitly rooted at `FUN_00489ad0()` and does not depend on offset matching.

The Ghidra database also places `FUN_0045da80` at slot 0 of heuristic vtable candidate `0x00ab563c`; this is corroborative only and is not needed for the root proof.

## What remains open

This does **not** prove:

- who populates/mutates the exact singleton `manager+0x2a0` collection;
- that a selected `manager+0x378` entry is `HDVehicle+0x4330`;
- that `manager+0x374 == HDVehicle+0x4330`;
- a selected non-sentinel writer for `HDVehicle+0x64e8`;
- retail control/input semantics.

P1.3 therefore remains incomplete and the external provider count remains 7.

## Next step

Trace exact writers/mutators of `FUN_00489ad0()+0x2a0`, then join the selected `manager+0x378` entry to `HDVehicle+0x4330` or reject that identity with machine evidence.
