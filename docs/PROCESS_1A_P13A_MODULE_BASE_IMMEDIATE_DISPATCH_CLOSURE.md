# Process 1A / P1.3A — module-base immediate-dispatch closure

## Scope

The merged runtime module-base storage proof identifies two getter slots on the exact `0x00bbf960` runtime receiver: vtable `+0x84` returns stored module base field `0x00bfa4f8+0x4`; `+0xa4` returns `+0xc`.

This pass closes a bounded consumer class only: direct calls to `FUN_00886980` followed, within at most 16 machine instructions and before any intervening call, by a tracked receiver-alias → vptr → slot → indirect-call chain. Direct call/jump transfers to the getter bodies are also inventoried independently.

## Retail result

The authoritative PC retail image contains exactly **203** direct calls to `FUN_00886980`.

The bounded immediate-dispatch tracker recovers exactly **14** receiver-proven virtual calls:

- slot `+0x3c`: 3
- slot `+0x48`: 4
- slot `+0x58`: 5
- slot `+0x5c`: 1
- slot `+0x80`: 1

The sole `+0x80` row is the already-proven startup setter at `0x00a691b2` after the getter call at `0x00a69197`.

There are **zero** immediate receiver-proven dispatches to module-base getter slots `+0x84` and `+0xa4`. There are also **zero** whole-image direct `call`/`jmp` transfers to getter bodies `FUN_00886c00` and `FUN_00886c70`.

This removes the simplest getter-consumer class. It does not prove that a receiver cannot be saved, copied, returned, or reached later through another alias before dispatch.

## Gate

```text
module-base immediate-dispatch subset complete = true
direct getter-body transfers                   = 0
immediate receiver-proven dispatches           = 14
module-base getter slot +0x84 dispatches        = 0
module-base getter slot +0xa4 dispatches        = 0
all getter consumer paths complete              = false
delayed/stored receiver aliases ruled out       = false
callback / incoming-indirect ruled out          = false
slot0 / slot1 / P1.3 complete                   = false
provider count                                  = 7
```

## Next step

Trace delayed or stored aliases of the exact runtime receiver and callback/registration paths. Keep selected-wheel data-pointer persistence as the independent parallel P1.3A frontier.
