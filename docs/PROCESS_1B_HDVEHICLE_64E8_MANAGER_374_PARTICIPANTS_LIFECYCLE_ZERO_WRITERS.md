# Process 1B — Participants Manager lifecycle target stores

## Result

The escaped `manager+0x20` alias is the embedded object labelled `Participants Manager`. Its constructor `FUN_00488dc0` overwrites the base vptr with `0x00ab916c`, so the BManager lifecycle dispatches can be resolved to concrete PC-retail callbacks.

The target `manager+0x374` is `Participants Manager+0x354`.

Two resolved callbacks contain exact literal stores to that offset:

```text
FUN_004871f0, vtable +0x08
0x00487203  xor eax,eax
0x0048720b  mov [esi+0x354],eax

FUN_00488970, vtable +0x14
0x004889ac  xor ebx,ebx
0x004889b4  mov [esi+0x354],ebx
```

Both therefore clear `manager+0x374`; neither is a nonzero producer.

The other directly resolved vtable entries at `+0x0c/+0x10/+0x18/+0x1c/+0x20` contain no literal `this+0x354` store on their direct instruction surfaces.

## Boundary

This advances the escaped-registry investigation but does not claim that every nested callee or computed/non-vtable alias is closed. Those remain fail-closed. It also does not reopen the rejected `manager+0x2a0 entry == HDVehicle+0x4330` route.

## Next

Trace nested/computed mutations reachable from the Participants Manager callbacks and unrelated manager aliases, while continuing the direct `HDVehicle+0x64e8` non-sentinel writer search.
