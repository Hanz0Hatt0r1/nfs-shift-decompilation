# Phase 545 — SGB spatial placement join

Phase 545 joins the production object/wrapper grammar from Phases 543–544 to
the two source-backed spatial indexing paths used by the retail scene runtime.

The result is `SHIFT.SGBPlacementJoin/1`.

## FLAT / SUMM path

The binary SUMM loader provides an exact index join:

1. `FUN_006a4900` calls
   `FUN_0068a920 -> FUN_006af330` with the SUMM record count, allocating
   primary `0x28` and secondary `0x40` runtime arrays.
2. Each SUMM wrapper is appended in source-record order through
   `FUN_00688510 -> FUN_006af4b0`.
3. After all SUMM wrappers are loaded,
   `FUN_00688520 -> FUN_006af820 -> FUN_006af780` traverses FLAT leaves.
4. FLAT leaf `+0x3c` is used as the secondary/primary array index.

Therefore:

```text
FLAT leaf.runtime_index == i
        ↕
SUMM source/runtime wrapper order == i
```

The join fails closed on count mismatch, duplicate indices, out-of-range
indices or missing coverage.

## Production Silverstone closure

The observation
`evidence/silverstone_era3_placement_join_observation.json` covers all four
Silverstone Era3 visual variants.

| Variant | FLAT leaves | SUMM records | Index coverage |
|---|---:|---:|---|
| Drift | 2,622 | 2,622 | 0..2621 |
| Grand Prix | 7,348 | 7,348 | 0..7347 |
| International | 5,932 | 5,932 | 0..5931 |
| National | 5,678 | 5,678 | 0..5677 |

Across 21,580 placements there are no count mismatches, duplicate indices or
gaps.

All serialized FLAT direct-object pointer words at `+0x38` are zero in this
corpus. They are not interpreted as portable object references.

## PART / NODE path

The alternate partition path is also exact in source:

- `FUN_006a4b40` appends binary NODE wrappers to the scene wrapper registry
  at manager `+0x54`;
- PART stores one-based child object IDs;
- `FUN_0068a360/FUN_00689a30` resolves each child with
  `FUN_006885b0(manager+0x54, source_id-1)`.

The placement join therefore maps every valid PART child ID directly to the
corresponding NODE wrapper record index.

This path is source-backed but is not claimed as production-observed in the
four Silverstone visual SGBs, which use FLAT/SUMM and contain no PART chunk.

## PART runtime materialization into FLAT geometry

`FUN_0068a810 -> FUN_006afd50 -> FUN_00689db0` proves how the PART runtime
can be converted into the same FLAT-like indexing geometry.

For every PART child object, the builder emits a `0x40` direct record:

- generated `+0x38` receives the child runtime object's pointer from its
  wrapper entry;
- generated `+0x3c` receives the sequential traversal index;
- the matching secondary slot receives back-pointers to the partition node,
  generated leaf and primary `0x28` slot.

This is a runtime equivalence statement. Phase 545 does **not** claim that PART
source records serialize FLAT `+0x38` pointers.

## Boundary

The object-to-placement identity join is now explicit for both supported
spatial paths.

Remaining scene work is narrower:

- recover only the FLAT direct-record spatial/mask fields required to express
  placement to RenderBinding;
- preserve unresolved runtime class identities until their consumers prove
  them;
- then expose the joined scene placement as neutral render input.
