# Process 1D — `FUN_00765c40` four-wheel register-alias closure

Merged P1D evidence proves that `FUN_00765c40` receives the exact `HDVehicle` root. This tranche consumes that identity and closes one separate register-only wheel alias loop without reopening the function's already-classified side effects.

The root is captured at function entry:

```text
0x00765c5f  mov esi,ecx     ; ESI = HDVehicle
```

The four-wheel loop is exact PC-retail machine code:

```text
0x00765eac  xor edx,edx
0x00765eae  lea ecx,[esi+0x400]
0x00765eb4  fld qword [esi+0x98]
0x00765eba  sub esp,0x8
0x00765ebd  fstp qword [esp]
0x00765ec0  push edx
0x00765ec1  call FUN_00752fa0
0x00765ec6  add edx,0x1
0x00765ec9  add ecx,0xa80
0x00765ecf  cmp edx,0x4
0x00765ed2  jl  0x00765eb4
```

Because `FUN_00752fa0` does not modify `ECX`, the receiver sequence is:

```text
iteration 0: HDVehicle+0x0400
iteration 1: HDVehicle+0x0e80
iteration 2: HDVehicle+0x1900
iteration 3: HDVehicle+0x2380  <- selected slot3 wheel
```

No instruction in the bounded loop stores or pushes the `ECX` pointer value. The only push is the integer wheel index in `EDX`; the qword argument is loaded from `HDVehicle+0x98`.

## Leaf consumer

`SHIFT.Fun00752fa0WheelStateMachineProof/1` already classifies the callee. This P1D tranche independently pins its complete machine body only to prove that the register alias does not escape through the leaf:

```text
0x00752fa3  mov  eax,[ebp+0x8]
0x00752fa6  fld  qword [ebp+0xc]
0x00752fa9  fstp qword [ecx+0xa00]
0x00752faf  mov  dword [ecx+0x9f8],eax
0x00752fb6  ret  0xc
```

The leaf has zero direct calls, never reassigns `ECX`, and never stores or pushes the receiver pointer value. On selected slot3 its writes normalize to:

```text
HDVehicle+0x2d78  dword
HDVehicle+0x2d80  qword
```

Both are disjoint from the selected target `HDVehicle+0x28b8..+0x28bf`.

## Gate impact

This closes only the bounded four-wheel register alias:

```text
fun00765c40_four_wheel_register_alias_subset_complete = true
fun00765c40_selected_slot3_register_alias_reached = true
fun00765c40_selected_slot3_pointer_escape_found = false
fun00752fa0_selected_slot3_writer_found = false
```

It does **not** promote the global register/storage gate. Other `FUN_00765c40` interior wheel pointers, stack-local derived aliases, runtime-generated pointers, callbacks, indirect entry and callee-created aliases remain open. Consequently `machine_register_alias_storage_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D and aggregate P1.3 remain false; provider count remains 7.

Reproduce against the pinned retail executable:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00765c40_wheel_register_alias_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1d_slot3_fun00765c40_carrier_handoff.json \
  evidence/fun_00752fa0_wheel_state_machine_proof.json \
  --output out/p1d_slot3_fun00765c40_wheel_register_alias_closure.json
```

Next, bound the branch-equivalent `wheel+0x678` interior-pointer loops rooted at `0x00765cde` / `0x00765d67`. Those loops keep the pointer in a stack-local slot, read the child pointer at `wheel+0x420`, and advance by the same `0xa80` wheel stride.
