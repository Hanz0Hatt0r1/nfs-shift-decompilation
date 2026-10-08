# Process 1B — Participants Manager active-dispatch nested frontier

## Scope

This slice continues `P1.3.manager374` after the direct Participants Manager lifecycle target stores were proven zero-only.

The exact Participants Manager subobject is `FUN_00489ad0()+0x20` with vptr `0x00ab916c`. For this adjusted receiver, `manager+0x374` is subobject-relative `+0x354`.

## Exact active dispatch

`FUN_00647d80` selects the BManager active update callback from the object's vtable:

- default mode: vtable `+0x18` -> `FUN_0048ade0`;
- alternate mode: vtable `+0x1c` -> `FUN_0048aee0`.

Neither callback directly stores to subobject `+0x354`.

Both callbacks do perform one exact root conversion before a shared nested call:

```text
FUN_0048ade0: ECX = participants_subobject - 0x20; call FUN_00489b00
FUN_0048aee0: ECX = participants_subobject - 0x20; call FUN_00489b00
```

Because the Participants Manager subobject is exactly `manager+0x20`, this receiver is the exact manager root.

## Shared root-forwarder result

`FUN_00489b00` is therefore the only exact manager-root forwarder directly reached from the two active-dispatch callbacks. Its PC-retail body contains no direct store to `manager+0x374`.

This rejects the directly resolved active-dispatch nested surface as the missing nonzero `HDVehicle+0x4330` producer.

## Fail-closed remainder

This does **not** close all nested lifecycle behavior. Receiver-preserving descendants of `FUN_00489b00` remain open, and the larger Participants Manager callback at vtable `+0x0c` contains indirect dispatches that are outside this bounded slice.

The last literal `HDVehicle+0x64e8` candidate at `0x004b86cf` therefore remains conditional on some still-unresolved writer placing `HDVehicle+0x4330` into `manager+0x374`.

External provider count remains 7.
