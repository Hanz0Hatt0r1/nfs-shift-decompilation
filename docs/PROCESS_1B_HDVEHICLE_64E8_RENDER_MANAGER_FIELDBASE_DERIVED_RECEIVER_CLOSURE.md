# Process 1B — render-manager field-base / derived-receiver closure

## Scope

This slice closes three more direct targets from the bounded `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` worklist. In each case the exact render-manager outer root is used only as a field base or is converted to a derived child/subobject receiver before any downstream call.

PC retail 1.02 machine transfer is authoritative. Decompiled source is navigation-only.

## `0x00441fd0 -> 0x00476cf0`

The thunk tail-jumps to `0x00476cf0`, where `0x00476cf8 mov esi,ecx` preserves the exact root. All uses of `ESI` are field accesses at `root+index+0x1598`, `root+index*4+0x15f4`, or the child-pointer load at `root+index*4+0x1548`. The call at `0x00476d35` receives that loaded child in `ECX`, not the exact root. The function returns an `AL` boolean and never stores, returns, or re-forwards the exact root.

## `0x0045e110`

`0x0045e111 mov esi,ecx` preserves the exact root. The body derives `root+0x2b0` for state handling and, on its tail-dispatch path, loads `ECX=[root+0xc4c]`, reads the child vtable and jumps through child slot `+0x18`. Thus the indirect receiver is the child/subobject, not the exact root. No exact-root store or return occurs.

## `0x00467e20 -> 0x00427610 -> 0x00465860`

The thunk reaches `0x00427610`, which keeps the exact root in `ESI` and calls `FUN_00465860` with exact root in `ECX`. `FUN_00465860` saves that incoming pointer at `[ebp-0x10]` (`0x0046586e`). Within the actual function body ending at `0x00465f65`, that saved exact root is reloaded only twice:

- `0x00465e20`, immediately followed by `add esi,0x780`; only `root+0x780` is passed onward at `0x00465e30`;
- `0x00465f4f`, immediately followed by `add ecx,0x2b0`; only `root+0x2b0` is passed onward at `0x00465f5a`.

There is no non-stack store, return, or downstream call carrying the exact root itself. Back in `0x00427610`, only `root+0x2b0` is used before the `AL` boolean return.

## Adjudication

These three direct-target paths are closed-negative as persistent/returned exact outer-root sources. Derived child/subobject pointers are intentionally not promoted back to exact-root identity.

The broader opaque-callee surface, external/unknown-origin aliases, and two-unknown-origin `HDVehicle+0x4330` reconstruction remain open. The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
