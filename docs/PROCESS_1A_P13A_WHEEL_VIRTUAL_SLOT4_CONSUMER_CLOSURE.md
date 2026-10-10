# Process 1A / P1.3A — persisted wheel virtual slot `+0x4` consumer closure

## Scope

The merged runtime queue-store contract proves that `FUN_0076df50` persists each exact wheel-root pointer in a runtime queue node and that the generic fiber consumer reloads that pointer and invokes wheel vtable slot `+0x4`. Retail vtable `0x00b09a68` resolves the slot to `0x0075cfb0`.

This pass closes that exact consumer with respect to P1.3A selected fields. For an exact wheel root, the selected target is wheel-relative `+0x538..+0x53f` (`HDVehicle+0x938..+0x93f` for slot0 and `HDVehicle+0x13b8..+0x13bf` for slot1).

## `0x0075cfb0` result

The complete pinned machine range is `0x0075cfb0..0x00760b48` (15,256 bytes / 3,841 decoded instructions). The method captures the exact persisted wheel receiver as `ESI=ECX` at `0x0075cfe5`.

Across the entire range:

- there are **zero** ESI-relative memory accesses whose byte range overlaps wheel `+0x538..+0x53f`;
- the exact root pointer is never stored to non-stack memory;
- it is never pushed after receiver capture;
- ESI is not redefined before its epilogue restore;
- the only exact-root register copy is `0x007606f4: ECX=ESI`.

That copy feeds exactly one call:

```text
0x007606f4  mov ecx,esi
0x00760705  call FUN_00755790
```

## Forward callee

`FUN_00755790` is pinned as the complete 442-byte range `0x00755790..0x0075594a`. It captures the wheel receiver in ESI and performs scalar wheel-relative reads/writes including `+0x4b8/+0x4c0/+0x4c8/+0x500`.

It contains zero memory accesses overlapping `+0x538..+0x53f`, stores no exact root pointer, pushes no exact root after capture, creates no exact-root GPR copy, and does not further forward the exact root.

Thus the persisted queue pointer has a real indirect consumer, but this bounded consumer chain is **not** a producer for the selected P1.3A f64 field.

## Gate effect

Promoted only:

- `p13a_persisted_wheel_virtual_slot4_consumer_subset_complete = true`;
- `persisted_wheel_virtual_slot4_only_exact_root_forward_closed = true`.

Negative bounded results:

- selected-target write found = false;
- exact-root pointer persistence inside this consumer = false.

The upstream runtime queue pointer store remains positive. Therefore runtime-generated selected-wheel pointer stores, broader stored aliases, callbacks/incoming-indirect entry, slot0, slot1 and aggregate P1.3 all remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_wheel_virtual_slot4_consumer.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun0076df50_runtime_wheel_queue_store.json \
  --output evidence/p1a_p13a_wheel_virtual_slot4_consumer_closure.json
pytest -q tests/test_process1a_p13a_wheel_virtual_slot4_consumer.py
```

## Next step

Enumerate other `FUN_00a62f60` registrations whose task pointer can be an exact wheel root or selected-wheel-derived alias, then compose those positives with the now-closed slot `+0x4` consumer and the residual indexed lifetimes.
