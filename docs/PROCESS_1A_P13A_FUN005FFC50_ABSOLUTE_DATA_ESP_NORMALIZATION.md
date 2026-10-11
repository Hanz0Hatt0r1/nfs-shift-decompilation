# Process 1A / P1.3A — simple ESP normalization for absolute `.data` provenance

## Scope

The merged implicit push/pop contract intentionally stopped on every arithmetic or LEA write to `ESP`. This bounded extension normalizes only simple byte deltas:

- `add esp, imm`
- `sub esp, imm`
- `lea esp, [esp +/- imm]`

The abstract stack is represented as exact byte offsets from the current `ESP`. Push/pop and the normalized ESP deltas move those offsets without inventing aliases. Any other `ESP`/`SP` write still terminates provenance.

## Retail result

Across the same **2,847,850** decoded instructions and **1,786** absolute writable `.data` loads from **434** unique slots:

- all **25** paths previously terminated as `unmodelled_esp_write` are now classified;
- normalization events: **23** `add esp,imm`, **2** `lea esp,[esp+0]`, **0** remaining unmodelled ESP writes in this bounded surface;
- tainted pushes increase from 208 to **209** because one previously truncated path continues far enough to reach a push;
- tainted pop reloads remain **0**;
- indirect `call/jmp` through any tracked register remain **0**;
- pop-derived indirect transfers remain **0**.

Termination after normalization is: 259 all-taint-dead paths, 1,507 unrelated control transfers, and 20 window expirations.

## Gate

Promoted only `p13a_fun005ffc50_absolute_data_esp_normalization_subset_complete=true`.

Still open: inter-block/phi carry, base/index-addressed writable `.data` loads, writable-memory aliases, heap/runtime values, general return provenance, callback/incoming-indirect closure, stored/escaped aliases, slot0/slot1 and aggregate P1.3. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_esp_normalization.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_implicit_push_pop.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_esp_normalization.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_esp_normalization.py
```

## Next step

Trace base/index-addressed writable `.data` loads and then inter-block carry. Simple same-window ESP normalization is now bounded.
