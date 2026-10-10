# Process 1A / P1.3A — `FUN_0076df50` runtime wheel queue store

## Result

This closes one **positive** runtime-generated selected-wheel pointer path that remained outside the bounded materializer composition.

A selected-HDVehicle callsite at `0x00798f97` loads literal receiver `0x00c13700` and calls `FUN_0076df50`. The initialization loop starts `EBX = HDVehicle+0x400`, advances by `0xa80`, and executes exactly four iterations. The resulting roots are `HDVehicle+0x400/+0xe80/+0x1900/+0x2380`, so slot0 and slot1 are both included.

For every root the loop first calls `FUN_00a62690`, which initializes only scalar wheel-local fields, then passes the exact root in EDX to `FUN_00a62f60` with queue manager `HDVehicle+0x6730` in ECX.

`FUN_00a62f60` preserves the wheel root in EBX, creates a runtime node through `FUN_00a62c30`, and at:

```text
0x00a62fc0  mov [esi], ebx
```

stores the **exact wheel-root pointer** at `runtime_node+0x0`. Thus one `FUN_0076df50` initialization registers four wheel pointers and positively registers both P1.3A selected roots.

## Consumer closure

The store is not dead data. `FUN_00a62940` later reloads the node task pointer, packages it for `lpStartAddress_00a62710`, and the fiber entry executes:

```text
ESI = stored task pointer
EAX = [ESI]       ; vptr
EAX = [EAX+0x4]
ECX = ESI
call EAX
```

The wheel constructor `FUN_0076b060` installs vptr `0x00b09a68`. Retail `.rdata` resolves:

```text
vtable +0x0 -> 0x0076b100
vtable +0x4 -> 0x0075cfb0
```

Therefore the persisted wheel pointer reaches an exact indirect virtual consumer at `0x0075cfb0`.

## Gate effect

Promoted only the bounded positive facts:

- `p13a_fun0076df50_runtime_wheel_queue_store_subset_complete = true`;
- `runtime_generated_selected_wheel_pointer_store_found = true`;
- slot0 and slot1 runtime wheel-pointer stores found;
- stored wheel pointer indirect virtual consumer found;
- wheel slot `+0x4` target resolved to `0x0075cfb0`.

The positive store means the broad negative gate **must remain false**:

- `runtime_generated_selected_wheel_pointer_stores_ruled_out = false`.

`stored_or_escaped_aliases_ruled_out`, callback/incoming-indirect, slot0, slot1 and aggregate P1.3 also remain fail-closed. Provider count remains 7.

The manager at `HDVehicle+0x6730` is still a distinct non-wheel object; the important fact here is that its allocated queue node payload contains an exact wheel-root pointer.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun0076df50_runtime_wheel_queue_store.py /path/to/SHIFT.exe \
  --output evidence/p1a_p13a_fun0076df50_runtime_wheel_queue_store.json
pytest -q tests/test_process1a_p13a_fun0076df50_runtime_wheel_queue_store.py
```

## Next step

Trace the resolved wheel virtual target `0x0075cfb0` as a selected-wheel consumer and enumerate any other runtime wheel-root registrations/stores outside `FUN_0076df50`. Independently close the residual indexed exact-root lifetimes in `FUN_00765850` and `FUN_00765aa0`.
