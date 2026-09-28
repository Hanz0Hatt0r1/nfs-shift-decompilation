# Phase 433 — exact specialized-provider workspace layout

Phase 433 resolves the static storage layout behind the provider accessor
functions discovered in Phase 431.

## Provider 0

The row-pointer table begins at 0x00C21698 and contains 40 32-bit pointers,
therefore 160 bytes. It ends exactly at the factor workspace base 0x00C21738.

The factor workspace contains 0x4A6 = 1190 doubles, i.e. 0x2530 bytes. It ends
exactly at the output vector base 0x00C23C68.

The output vector contains 40 doubles and occupies 0x140 bytes.

The accessor relationships are:

    +0x04 -> 0x00C23C68
    +0x08 -> 0x00C21738
    +0x0C -> 0x00C21698
    +0x24 -> 1190
    +0x28 -> 40
    +0x2C -> [DAT_00b8d8ec]

## Provider 1

The row-pointer table begins at 0x00C1FDB0 and contains 34 pointers, 136 bytes.
It ends exactly at factor workspace 0x00C1FE38.

The factor workspace contains 0x2EA = 746 doubles, i.e. 0x1750 bytes. It ends
exactly at output vector 0x00C21588.

The output vector contains 34 doubles and occupies 0x110 bytes.

    +0x04 -> 0x00C21588
    +0x08 -> 0x00C1FE38
    +0x0C -> 0x00C1FDB0
    +0x24 -> 746
    +0x28 -> 34
    +0x2C -> [DAT_00b8d8f0]

## Consequence

The previously opaque constants are now explained by exact address arithmetic:
+0x24 is the number of doubles in the provider's static factor workspace,
while +0x28 is the fixed scalar dimension.

The factor workspace's internal slot meaning is intentionally left to the
provider solve function; this phase only authenticates its boundaries.
