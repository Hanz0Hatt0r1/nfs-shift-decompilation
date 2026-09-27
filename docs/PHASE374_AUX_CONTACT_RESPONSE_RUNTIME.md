# Phase 374 — auxiliary contact-response kernel

Phase 374 reconstructs FUN_00758fc0, called twice near the end of
FUN_00766510.

## Record fields

The caller passes records at:

- this + 0x37d8
- this + 0x3858

The function observes:

| Offset | Use |
|---:|---|
| +0x00 | active flag |
| +0x38 | response gain |
| +0x40 | response scale |
| +0x48 | directional curve consumed by FUN_00755340 |
| +0x68 | source point |

## Transform chain

The source calls three established transform boundaries:

1. FUN_007aefb0(body + 0xd4, record + 0x68, local_78)
2. FUN_007537b0(body, local_78, local_a8)
3. FUN_007af0a0(body + 0xd4, local_a8, local_28)

After the transforms, the result is differenced against the caller's reference
point. The phase does not assign names to these coordinate spaces.

## Exact response

The response branch is active only when the record flag is non-zero and the
third relative component is negative.

Let z be that relative third component. Then:

- square = z²
- X = 0
- Y = FUN_00755340(record + 0x48, relative X, z) × (record + 0x38) × square
- Z = (record + 0x40) × square

The resulting vector is transformed with FUN_007aefb0 and submitted to
FUN_007baa70 using the transformed source point as the application point.

## Scope

This phase deliberately leaves FUN_007537b0, FUN_00755340 semantics, and all
physical field names/units external.
