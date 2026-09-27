# Phase 372 — body load accumulation boundary

Phase 372 closes FUN_007baa70, the common application boundary reached by the
new wheel/contact response path and by several other physics response stages.

## Exact arithmetic

For input point P = (Px, Py, Pz) and input vector V = (Vx, Vy, Vz), the function:

1. adds V to the vector accumulator;
2. adds P × V to the second accumulator.

The source-level expressions are:

- X = Py·Vz − Pz·Vy
- Y = Pz·Vx − Px·Vz
- Z = Px·Vy − Py·Vx

No subtraction of the body's position is performed inside FUN_007baa70.

## Storage

| Accumulator | Offsets |
|---|---|
| point × vector | +0x48, +0x50, +0x58 |
| vector sum | +0x60, +0x68, +0x70 |

## Related implementation

FUN_007ba9e0 updates the same two accumulator groups but first subtracts
the body's stored position from the application point. This confirms that
the origin adjustment belongs to a separate variant and is not hidden inside
FUN_007baa70.

## Scope

The phase records the exact arithmetic and storage contract only. It does not
rename the accumulators to a specific PhysX type or infer units.
