# Process 1B — Participants Manager root-origin coverage

This aggregate composes the merged bounded proofs for creation and persistence of the exact Participants Manager root `0x00bc9fc0` before final `manager+0x374` identity adjudication.

## Known literal/static origins

The whole retail image contains exactly three direct immediate materializations of `0x00bc9fc0`:

```text
0x00489ae3  singleton initialization receiver
0x00489afa  getter return
0x00a9c5a0  registered static cleanup thunk
```

None is an independent runtime producer.

A whole-file exact-pointer scan finds those same three occurrences, all in `.text`; there are zero preinitialized exact pointer cells in `.rdata`, `.data`, or other sections. A separate aligned scan over the bounded manager interior range finds zero static interior-pointer cells. PE base relocations are stripped and the relocation directory is absent.

## Bounded reconstruction

The merged reconstruction coverage contains:

- 38,128 `mov r32,imm32` seeds;
- 499 simple same-register arithmetic transitions;
- 834 constant multi-register transitions;
- zero non-literal exact-root productions.

Therefore the bounded static/constant reconstruction classes create no unrelated Participants Manager root.

## Getter-derived aliases

The exact `FUN_00489ad0()` persistence surface contains 394 direct getter callsites. Across the audited whole-image paths:

- exact-root object/global stores = 0;
- exact-root stack saves = 9 and are locally bounded;
- immediate `push eax` after the getter = 0;
- escaped-storage paths are complete;
- stack-argument alias paths are complete.

## Writer/helper paths

All 18 computed `manager+0x374` paths are already closed, remaining = 0.

The exact Participants Manager lifecycle surface is also closed: its two direct target writers write zero only, active-dispatch receiver-preserving descendants do not reach `+0x374`, and all six vtable `+0x0c` indirect calls are resolved negative for parent recovery or target stores.

## Adjudication

`SHIFT.P1B.Manager374RootOriginCoverage/1` promotes only bounded origin coverage:

```text
bounded_manager_root_origin_classes_composed = true
known_literal_static_loader_constant_reconstruction_origins_complete = true
known_bounded_origin_classes_create_unrelated_manager_root = false
exact_getter_alias_persistence_complete = true
computed_runtime_writer_paths_complete = true
participants_lifecycle_helper_writer_surface_complete = true
```

The remaining class is deliberately explicit rather than hidden behind a generic TODO:

- opaque helper-returned exact roots synthesized from unrelated inputs;
- externally/runtime initialized memory containing the exact root without canonical getter lineage;
- unrecognized runtime transforms outside the bounded arithmetic classes.

Accordingly the global origin, global helper/non-vtable setter, final `manager+0x374 -> HDVehicle+0x4330` join, `0x004b86cf` rejection, and aggregate P1.3 gates remain fail-closed.

No identity is inferred from matching offsets. Provider count remains 7.
