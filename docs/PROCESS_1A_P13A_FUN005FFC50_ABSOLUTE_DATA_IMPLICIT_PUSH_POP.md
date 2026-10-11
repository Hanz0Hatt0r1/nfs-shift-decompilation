# Process 1A / P1.3A — implicit push/pop transfer of absolute `.data` provenance

## Scope

The explicit stack contract tracks `mov` spill/reload through exact EBP/ESP-relative slots. This contract isolates the separate x86 implicit stack-value path: a tainted GPR is `push`ed, nested pushes/pops are modeled as abstract stack cells, and a later `pop` may restore that exact dependency into another GPR.

GPR provenance still includes the bounded same-block copies/transforms proved upstream. Arbitrary writes/arithmetic on ESP stop this subset rather than guessing a normalized stack offset. `pushf/pusha` add unknown cells and corresponding pop-family operations consume an unknown cell.

## Retail result

Across **2,847,850** decoded instructions and the same **1,786** absolute `.data` loads from **434** slots:

- **208** tainted implicit `push` events from **208** source loads;
- source registers: EAX 92, ECX 71, EDX 44, ESI 1;
- **12** pushes carry already-transformed taint;
- tainted `pop` reloads before the bounded exit: **0**;
- indirect transfers through any tracked register: **0**;
- pop-derived indirect transfers: **0**.

Termination inventory: 1,482 unrelated control transfers, 259 all-taint-dead paths, 25 unmodelled ESP writes, and 20 window expirations.

## Boundary

Promoted only `p13a_fun005ffc50_absolute_data_implicit_push_pop_subset_complete=true`.

Still open: normalization across arbitrary ESP arithmetic/LEA, inter-block/phi carry, base/index-addressed writable sources, memory aliases, heap/runtime values and return provenance. The explicit `mov` stack spill/reload subset remains separately covered by the upstream contract. All global writable-memory, callback/incoming-indirect, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_implicit_push_pop.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_stack_spill_reload.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_implicit_push_pop.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_implicit_push_pop.py
```

## Next step

Normalize simple ESP arithmetic and then trace inter-block/base-indexed writable-memory provenance. Implicit push/pop transfer is now bounded.
