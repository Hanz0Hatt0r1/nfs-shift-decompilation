# Process 1B — returned render-manager root direct-caller surface

## Scope

A retail machine-CFG pass over all 112 direct loads of `DAT_00bc185c` tracks exact 32-bit pointer identity through register copies and control flow. Partial writes to `AL/AH/AX` invalidate exact `EAX` identity.

Seven functions can reach a return while `EAX` still contains the exact outer-object pointer on at least one conditional path:

- `FUN_0040cfc0`
- `FUN_00499840`
- `FUN_004b7350`
- `FUN_004b73c0`
- `FUN_00512b00`
- `FUN_0051e010`
- `FUN_00558b30`

This is an incidental machine-register residue statement, not an API return-type claim.

## Direct caller result

Five of those functions have direct rel32 callers, for six callsites total. Every direct caller destroys or ignores the exact 32-bit `EAX` value before any store or indirect dispatch can consume it:

- `0x0040d240 -> FUN_0040cfc0`: next instruction is another call at `0x0040d245`, clobbering caller-saved `EAX`.
- `0x0049a2cf -> FUN_00499840`: control joins at `0x0049a2ef`; no `EAX` consumer precedes `0x0049a2f6 call FUN_00624930`, which clobbers it.
- `0x005115ab -> FUN_00512b00`: only `BL` is tested; both successor paths reach a call before any `EAX` use.
- `0x0051e099 -> FUN_0051e010`: `0x0051e09e call FUN_006e8da0` immediately clobbers `EAX`.
- `0x0051e8e8 -> FUN_0051e010`: `0x0051e8f0 mov eax,[ebp+0x8]` overwrites it.
- `0x008a82b0 -> FUN_00558b30`: `0x008a82b5 mov al,bl` destroys exact 32-bit pointer identity.

Therefore no direct caller persists the returned exact root, uses it as a vcall receiver, or forwards it as an exact pointer.

## Remaining indirect-only frontier

`FUN_004b7350` and `FUN_004b73c0` have no direct rel32 callsites. Their addresses occur once each as adjacent `.rdata` cells at `0x00abed00` and `0x00abed04`. The current `vtables.json` does not classify those cells as vtable slots, so this contract does not guess their table semantics.

Their indirect consumers and post-call `EAX` use remain open. The manager `+0x374` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count stays 7.
