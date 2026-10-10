# Process 1A / P1.3A — `FUN_005ffc50` read-only image + stack reconstruction

## Scope

Merged `SHIFT.P1A.P13AFun005ffc50SimpleImmediateReconstruction/1` closes direct/raw-pointer entry and straight-line GPR construction from immediate/known-register values. The next bounded class is a pointer reconstructed from an image-backed dword or an explicit stack local before an indirect transfer.

The analyzer tracks `.text`/`.rdata` 32-bit dword loads, explicit `ESP`/`EBP` stack slots, `push`/`pop`, and the same bounded integer transformations used by the simple-GPR pass. Standard `mov ebp,esp` frames are normalized onto the current `ESP` delta. Calls, jumps, conditional branches, loops and returns/traps end the straight-line region.

Writable `.data` is intentionally excluded from the static-source claim because startup/runtime code can replace it before a load.

## Retail result

Across **2,847,850** decoded instructions the bounded scanner observes **484** image-backed dword loads (`483` from `.rdata`, `1` from `.text`) but:

- **0** exact `0x005ffc50` register materializations;
- **0** exact `0x005ffc50` explicit stack-slot materializations;
- **0** indirect `call`/`jmp` transfers to `0x005ffc50` through a tracked register, stack slot or read-only image memory operand.

Synthetic regressions prove both important positive cases are recognized: `.text` dword base + arithmetic -> `call reg`, and `EBP` local base + arithmetic -> reload -> `call reg`.

## Gate effect

Promoted only `p13a_fun005ffc50_readonly_image_and_explicit_stack_reconstruction_subset_complete=true`.

Still fail-closed: writable-memory/runtime callback slots, PIC/return-address reconstruction, inter-block dataflow, encoded/split pointers, dynamic registry registration, global callback/incoming-indirect closure, runtime-generated selected-wheel pointer-store negative, stored aliases, slot0, slot1 and aggregate P1.3. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_static_memory_stack_reconstruction.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_simple_reconstruction.json \
  --output evidence/p1a_p13a_fun005ffc50_static_memory_stack_reconstruction.json
pytest -q tests/test_process1a_p13a_fun005ffc50_static_memory_stack_reconstruction.py
```

## Next step

Trace writable-memory/runtime callback slots and PIC/inter-block entry to `FUN_005ffc50`. The direct/raw, simple GPR, read-only image seed and explicit stack-local subsets no longer need to be rescanned.
