# Phase 430 — provider-neutral backend construction contract

Phase 430 closes the visible ABI around the accepted-provider branch of FUN_007b3820 without inventing provider or PhysX class names.

## Exact call sequence

FUN_007b3820 probes:

1. slot 0 = DAT_00c23da8
2. slot 1 = DAT_00c23dac
3. selector index 2 -> null -> generic fallback

For each candidate, the retail code invokes vtable +0x14 with the current row-table pointer. A rejecting provider advances to the next slot.

For the accepted provider:

    release old matrix (+0x38)
    free old row table (+0x3c)
    provider +0x0c() -> physics_system +0x3c
    provider +0x04() -> physics_system +0x40
    provider +0x08() -> physics_system +0x44
    provider +0x2c() -> per-body +0xa8 domain
    store provider pointer -> physics_system +0x48

The +0x2c return is significant: the generic path uses scalar_count * scalar_count for the per-body +0xa8 domain, while the accepted provider replaces that value with the provider-returned domain.

## Fallback

When all provider candidates reject, the retail path returns to FUN_007b2010 / FUN_007b1360 and retains:

    secondary_domain = scalar_count * scalar_count

The new Python layer exposes this as a provider-neutral state machine and records the exact vtable call trace, allowing a future live provider capture or adapter to be compared without assigning undocumented SDK semantics.

## Provider identity

FUN_007d2f70 initializes slot 0 with vtable PTR_FUN_00b0fc5c; FUN_007cd980 initializes slot 1 with vtable PTR_FUN_00b0fc8c. These are identity evidence only.
