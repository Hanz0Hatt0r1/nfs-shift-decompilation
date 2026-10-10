# Process 1A / P1.3A — simple `FUN_005ffc50` immediate reconstruction

## Scope

The merged direct-entry closure proves that `FUN_005ffc50` has no direct `creg` callers and no exact raw VA/RVA pointer literal. This pass closes one additional reconstructed-entry class: straight-line GPR constant construction inside one control-flow region.

The analyzer performs conservative constant propagation across `mov`, simple `lea`, immediate/known-register arithmetic and bitwise operations, immediate shifts, `inc/dec/neg/not`, three-operand immediate `imul`, and register `xchg`. Any call, jump, conditional branch, loop, return/trap, unmodelled register write, or subregister write drops the affected state.

## Retail result

Across **2,847,850** decoded instructions there are:

- **0** exact materializations of `0x005ffc50` in a tracked GPR;
- **0** indirect `call reg` / `jmp reg` transfers where the tracked register equals `0x005ffc50`.

This is independent of the already-merged raw literal scan: it covers multi-instruction forms such as `mov reg,base; add reg,delta` and similarly bounded arithmetic/`lea` reconstruction.

## Boundary

This is deliberately not a whole-program points-to proof. Memory loads, stack spill/reload, split byte/word assembly, table lookup, relocations, return-value provenance, and runtime-generated values remain open. State is discarded across every control-flow transfer rather than merged path-sensitively.

Promoted only `p13a_fun005ffc50_simple_straight_line_immediate_reconstruction_subset_complete=true`. Global reconstructed-entry, callback/incoming-indirect, stored-alias, slot0, slot1, and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_simple_reconstruction.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_direct_creg_entry_closure.json \
  --output evidence/p1a_p13a_fun005ffc50_simple_reconstruction.json
pytest -q tests/test_process1a_p13a_fun005ffc50_simple_reconstruction.py
```

## Next step

Trace memory-backed, stack-backed, or runtime/indirect incoming entry to `FUN_005ffc50`. Direct/raw and simple straight-line immediate reconstruction no longer need to be rescanned.
