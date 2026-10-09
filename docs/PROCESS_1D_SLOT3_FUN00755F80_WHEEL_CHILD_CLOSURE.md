# Process 1D — `FUN_00755f80` exact wheel-child closure

`SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1` already proves `FUN_00763570` receives the `HDVehicle` root. Retail machine code then gives the exact wheel path:

```text
0x0076358e  EDI = ECX = HDVehicle
0x007635f4  EAX = EDI + 0x400
0x00763609  [EBP-4] = wheel0
0x0076360c  ECX = [EBP-4]
0x0076360f  call FUN_00755f80
0x0076361b  [EBP-4] += 0xa80
0x00763625  compare iteration with 4
```

So iteration 3 enters `FUN_00755f80` with exact selected slot3 receiver `HDVehicle+0x2380`.

Inside `FUN_00755f80`, `0x00755f9a` captures the wheel root in ESI. The function never writes through ESI and never stores/pushes that exact root after capture. It immediately dereferences `[wheel+0x420]`; both direct callees receive child-derived state, and the only persistent writes are to that child object at `+0x48/+0x50/+0x58`.

Therefore selected local target `wheel+0x538` (`HDVehicle+0x28b8`) is not written or forwarded through this path.

Reproduce with:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00755f80_wheel_child_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1a_p13a_slot01_x87_reuse_tranche_closure.json \
  --output out/p1d_slot3_fun00755f80_wheel_child_closure.json
```

This closes only `FUN_00763570 -> FUN_00755f80`. Other exact selected-wheel paths, stored aliases, out-of-line chunks, indirect calls and callback carriers remain open. Slot3 writer provenance, P1.3D and aggregate P1.3 remain false; external provider count remains 7.
