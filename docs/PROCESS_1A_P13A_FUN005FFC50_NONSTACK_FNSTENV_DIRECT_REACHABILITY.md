# Process 1A / P1.3A — non-stack FNSTENV direct reachability

## Scope

The stack-local `FNSTENV [esp]` paths are handled separately. Two additional linear-disassembly `FNSTENV` decodes remain at `0x004177e4` and `0x0050d063`. This contract asks only whether ordinary direct control flow can enter either decode.

## `0x004177e4`

There are no direct `call`, `jmp`, `jcc` or loop targets to `0x004177e4`. Ordinary fallthrough is stopped by `0x004177e2 ret`.

The 44 bytes beginning exactly at `0x004177e4` are eleven aligned little-endian dwords. Every value points into nearby `.text` (`0x004175d7..0x004177d9`), including `0x004177d9`, `0x004175e3`, `0x00417630`, `0x00417654`, `0x0041768b`, `0x0041774b`, `0x00417768`, `0x004177a8`, and `0x004177cc`. That is table-shaped machine data rather than a direct-entry `FNSTENV` path. Arbitrary computed indirect entry is still not ruled out.

## `0x0050d063`

There are no direct `call`, `jmp`, `jcc` or loop targets to `0x0050d063`. The surrounding `0x0050d035..0x0050d070` window is 59 bytes: 56 are `INT3` (`0xcc`); the only other bytes are one `NOP` and the two bytes `d9 b3` that cause the linear `FNSTENV` decode. The preceding code at `0x0050d030` is an unconditional jump away; the next trampoline begins at `0x0050d070`.

Thus ordinary direct/fallthrough control flow does not enter this decode. Computed/runtime entry into padding remains outside the claim.

## Gate effect

Promoted only `p13a_fun005ffc50_nonstack_fnstenv_direct_reachability_subset_complete=true`. The global indirect/reconstructed-entry gates stay fail-closed; provider count remains 7.

## Next step

Move the `FUN_005ffc50` frontier to writable-memory/runtime callback slots and inter-block/return-value provenance. All four retail `FNSTENV` decodes now have bounded direct/static classifications.
