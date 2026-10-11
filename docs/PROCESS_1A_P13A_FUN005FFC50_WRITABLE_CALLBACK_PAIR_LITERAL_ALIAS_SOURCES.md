# Process 1A / P1.3A — writable callback-pair exact-literal alias sources

## Result

For PC retail 1.02, every exact 32-bit image literal equal to the two heavily used callback-slot VAs is fully accounted for by already-known direct absolute memory operands.

- `0x00b87b80`: 29 raw occurrences = 26 indirect transfers + 2 direct writes + 1 startup snapshot load.
- `0x00b87b7c`: 54 raw occurrences = 51 indirect transfers + 2 direct writes + 1 startup snapshot load.
- Unclassified exact-address literals: **0**.

The analyzer maps each raw little-endian occurrence one-to-one into the containing decoded instruction. There are no exact slot-VA literals elsewhere in `.rdata`, `.data`, resources, or other image bytes that could directly seed an address-taken alias.

## Boundary

This closes only exact embedded slot-address literals. Computed addresses such as base+offset/index, copied runtime pointers, external mutation and reconstructed/indirect entry to the setter/config path remain open. Therefore the broad alias/writable-memory/P1.3 gates stay fail-closed and provider count remains 7.

## Next

Trace computed base/index address formation that can resolve to either callback slot, then classify remaining runtime mutation sources.
