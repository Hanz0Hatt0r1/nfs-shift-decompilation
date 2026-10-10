# Process 1D — `FUN_00765c40` `wheel+0x678` interior-alias closure

This tranche closes the two branch-equivalent interior-pointer loops near the start of `FUN_00765c40`. The exact `HDVehicle` identity is consumed from `SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1`; no new ownership claim is introduced.

Both branches start from the same wheel-relative interior address and advance by the canonical `0xa80` wheel stride:

```text
wheel 0: HDVehicle+0x0a78 = wheel+0x678
wheel 1: HDVehicle+0x14f8 = wheel+0x678
wheel 2: HDVehicle+0x1f78 = wheel+0x678
wheel 3: HDVehicle+0x29f8 = selected slot3 wheel+0x678
```

The pointer is persisted only in the function-local stack slot `[ebp-0xc]`. The exact store sites are `0x00765ce4`, `0x00765d5d`, `0x00765d6d`, and `0x00765ded`. No nonlocal or persistent store of this pointer exists in either byte-hash-locked window.

## Writes and child load

The loops write only:

```text
[interior-0x8] = wheel+0x670
[interior]     = wheel+0x678
```

For selected slot3 these normalize to `HDVehicle+0x29f0` and `HDVehicle+0x29f8`, both disjoint from the target `HDVehicle+0x28b8..+0x28bf`.

Each branch also loads:

```text
[interior-0x258] = [wheel+0x420]
```

because `0x678 - 0x258 = 0x420`. For selected slot3 the child-pointer field is therefore `HDVehicle+0x27a0`. The loaded child pointer is used only for three qword reads (`+0x0/+0x8/+0x10`) in the bounded windows; it is neither stored nor forwarded to a call.

## Transient `push ecx`

Branch B contains a raw pointer push:

```text
0x00765da4  push ecx       ; ECX = wheel+0x678
...
0x00765dc9  fstp dword [esp]
0x00765dcc  call FUN_00758ad0
```

This is not silently ignored. The pushed pointer is a transient stack scratch copy, and the same top stack word is overwritten by the scalar float argument at `0x00765dc9` before the call. The interior pointer therefore does not reach `FUN_00758ad0` as a stack argument.

Immediately before the scalar call both branches execute `ECX=ESI=HDVehicle`. The callee prefix is independently byte-hash locked. `FUN_00758ad0` reads only `[ebp+0x8]` before `0x00758adb lea ecx,[ebp+0x8]`, which overwrites incoming `ECX`. Thus the HDVehicle pointer is not consumed as an object receiver at this call boundary.

## Gate impact

This bounded surface establishes:

```text
fun00765c40_wheel_678_interior_alias_subset_complete = true
fun00765c40_selected_slot3_interior_persistent_escape_found = false
fun00765c40_selected_slot3_child_pointer_forward_found = false
fun00765c40_transient_stack_pointer_copy_found = true
fun00765c40_transient_stack_pointer_copy_reaches_callee = false
fun00758ad0_consumes_hdvehicle_receiver = false
```

The global register/storage gate remains false. Other `FUN_00765c40` derived pointers after `0x00765df2`, runtime/generated pointers, callbacks, indirect entry and callee-created aliases remain open. Slot3 writer provenance, P1.3D and aggregate P1.3 also remain false; provider count remains 7.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00765c40_wheel_interior_alias_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1d_slot3_fun00765c40_carrier_handoff.json \
  --output out/p1d_slot3_fun00765c40_wheel_interior_alias_closure.json
```

Next, inventory the remaining `FUN_00765c40` `LEA`-derived pointer families after `0x00765df2` and classify them as wheel-relative, HDVehicle-local, BODY-child, stack-only, or callee-facing before attempting any carrier-level register/storage composition.
