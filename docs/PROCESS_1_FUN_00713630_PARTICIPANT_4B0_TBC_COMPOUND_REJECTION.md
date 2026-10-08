# Process 1A — reject `0x007a2006` from the participant `+0x4b0` frontier

## BLOCKER

Eight direct-displacement `+0x4b0` candidates remained after the FLAC-record rejection. `0x007a2006` is a constructor write whose object root must be identified exactly.

## OUTPUT

`FUN_007a32a0` owns TBC tire-manager parsing. The source-order path contains both `Could not open TBC file: %s` with `.\Source\Vehicle\tire_manager.cpp` and the `[COMPOUND]` section marker.

For each compound, the function allocates a vector with exact element stride `0x610` and installs `FUN_007a1fc0` as its constructor:

```text
count = owner+0x0c
allocation = count * 0x610 + 4
_eh_vector_constructor_iterator_(array, 0x610, count,
                                 FUN_007a1fc0, FUN_007a3090)
owner+0x10 = array
```

The candidate store occurs inside that element constructor:

```text
0x007a2006  [compound_record+0x4b0] = 0
```

Therefore the store is TBC `[COMPOUND]` record state in the tire-manager-owned array, not selected `0x2b90` PhysicsParticipant state.

## GATES_CHANGED

- `0x007a2006`: **rejected**;
- TBC compound array/record owner: **closed**;
- unresolved direct-displacement candidates: **7**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining seven direct-displacement candidates before widening to computed-address, escaped-alias, indirect-dispatch, or residual bulk-copy paths.
