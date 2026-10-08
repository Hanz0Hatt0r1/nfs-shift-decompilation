# Process 1B — Participants Manager +0x374 delayed stack-alias surface

## Scope

This slice follows exact `FUN_00489ad0()` results that are first copied into a general-purpose register and only then persisted to a stack local. It complements `SHIFT.HDVehicle64e8Manager374GetterLocalAliasSurface/1`, which closed the immediate getter-local pattern.

PC retail 1.02 machine transfer is authoritative. The Ghidra SQLite export is navigation-only.

## Result

There are four delayed register-to-stack candidates:

- `FUN_00492520`, call `0x00492591`: manager root is held in `EDI`, saved to `[ebp-0x8]`, and used only for `+0x2d4`, `+0x2c4`, and `+0x2a0` reads/lookups.
- `FUN_00496680`, call `0x004966c3`: manager root is held in `ESI`, saved to `[ebp-0x4]`, and used only for the same manager count/array lookup surface.
- `FUN_004bad20`, call `0x004bad36`: manager root is held in `ESI`, saved to `[ebp-0x14]`, and used for `+0x2fc/+0x2d4` counts plus `+0x2a0/+0x2d8` entry lookup. Later writes at participant-entry `+0x219c/+0x21a0` are writes to the selected entry, not to the manager root.
- `FUN_0051df70`, call `0x0051df7a`: manager root is held in `EDX`, saved to `[ebp-0x4]`, and used for `+0x2d4/+0x2c4/+0x2a0`. `EDX` is temporarily repurposed as the lookup index and the manager root is then restored from the stack local; it is never forwarded as a callee receiver.

None of the four functions writes through the manager root, forwards the exact manager root to another callee, or can create a new value at manager `+0x374`.

## Adjudication

The complete delayed GPR→stack alias pattern for the exact manager getter result is closed-negative for manager `+0x374` mutation.

This does not close object-field/global persistence of the manager root, unrelated root reconstruction, or escaped/non-root-derived `HDVehicle+0x4330` aliases. The remaining literal `0x004b86cf` candidate therefore stays fail-closed. Provider count remains 7.
