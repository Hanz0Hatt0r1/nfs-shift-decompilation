# Process 1A / P1.3A — writable callback-pair computed alias sources

## Result

After #1954 removes exact embedded slot-address literals as an alias source, this pass tracks exact GPR constants within each straight-line region until overwrite or control boundary. Calls retain only x86 callee-saved `EBX/ESI/EDI/EBP` constants.

Across all **2,847,850** decoded PC retail 1.02 instructions:

- exact register formations equal to `0x00b87b80` or `0x00b87b7c`: **0**;
- GPR-based bracketed memory operands resolving exactly to either slot: **0**.

The formation surface covers immediate/copy `mov`, exact `lea`, immediate `add/sub`, and self-`xor` zeroing used by the established address-state model. There is therefore no branch-local exact computed alias to either callback slot.

## Boundary

This does not yet carry constants across direct CFG edges. Nonconstant aliases, stack/heap pointer copies, runtime/external mutation and reconstructed setter/config entry remain open. Broad alias/writable-memory/callback/P1.3 gates stay fail-closed; provider count remains 7.

## Next

Carry exact address constants across resolved direct CFG edges, then address nonconstant/runtime mutation sources.
