# Phase 479 — corrective reset/cleanup equivalence

Phase 479 corrects the Phase 468 interpretation of provider reset zeroing.

## Correction

The reset profile must include **both** direct `DAT_x = 0` stores and `FUN_0040cec0(..., 0, size)` bulk clears. Counting direct stores alone under-reports the reset zero domain.

Against the real `SHIFT.exe.c` source, the corrected domains are:

- provider 0: **370** packed-workspace zero slots + **40** output-vector zero slots = **410** reset-zero slots;
- provider 1: **280** packed-workspace zero slots + **34** output-vector zero slots = **314** reset-zero slots.

These sets exactly match the corresponding cleanup coverage domains from Phase 467.

## Diagonal seeds

Both reset functions still contain exactly one `1.0` seed per selector case: 40 cases for provider 0 and 34 for provider 1. A per-case audit confirms that the seed address is not simultaneously cleared by another zero operation inside the same case block.

The fact that a seed address may appear in the global zero set is no longer interpreted as a temporal overwrite: global set equality and per-case instruction order are distinct facts.

## Resulting storage model

`cleanup zero coverage == reset zero-write domain`

`reset case N → zero/clear associated storage → write exact 1.0 seed`

The second line is constrained to the addresses within that case block; no claim is made about ordering across different selector invocations.

## Scope boundary

This correction remains storage-level. It does not infer matrix semantics, provider class names, or physical units.
