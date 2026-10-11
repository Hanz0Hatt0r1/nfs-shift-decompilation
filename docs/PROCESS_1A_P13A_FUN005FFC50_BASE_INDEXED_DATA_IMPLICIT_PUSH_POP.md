# Process 1A / P1.3A — base/index writable `.data` implicit push/pop subset

## Result

Starting from the 63 verified base/index-addressed writable `.data` loads, this subset composes bounded GPR copy/transform provenance with implicit `push`/`pop` stack cells for 16 decoded instructions.

PC retail 1.02 contains exactly **5 tainted push events from 5 loads**: EAX 3 and ECX 2. None is transformed before the push. There are **0 tainted pop reloads**, **0 pop-derived indirect transfers**, and **0 tainted-register indirect transfers**.

Push sites are `0x004b1c17`, `0x004cd464`, `0x005f51e2`, `0x008d1958`, and `0x00d74304`. Their source load effective addresses are `0x00b82034`, `0x00b822a4`, `0x00b869d0`, `0x00b95320`, and `0x00b82030`.

Termination inventory is 61 other control transfers and 2 all-taint-dead paths.

## Boundary

Promoted only `p13a_fun005ffc50_base_indexed_data_implicit_push_pop_subset_complete=true`. ESP arithmetic/LEA normalization, inter-block/phi carry, broader aliases and aggregate writable-source/callback/slot0/slot1/P1.3 gates remain fail-closed. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_implicit_push_pop.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_base_indexed_data_stack_spill_reload.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_implicit_push_pop.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_implicit_push_pop.py
```

## Next

Normalize simple ESP arithmetic/LEA for this base/index subset, then trace bounded inter-block carry.
