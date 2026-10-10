# Process 1B — Participants Manager lifecycle/helper closure for `manager+0x374`

This composition updates an older open frontier by consuming the later machine-level closures for the Participants Manager active-dispatch descendants and the vtable `+0x0c` indirect surface.

## Exact Participants Manager identity

The Participants Manager is the exact `manager+0x20` subobject of the singleton returned by `FUN_00489ad0`. Its vptr is `0x00ab916c`. Relative target `participants+0x354` normalizes exactly to `manager+0x374`.

## Lifecycle direct writers

The recovered lifecycle vtable contains two exact stores to the target:

```text
FUN_004871f0 (+0x08): manager+0x374 = 0
FUN_00488970 (+0x14): manager+0x374 = 0
```

No lifecycle direct callback contains a nonzero exact target writer.

## Active-dispatch nested path

The `+0x18/+0x1c` active-dispatch callbacks resolve to `FUN_0048ade0` and `FUN_0048aee0`. Their only exact manager-root forwarder is `FUN_00489b00`.

`FUN_00489b00` has exactly one direct descendant that still receives the exact manager root: `FUN_00d610c0`. That descendant immediately transitions to `manager+0x2d8`, does not write `manager+0x374`, and does not preserve the exact root to another direct callee. Therefore the receiver-preserving active-dispatch descendant surface is closed-negative for an additional target writer.

## Vtable `+0x0c` indirect path

`FUN_0048a7f0` contains exactly six indirect calls:

- three heap-helper calls;
- three calls on the exact `manager+0x438` subobject.

The helper targets are resolved to the type3/type4 helper classes and do not recover the manager root or write the target. The `manager+0x438` target resolves to `FUN_007da470`; its same-receiver descendants and foreign helper callback/list-link path are already closed. No parent recovery and no `manager+0x374` store occurs.

Thus the entire Participants Manager vtable `+0x0c` indirect surface is closed-negative for `manager+0x374`.

## Parallel closed surfaces

The aggregate also verifies that:

- all 18 computed `+0x374` runtime paths are closed, remaining = 0;
- exact `FUN_00489ad0()` getter-root storage escapes are closed;
- exact getter-root stack-argument aliases are closed.

## Scoped adjudication

`SHIFT.P1B.Manager374ParticipantsLifecycleClosure/1` promotes:

```text
participants_lifecycle_nested_writer_surface_complete = true
participants_lifecycle_nonzero_manager_374_writer_found = false
participants_lifecycle_helper_or_indirect_setter_surface_complete = true
participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374 = false
```

This does not promote the global join. An unrelated reconstructed or unknown manager-root alias outside the audited lifecycle lineage could still, in principle, reach another helper/non-vtable setter. Therefore these remain fail-closed:

```text
unrelated_manager_alias_or_unknown_root_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
```

The manager `+0x2a0` selection writer remains a separate allocator-owned object domain and is not promoted to fixed `HDVehicle+0x4330`. Provider count remains 7.
