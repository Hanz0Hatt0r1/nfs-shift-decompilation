# Process 1D — `FUN_00765c40` `wheel+0x7a8` register-alias closure

This tranche closes the remaining obvious four-wheel stride alias after the earlier `wheel` and `wheel+0x678` paths. Exact `HDVehicle` identity is consumed from `SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1`.

The machine init is:

```text
0x00765fbe  lea ecx,[esi+0xba8]
0x00765fc4  fld1
0x00765fc6  mov edx,0x4
0x00765fcb  jmp 0x00765ff3
```

With `ESI=HDVehicle`, `0xba8 = wheel0 base 0x400 + 0x7a8`. The loop advances only by the canonical wheel stride:

```text
0x00766062  add ecx,0xa80
```

so the four aliases are:

```text
wheel 0: HDVehicle+0x0ba8 = wheel+0x7a8
wheel 1: HDVehicle+0x1628 = wheel+0x7a8
wheel 2: HDVehicle+0x20a8 = wheel+0x7a8
wheel 3: HDVehicle+0x2b28 = selected slot3 wheel+0x7a8
```

The complete loop window `0x00765ff1..0x00766080` is byte-hash locked. Across all 55 instructions, the only `ECX` uses are the stride update and two receiver-relative memory destinations. There is no `push ecx`, no pointer-valued memory store, and no direct call.

The writes occur after the stride increment:

```text
0x0076606b  fstp qword [ecx-0xa88]
0x00766073  fst  qword [ecx-0xa80]
```

Relative to the pre-increment wheel alias these are exactly `wheel+0x7a0` and `wheel+0x7a8`. For selected slot3 they normalize to `HDVehicle+0x2b20` and `HDVehicle+0x2b28`, both disjoint from the selected target `HDVehicle+0x28b8..+0x28bf`.

## Gate impact

This establishes only:

```text
fun00765c40_wheel_7a8_register_alias_subset_complete = true
fun00765c40_selected_slot3_wheel_7a8_alias_reached = true
fun00765c40_selected_slot3_wheel_7a8_pointer_escape_found = false
fun00765c40_wheel_7a8_selected_target_writer_found = false
```

The global register/storage gate remains false. Later `FUN_00765c40` pointers at `+0x3430/+0x35c8/+0x35f8/+0x36e0/+0x6730` are not treated as wheel aliases by numeric proximity; they require independent lifetime/callee classification. Runtime/generated pointers, callbacks, indirect entry and callee-created aliases remain open. Slot3 writer provenance, P1.3D and aggregate P1.3 remain false; provider count remains 7.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00765c40_wheel_7a8_alias_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1d_slot3_fun00765c40_carrier_handoff.json \
  --output out/p1d_slot3_fun00765c40_wheel_7a8_alias_closure.json
```

Next, classify the remaining post-`0x00766081` derived pointer families by exact storage and call lifetime before attempting a carrier-level register/storage composition.
