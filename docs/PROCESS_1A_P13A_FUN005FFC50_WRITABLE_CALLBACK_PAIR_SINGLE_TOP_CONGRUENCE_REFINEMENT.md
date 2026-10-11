# Process 1A / P1.3A — single-TOP congruence refinement

## Scope

This step refines only the 2,686 `single_top_only` static memory-use sites emitted by the callback-slot TOP inventory. It does not claim global alias closure.

The previous finite-set domain widens a register to `TOP` after more than eight distinct exact constants meet. This pass replaces that loss of all value structure with a sound hybrid domain: up to eight exact constants are retained; larger joins keep a 32-bit congruence hull. The hull records a residue/modulus relation that contains every represented exact value.

Affine operations already supported by the callback-slot series preserve that relation: MOV copy/immediate, LEA expressions, immediate ADD/SUB, and self-XOR zeroing. Direct JMP/Jcc propagation runs to the same fixed point, and calls retain only the established callee-saved EBX/ESI/EDI/EBP state.

## Retail result

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

- upstream single-TOP-only sites: 2,686
- congruence-incompatible with both callback slots: 290
- congruence-compatible with at least one slot: 1,145
- expressions requiring another unrepresented register value: 1,244
- not observed in the refined fixed point: 7
- unresolved after this step: 2,396
- refined CFG entries: 116,677
- entry-state updates: 420,030
- refined memory-use observations: 33,644

The 290 excluded sites are rejected only when every refined observation is known and neither `0x00b87b80` nor `0x00b87b7c` satisfies the observed congruence class. Observed exclusion moduli are 2, 4, 8, 16, 32, 64 and 128.

## Gate effect

Only `p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement_subset_complete` is promoted. The remaining single-TOP frontier, mixed/two-TOP classes, nonconstant/runtime aliases, writable-memory closure, callback closure, slot0/slot1 and aggregate P1.3 remain fail-closed. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement.py \
  SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_writable_callback_pair_top_site_inventory.json \
  --output /tmp/p1a_single_top_congruence.json
pytest -q tests/test_process1a_p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement.py
```

## Next

Refine the 1,145 congruence-compatible sites with provenance classes. Treat the 1,244 sites containing another unrepresented register as a separate unresolved class rather than folding them into the same proof.
