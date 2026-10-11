# Process 1A / P1.3A — base/index writable `.data` stack spill/reload subset

## Result

Starting from the verified 63 base/index-addressed writable `.data` loads and preserving the upstream copy/transform taint, this subset tracks exact `mov` spills and reloads through `DWORD PTR [ebp/esp +/- immediate]` slots within the same 16-decoded-instruction straight-line window.

PC retail 1.02 contains exactly **2 tracked stack spills from 2 loads**: one EBP-relative spill and one ESP-relative spill. One spill carries transformed taint. There are **0 exact reloads**, **0 reload-derived indirect transfers**, and **0 tainted-register indirect transfers**.

Concrete spills:

- load `0x004da33e` from effective address `0x00b82304` -> `ECX` spill at `0x004da344` to `[ebp-0x28]`, untransformed, distance 1;
- load `0x009f71a8` from effective address `0x00bac6e0` -> transformed `EAX` spill at `0x009f71c3` to `[esp+0x8]`, distance 7.

Termination inventory remains 59 other control transfers and 4 all-taint-dead paths.

## Boundary

Promoted only `p13a_fun005ffc50_base_indexed_data_stack_spill_reload_subset_complete=true`. Implicit push/pop, ESP-delta normalization for this base/index subset, memory aliases, inter-block/phi carry, and aggregate writable-source/callback/slot0/slot1/P1.3 gates remain fail-closed. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_stack_spill_reload.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_base_indexed_data_transform_near_transfer.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_stack_spill_reload.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_stack_spill_reload.py
```

## Next

Trace implicit/normalized stack carriers, then bounded inter-block carry for remaining base/index-derived writable-memory provenance.
