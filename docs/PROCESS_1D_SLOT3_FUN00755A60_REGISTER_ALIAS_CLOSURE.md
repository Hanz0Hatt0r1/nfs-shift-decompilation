# Process 1D — `FUN_00755a60` exact-root and `wheel+0x7c8` alias closure

This pass bounds the remaining register-resident alias surface in the machine-proven `FUN_00755a60` selected-wheel carrier without re-owning the selected-object proof.

The merged direct-carrier contract proves that each receiver is `HDVehicle+0x400+slot*0xa80`, so the slot3 iteration enters with `ECX = HDVehicle+0x2380`. The function captures it at:

```text
0x00755a6c  push esi
0x00755a73  mov  esi,ecx    ; ESI = exact wheel root
```

Across the exact 1,297-byte body there are 70 `ESI` uses. After capture, the only instruction that copies the exact root value out of `ESI` is the already-known leaf forward:

```text
0x00755db3  mov  ecx,esi
0x00755db5  call FUN_00752fc0
```

`SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1` already proves `FUN_00752fc0` is a leaf, has no direct calls, and does not overlap the selected `+0x538` target. This tranche consumes that result rather than duplicating it.

## Derived `wheel+0x7c8` alias

A separate derived address is materialized once:

```text
0x00755c04  lea ecx,[esi+0x7c8]
```

The complete `ECX` use window before the exact-root overwrite at `0x00755db3` contains only reads/writes through `[ecx]`; `ECX` is never replaced. It therefore reaches:

```text
0x00755dae  call FUN_00753620
```

with `ECX = selected wheel+0x7c8`.

`FUN_00753620` is a bounded clamp helper. Its only receiver-relative access is `[ecx]`; it may write exactly `receiver+0x0`, has zero direct calls, and creates no deeper receiver alias. For the selected wheel this normalizes to:

```text
selected wheel + 0x7c8
```

which cannot overlap the selected target at `wheel+0x538`.

## Gate impact

This sets only the function-local bounded gates:

```text
fun00755a60_exact_root_register_alias_subset_complete = true
fun00755a60_unexpected_exact_root_register_escape_found = false
fun00755a60_wheel_7c8_derived_alias_subset_complete = true
fun00753620_selected_target_writer_found = false
```

The global register/storage, callee-created-alias, stored/escaped-alias, slot3 writer-provenance, P1.3D and P1.3 gates remain fail-closed. Provider count remains 7.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00755a60_register_alias_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json \
  evidence/p1d_slot3_register_alias_subset_closure.json \
  --output out/p1d_slot3_fun00755a60_register_alias_closure.json
```

Next, inventory callee-created aliases reached from other machine-proven selected-wheel subobjects, then compose the closed register paths without promoting the global escape gate prematurely.
