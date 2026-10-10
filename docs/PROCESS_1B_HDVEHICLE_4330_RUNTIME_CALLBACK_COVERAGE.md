# Process 1B — HDVehicle+0x4330 runtime callback coverage aggregate

`SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/2` supersedes `/1` and composes the callback/indirect-entry surfaces that Process 1B has already bounded on pinned PC retail 1.02 evidence.

## Composed closed surfaces

| Surface | Physical callsites | Possible entrypoints | Exact P1B carrier hits |
| --- | ---: | ---: | ---: |
| `CreateThread` / `__beginthreadex` | 10 | 9 | 0 |
| selected Win32/Winsock non-thread callbacks | 11 | 3 | 0 |
| `FUN_0061cdf0` Massive callback wrapper | 2 | 2 | 0 |
| CRT `_qsort` comparators | 16 | 17 | 0 |
| WinMM `waveOutOpen` / `waveInOpen` / `timeSetEvent` | 6 | 2 | 0 |
| `SetUnhandledExceptionFilter` | 3 | 0 | 0 |

Composed totals:

```text
bounded callback-capable callsites = 48
unique possible callback entrypoints = 33
exact HDVehicle+0x4330 carrier hits = 0
```

The sixth surface adds three physical calls but no entrypoint because every `SetUnhandledExceptionFilter` registration passes `NULL`.

The aggregate builder consumes six dedicated upstream contracts and fails closed if any format, readiness state, provider count, closed-subset gate, carrier-intersection result, callsite count, or unique-entrypoint count drifts.

## Reproduce

```bash
python3 tools/ghidra/build_p1b_hdvehicle_4330_runtime_callback_coverage.py \
  evidence/p1b_hdvehicle_4330_thread_start_callback_surface.json \
  evidence/p1b_hdvehicle_4330_nonthread_callback_closure.json \
  evidence/p1b_hdvehicle_4330_massive_thread_callback_wrapper.json \
  evidence/p1b_hdvehicle_4330_qsort_callback_surface.json \
  evidence/p1b_hdvehicle_4330_winmm_callback_surface.json \
  evidence/p1b_hdvehicle_4330_unhandled_exception_filter_surface.json \
  --output evidence/p1b_hdvehicle_4330_runtime_callback_coverage.json
```

## Gate discipline

This aggregate does **not** promote the global runtime callback or indirect-entry gates. The following remain open:

- callback API families not yet explicitly inventoried;
- application-owned callback wrappers other than the bounded `FUN_0061cdf0` path;
- generic function-pointer stores and copies;
- computed or encoded code pointers;
- vtable-driven or table-driven runtime registration;
- other indirect dispatch capable of entering an exact carrier.

Therefore:

```text
bounded runtime callback coverage composed = true
bounded exact-carrier callback hit found = false
runtime callback registration ruled out = false
indirect entry into carriers ruled out = false
manager+0x374 -> HDVehicle+0x4330 identity join complete = false
final 0x004b86cf rejection = false
P1.3 complete = false
external provider count = 7
```

## Next step

Use this aggregate as the no-duplication baseline. Continue with remaining finite callback API families and generic function-pointer stores/copies before any global indirect-entry promotion or final manager-identity adjudication. The two-call CRT `_bsearch` surface remains fail-closed until the unusual `FUN_0053c2d2` comparator argument is recovered at machine level.
