# Process 1A / P1.3A — fold represented secondary singletons into congruence

## Scope

The preceding 27-site contract proves that every represented secondary operand is an exact singleton. This pass evaluates those full affine addresses in the same sound finite-set/congruence fixed point used by the single-TOP refinement.

## Retail result

PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`:

- 27 folded-secondary sites
- 12 ruled out for both callback slots
- 15 remain compatible with at least one target
- fixed point: 116,677 entries / 420,030 entry updates

The 12 exclusions are the `+1`, `+2`, and `+3` byte-offset siblings in four address groups (`0x00572957/5e/65`, `0x00878f88/8f/96`, `0x00a64936/3d/44`, `0x00a64e46/4d/54`). After exact secondary folding, the widened primary produces modulo-4 classes; these three nonzero residues cannot equal either 4-byte-aligned callback slot `0x00b87b7c` or `0x00b87b80`.

## Gate effect

Only the folded-secondary congruence subset and the existence of 12 sound exclusions are promoted. The remaining 15 sites, the 1,095 missing-secondary sites, global single-TOP/TOP alias closure and all runtime/callback/slot/P1.3 gates remain fail-closed. External provider count remains 7.

## Next

Trace provenance for the 15 target-compatible folded-secondary sites. Independently add bounded provenance for the missing secondary GPR in the 1,095-site class.
