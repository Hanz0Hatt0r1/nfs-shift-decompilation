# Process 1A / P1.3A — target-compatible congruence frontier

## Scope

This pass inventories the 15 folded-secondary sites that remain compatible with at least one callback slot after #1984. It records the terminal congruence strength after the same sound fixed point stabilizes. No site is ruled out here.

## Retail result

PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`:

- 15 target-compatible sites
- terminal `0 mod 1`: 7 sites
- terminal `0 mod 4`: 5 sites
- terminal `0 mod 8`: 2 sites
- terminal `4 mod 8`: 1 site
- instruction classes: CMP 7, MOV 5, LEA 3
- fixed point remains 116,677 entries / 420,030 updates

Seven sites have modulus 1, meaning congruence arithmetic has lost all exclusion power there. The remaining eight preserve modulo-4/8 structure, but that structure is still compatible with at least one of `0x00b87b7c` / `0x00b87b80`. Deeper refinement therefore needs producer/join provenance rather than another arithmetic-only domain.

## Gate effect

Promoted only:

- `p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier_subset_complete`
- `writable_callback_pair_target_compatible_frontier_requires_provenance_refinement`

No alias-closure, callback, slot0/slot1, writable-runtime or aggregate P1.3 gate is promoted. External provider count remains 7.

## Next

Trace widening/join provenance for the primary register at these 15 sites, prioritizing the seven modulus-1 sites. Keep the separate 1,095 missing-secondary frontier open.
