# Process 1B — manager+0x374 runtime-root frontier

This aggregate composes already-merged bounded machine evidence around alternate Participants Manager-root creation/propagation.

## Closed classes

- static exact/interior manager-root pointer cells;
- shipped PE base-relocation-derived roots;
- constant same-register and multi-register reconstruction;
- exact `FUN_00489ad0()` getter persistence through registers, stack, object fields, globals and immediate stack-argument forwarding;
- `FUN_0045ef50` constructor exact-`this` escape before the canonical global store;
- the `outer+0xc4c -> vtable+0x24 -> FUN_004d1640` EAX-residue path;
- `FUN_0045b130` at `0x00ab5644+0x0c` for the exhaustive exact `DAT_00bc185c` first-hop receiver-transfer surface.

The `FUN_0045b130` first-hop inventory covers 95 exact-global source reads across 80 functions, with three proven indirect receiver transfers. Those three dispatch slots are `+0x1c/+0x20`; target slot `+0x0c` is reached zero times.

The render-manager constructor creates no persistent exact-root copy and forwards exact `this` to no opaque helper before the canonical `DAT_00bc185c` store.

## Remaining frontier

The surviving manager-root source class is now post-construction runtime-created/copied aliases of the outer object, including external/unknown-origin aliases that can bypass the exact-global first-hop scan. Opaque runtime sources not rooted in the already-closed exact-global/constructor/static/constant paths also remain open.

Therefore this contract does **not** promote the global identity join. `manager+0x374 == HDVehicle+0x4330`, final `0x004b86cf` rejection and aggregate P1.3 remain fail-closed. Provider count remains 7.
