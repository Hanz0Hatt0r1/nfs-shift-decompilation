# Phase 375 — body point transform

Phase 375 reconstructs FUN_007537b0 and its close variant FUN_00753810.

## FUN_007537b0

For angular = (Ax, Ay, Az), point = (Px, Py, Pz), translation T, the exact
output is:

- X = Pz·Ay − Py·Az + Tx
- Y = Px·Az − Ax·Pz + Ty
- Z = Ax·Py − Px·Ay + Tz

This is angular × point + translation.

The function reads:

| Role | Body offsets |
|---|---|
| angular | +0x18, +0x20, +0x28 |
| translation | +0x78, +0x80, +0x88 |

## FUN_00753810

The variant first subtracts body position:

P' = P − body_position

using body +0x00/+0x08/+0x10, then applies the same angular × P' + translation
formula.

## Scope

This phase deliberately keeps the body fields unnamed beyond their use in the
instruction stream. It closes the transform arithmetic that is used by
FUN_00758fc0.
