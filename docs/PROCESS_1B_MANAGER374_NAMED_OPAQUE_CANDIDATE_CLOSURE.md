# Process 1B — named opaque manager-root candidate closure

## Result

Merged Process 1B evidence contains two concrete opaque/helper-shaped candidates that could appear to export the exact Participants Manager root `0x00bc9fc0`. Both are closed negative for their observed retail consumers.

## `FUN_004d1640`, vslot `+0x24`

`FUN_004d1640` is reached through vtable `0x00ac1860+0x24`. Its body calls `FUN_00489ad0` and can leave the exact manager root in EAX at return, but this is register residue rather than a stable ABI result.

The exact retail consumer at `0x004b75bc` immediately executes `0x004b75be mov al,1`, destroying the exact 32-bit manager-root value. Therefore `vslot_24_can_export_exact_manager_root_to_its_observed_consumer=false`.

## `FUN_0045b130`, render-manager vslot `+0x0c`

The exact render-manager primary vtable is `0x00ab5644`; slot `+0x0c` resolves to `FUN_0045b130`.

The exhaustive exact `DAT_00bc185c` first-hop receiver surface contains 95 source reads across 80 functions and exactly three proven indirect receiver transfers. Those three use slots `+0x1c` or `+0x20`; none uses `+0x0c`.

Therefore the merged machine contract reports `target_slot_plus_0x0c_dispatch_count=0` and `fun_0045b130_alternate_manager_root_source_closed=true` for the exact canonical render-manager lineage.

## Adjudication

```text
named opaque manager-root candidates = 2
named exportable candidates = 0
named_opaque_manager_root_candidate_surface_complete = true
known_named_opaque_helpers_can_create_independent_manager_root_alias = false
```

The known Participants Manager root lineage is separately closed against object/global persistence, stack-argument escape and external direct-callee escape. Neither named opaque candidate supplies a new known-lineage route that places fixed `HDVehicle+0x4330` into `manager+0x374`.

The global root-origin gate remains fail-closed. This contract does not prove absence of a previously unidentified helper, externally initialized memory cell, or unrecognized runtime transform that independently synthesizes the exact absolute address `0x00bc9fc0`.

Accordingly the final `manager+0x374 -> HDVehicle+0x4330` identity join, `0x004b86cf`, P1.3 completion and provider removal remain open. Provider count remains 7.

## Next step

Search specifically for any additional unnamed opaque helper/memory-load producer of exact `0x00bc9fc0`. If no concrete retail candidate exists, move from candidate adjudication to a final machine-surface absence proof.
