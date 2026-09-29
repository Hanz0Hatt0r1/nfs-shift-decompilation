# Phase 534 — source-backed SGB OCCL runtime object

Phase 534 separates the SGB `OCCL` path from the previously shared fixed-record
view and maps its source fields to the concrete runtime object created by the
retail loader.

## Loader path

The binary SGB dispatcher `FUN_006a5270` routes the `OCCL` chunk to
`FUN_006a4f10` and forwards SGB header flag bit 1 as the third argument.

Each source record consumed by `FUN_006a4f10` is exactly `0x38` bytes:

| Source offset | Field |
|---:|---|
| `+0x00` | Name relative string |
| `+0x04` | Resource relative string |
| `+0x08` | PositionTL vec3 |
| `+0x14` | PositionTR vec3 |
| `+0x20` | PositionBL vec3 |
| `+0x2c` | PositionBR vec3 |

The field names are not inferred from position alone. The XML constructor for
the same concrete object, `FUN_006a3c40`, reads `Name`, `Resource`,
`PositionTL`, `PositionTR`, `PositionBL` and `PositionBR`. The retail PE
string referenced by `DAT_00aaf9fc` is `Name`.

## Concrete runtime object

For every OCCL source record, `FUN_006a4f10` allocates `0x120` bytes and
calls `FUN_006b43d0`. The constructor installs vtable
`PTR_FUN_00afa2fc` and initializes the descriptor/matrix fields.

The binary loader then copies the source data as follows:

| Runtime offset | Source |
|---:|---|
| `+0x60` | Name/Resource descriptor populated through `FUN_008244e0` / `FUN_008246a0` |
| `+0x90` | PositionTL, expanded from vec3 to vec4 |
| `+0xa0` | PositionTR, expanded from vec3 to vec4 |
| `+0xb0` | PositionBL, expanded from vec3 to vec4 |
| `+0xc0` | PositionBR, expanded from vec3 to vec4 |
| `+0xd0` | secondary 4x4 matrix initialized from `DAT_00b88a40` |
| `+0x110` | constructor flag byte initialized to zero |

The binary loader writes `1.0f` to the fourth component of each of the four
corner vectors.

## Admission modes

SGB header flag bit 1 selects two distinct runtime paths.

When bit 1 is clear, each concrete OCCL object is wrapped in the established
`0x38` generic scene wrapper with vtable `PTR_FUN_00af78ec`; the concrete
object pointer is stored at wrapper `+0x08`.

When bit 1 is set, the concrete objects are accumulated through
`FUN_004f5e60` and submitted as a batch through `FUN_0068b5a0`; no per-record
generic wrapper is created by this path.

## Contract

`SHIFT.SGBRuntime/1` now reports:

- semantic `name` and `resource` fields;
- semantic `position_tl/tr/bl/br` vectors;
- the concrete `0x120` runtime-object layout;
- the exact vec3-to-vec4 copy;
- the bit-1-dependent per-record-wrapper versus batched admission mode.

The old accidental treatment of OCCL records as SUMM wrappers is removed.

## Boundary

This phase does not assign a higher-level occlusion algorithm to the object,
does not name the owner/manager class reached by the batch sink, and does not
infer semantics for the secondary matrix beyond its proven constructor/load
copy. SUMM vector semantics and FLAT leaf semantics remain separate open
targets.
