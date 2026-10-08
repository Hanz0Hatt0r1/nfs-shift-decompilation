# Process 1B — render-manager slot-address consumer closure

## Scope

`SHIFT.HDVehicle64e8RenderManagerGlobalSlotAddressSurface/1` proves that the whole retail image contains one raw occurrence that takes the **address** of canonical slot `DAT_00bc185c` rather than directly loading or storing the slot. This slice bounds that unique occurrence at `0x004fb9af`.

PC retail 1.02 machine transfer is authoritative. Decompiled source is navigation-only.

## Unique address-of-slot path

Inside `FUN_004fb940`:

```text
0x004fb9af mov edi,0x00bc185c
0x004fb9b5 mov edi,[edi]
0x004fb9b7 add edi,0x780
```

The literal slot address is therefore immediately dereferenced. It is not stored, returned, pushed, or forwarded to a helper before the dereference. The resulting exact outer root is immediately transformed into `outer+0x780` before helper transfer.

The first helper call is:

```text
0x004fb9c4 call FUN_0048fc70
ECX = outer+0x780
```

`FUN_0048fc70` preserves that derived receiver in EDI and reaches `FUN_00633290`, the already-bounded runtime-item allocator primitive. That primitive stores the same incoming `outer+0x780` pointer in item metadata; it does not reconstruct the outer root.

The success path later uses the same derived receiver through `FUN_00493410`. That function recovers runtime-item pointers through `FUN_00632fe0`, uses `FUN_006333f0`, and can recursively allocate another item through `FUN_0048fc70`, but no bounded descendant subtracts `0x780`, stores an exact outer root, or returns one.

## Result

The single raw address-of-slot occurrence does **not** create an alternate exact-root source. Its entire path reduces to the already-known `outer+0x780` derived-pointer/item family.

This does not close arbitrary unknown-memory or externally supplied exact-root aliases. Cross-control-flow/two-unknown-origin `HDVehicle+0x4330`, the manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. Provider count remains 7.
