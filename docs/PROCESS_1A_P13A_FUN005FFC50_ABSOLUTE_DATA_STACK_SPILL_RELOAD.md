# Process 1A / P1.3A — exact stack spill/reload from absolute `.data` provenance

## Scope

The preceding contracts preserve an absolute writable `.data` load through same-block GPR copies and selected dependency-preserving transforms. This pass adds exact stack storage for that taint.

Tracked stack slots are `DWORD PTR [ebp/esp +/- immediate]` used by explicit `mov` stores and reloads. EBP-relative slots are invalidated by writes to EBP. ESP-relative slots are invalidated by push/pop-family operations or any write to ESP, rather than attempting to normalize stack deltas. Exact writes to a tracked slot from an untainted source clear that slot.

The same 16-decoded-instruction straight-line boundary remains in force. Implicit push/pop value transfer is deliberately excluded.

## Retail result

Across **2,847,850** decoded instructions and the same **1,786** absolute `.data` loads from **434** writable slots:

- **109** tracked stack spill events from **108** source loads;
- spills: **91 EBP-relative**, **18 ESP-relative**;
- **82** spills carry already-transformed taint;
- **8** exact reload events from **8** source loads;
- all 8 reloads are EBP-relative;
- transformed reloads: **0**;
- indirect `call/jmp` through any tainted register: **0**;
- reload-derived indirect transfers: **0**.

Termination inventory is 1,466 unrelated control transfers, 282 cases where all register/stack taint dies, and 38 window expirations.

## Boundary

Promoted only `p13a_fun005ffc50_absolute_data_stack_spill_reload_subset_complete=true`.

Still open: implicit push/pop transfer, normalized ESP stack tracking across stack adjustments, memory aliases, inter-block/phi carry, base/index-addressed writable sources, heap/runtime values and return provenance. Global writable-memory, callback/incoming-indirect, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_stack_spill_reload.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_transform_near_transfer.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_stack_spill_reload.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_stack_spill_reload.py
```

## Next step

Trace inter-block carry and implicit/normalized stack transfer, then base/indexed writable-memory and alias sources. Exact same-block `mov` spill/reload is now negative.
