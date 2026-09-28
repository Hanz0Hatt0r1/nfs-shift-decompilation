# Phase 434 — provider workspace-size domain correction

Phase 434 resolves the last semantic ambiguity in the provider workspace accessors.

## Direct PE evidence

Provider 0:

    FUN_007d2ee0 (+0x24) -> 0x4A6 = 1190
    FUN_007d2f00 (+0x2C) -> [DAT_00b8d8ec] = 0x4A6 = 1190

Provider 1:

    FUN_007d2f40 (+0x24) -> 0x2EA = 746
    FUN_007d2f60 (+0x2C) -> [DAT_00b8d8f0] = 0x2EA = 746

The .data bytes at DAT_00b8d8ec/f0 are therefore the same workspace-size values returned immediately by +0x24.

## Runtime destination

FUN_007b3820 stores the +0x2C result into each BODY runtime record at +0xA8. The generic fallback instead initializes the same slot from scalar_count * scalar_count.

The provider-neutral runtime now describes the accepted-provider value as the observed provider workspace size. Backward-compatible field names remain unchanged where external callers may already depend on them.

## Consequence

    +0x04 -> output vector
    +0x08 -> factor workspace
    +0x0C -> row-pointer table
    +0x24 -> factor workspace double count
    +0x28 -> scalar count
    +0x2C -> same factor workspace double count in the shipped PE

The broader class/type semantics of the +0x2C method remain intentionally unassigned.
