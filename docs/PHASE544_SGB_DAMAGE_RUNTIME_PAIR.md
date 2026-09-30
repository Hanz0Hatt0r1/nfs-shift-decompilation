# Phase 544 — DAMAGE two-child runtime contract

Phase 544 extends the source-backed SGB object model without pretending that a
retail DAMAGE payload has been observed in the available Silverstone corpus.

The result is a runtime ownership/dispatch contract, not a claim that the full
serialized DAMAGE layout is closed.

## Concrete wrapper

The DAMAGE object constructed by `FUN_00698b00` is a `0xa0`-byte runtime
object with vtable `0x00af7c88`.

The constructor initializes:

| Runtime offset | Proven role |
|---:|---|
| `+0x80` | matrix count |
| `+0x84` | runtime matrix array |
| `+0x88` | child-object pointer allocation |
| `+0x90` | MatrixNumber |

The matrix array uses the same `0x28`-byte runtime MATRIX elements recovered
for LOD/HIERARCHY in Phase 543.

## The +0x88 allocation is a two-object pair

`FUN_0068cf40`, the concrete DAMAGE destructor, iterates the allocation at
`+0x88` from byte offset 0 through byte offset 4 and stops at 8 bytes.

For each non-null entry it invokes child vfunc `+0x00` with destroy argument
1. It then frees the pair allocation and clears `+0x88`.

This proves that the runtime consumer owns exactly **two child object pointers**
at this boundary. The source does not justify assigning gameplay names such as
"undamaged/damaged" to slot 0 or slot 1, so the IR keeps them numeric.

The destructor separately frees the matrix allocation at `+0x84` and clears
that field.

## Symmetric child dispatch

The DAMAGE vtable contains methods that operate on both entries of the pair:

| Wrapper vfunc | Function | Child vfunc | Behavior |
|---:|---|---:|---|
| `+0x10` | `FUN_0068c6d0` | `+0x10` | forward to both |
| `+0x14` | `FUN_0068c750` | `+0x14` | forward to both |
| `+0x18` | `FUN_0068c710` | `+0x18` | forward to both |
| `+0x20` | `FUN_0068c790` | `+0x20` | logical AND of both |
| `+0x28` | `FUN_0068c7c0` | `+0x28` | logical AND of both |

The wrapper `+0x24` path, `FUN_0068dea0`, first probes child vfunc `+0x3c`
on both objects and uses a specialized two-child selection/fallback path through
child vfunc `+0x24`.

## Construction consumer

`FUN_0068cfe0` consumes the same wrapper state:

- `+0x80` matrix count;
- `+0x84` `0x28`-stride matrix array;
- `+0x90` MatrixNumber;
- both pointers from `+0x88`.

When an external matrix stack is supplied, MatrixNumber selects an entry with
a `0x40` stride. When the stack is absent, the function reconstructs an
internal stack from the recovered MATRIX records.

The two child objects are queried through vfunc `+0x24`, with their returned
objects stored into consumer fields `+0xa0` and `+0xa4`.

## Serialized boundary

Both binary and XML construction paths prove the common header's
`matrices`/ `subobjects` counts and MatrixNumber.

The binary branch uses `FUN_00699870` to build the runtime matrix data, while
the XML branch uses `FUN_006990d0`.

However, the exact binary DAMAGE subobject-offset table is not normalized in
the current decompilation, and no DAMAGE payload exists in the four Silverstone
Era3 scene variants currently available:

- Drift;
- Grand Prix;
- International;
- National.

Therefore Phase 544 deliberately leaves
`binary_subobject_offset_table = not-normalized`.

## Boundary

Phase 544 proves the concrete two-child runtime ownership and dispatch model.
It does not name the two child roles and does not fabricate serialized offsets
that have not been observed or recovered.

The next useful scene target is either a real DAMAGE-bearing SGB from the
broader game corpus or the remaining FLAT direct-record float payload
consumers.
