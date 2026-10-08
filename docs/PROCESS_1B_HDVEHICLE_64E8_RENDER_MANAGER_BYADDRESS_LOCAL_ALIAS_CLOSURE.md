# Process 1B — render-manager by-address local alias closure

## Scope

The merged exact-root receiver work still leaves opaque callee-created aliases open. During review of the bounded direct-target surface, two concrete paths save the exact render-manager outer root in a stack local and then pass the **address of that local** to a helper. Those paths require explicit adjudication because a helper could otherwise read the original pointer and persist it elsewhere.

PC retail 1.02 machine transfer is authoritative. Decompiled source is navigation-only.

## `FUN_00462250`

At entry the exact receiver is in `ECX`. After `mov ebp,esp`, instruction `0x00462253 push ecx` materializes that value at `[ebp-0x4]`. Later `0x00462294 lea edx,[ebp-0x4]` passes the local address while `ECX` is switched to the derived receiver `root+0x2c0`; `0x00462299` calls thunk `0x00481860 -> 0x00d5ddb0`.

Inside the helper, `0x00d5ddc7 mov esi,edx` captures the pointer-to-local. The first access to the pointed slot is not a read: `0x00d5de0b mov dword ptr [esi],0` overwrites it. Therefore the original exact outer root is destroyed before the helper can observe or copy it. Later helper writes are replacement queue/object pointers and are not promoted back to the original root.

## `0x004695e0 -> FUN_004b1ea0`

The direct worklist target `0x004695e0` tail-jumps to `0x004b1ea0` without changing the receiver. In the body, `0x004b1ea3 push ecx` materializes the exact receiver at `[ebp-0x4]`; `0x004b1ead lea edx,[ebp-0x4]` passes the address while `ECX` switches to derived `root+0x780`. The call at `0x004b1eb2` reaches thunk `0x0045ecf0 -> 0x00d52670`.

The helper captures the pointer-to-local with `0x00d5269c mov esi,edx`, and its first access to that slot is `0x00d526ef mov dword ptr [esi],0`. Again, the original exact root is overwritten before any read and cannot escape through this helper path.

## Adjudication

These two address-of-stack-local paths are closed-negative as exact outer-root persistence sources. This is intentionally narrower than a full opaque-callee closure: other direct-target behaviors, external/unknown-origin aliases, and two-unknown-origin `HDVehicle+0x4330` reconstruction remain open.

The `manager+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. External provider count remains 7.
