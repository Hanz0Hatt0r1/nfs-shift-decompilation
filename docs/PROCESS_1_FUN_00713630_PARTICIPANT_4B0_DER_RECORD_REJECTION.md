# Process 1A — reject `0x00607f22` from the participant `+0x4b0` frontier

## BLOCKER

Two direct-displacement `+0x4b0` candidates remain after the nested-copy rejection. `0x00607f22` is one of them.

## OUTPUT

The store belongs to a nested parser record, not root-relative selected PhysicsParticipant state.

`FUN_006075f0` starts by zeroing exactly `0x5e0` bytes at its explicit `param_1` receiver. Within that record it stores a blob length at `param_1+0x4b0` and the blob at `param_1+0x4b4`; a second length/payload pair lives at `+0x5b4/+0x5b8`.

The only recovered source caller is `FUN_00608720`, which invokes:

```text
FUN_006075f0((undefined1 *)(iVar2 + 0x410), ...)
```

Therefore the candidate storage maps to `outer+0x8c0`, not `outer+0x4b0`. `FUN_006087c0` independently consumes `outer+0x8c0` as a length and `outer+0x8c4` as its payload, confirming the nested mapping.

## GATES_CHANGED

- `0x00607f22`: **rejected**;
- unresolved direct-displacement candidates: **1**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Adjudicate the final direct-displacement site `0x0076019f` by exact enclosing-function and receiver provenance before widening to computed-address, escaped-alias, indirect-dispatch or residual bulk-copy paths.
