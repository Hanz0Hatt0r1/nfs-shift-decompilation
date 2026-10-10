# Process 1D — `FUN_00760b50` selected-wheel register-alias closure

This tranche follows the remaining register-only alias frontier after the merged bounded register-alias subset. It consumes both `SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1` for selected-object identity and `SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1` for the already-closed `FUN_00758b50` / `FUN_00755950` / `FUN_00755f80` paths; it does not re-own those proofs.

For PC retail 1.02, the merged upstream contract proves that the call at `0x00771180` enters `FUN_00760b50` with:

```text
ECX = HDVehicle+0x2380 = selected slot3 wheel
```

The exact machine body at `0x00760b50` captures that receiver once:

```text
0x00760b69  push esi       ; saves the caller's ESI before capture
0x00760b6a  mov  esi,ecx   ; ESI = exact selected wheel
```

The complete `ESI`-use inventory contains 35 instructions. Excluding the pre-capture save, the capture itself and the epilogue restore, all 32 uses are memory accesses based on `[esi+offset]`. There is no post-capture `push esi`, no copy of the exact root into another argument/value register, no store of the pointer value to nonlocal memory, and no explicit direct-callee forward of the exact wheel root.

One callee-facing pointer is derived from the selected wheel:

```text
0x00760d02  mov ecx,DWORD PTR [esi+0x420]
...
0x00760d4b  call 0x007ba860
```

This is a dereference of `wheel+0x420`, producing the already-recorded child receiver. It is not the exact selected-wheel root and is therefore kept separate from the wheel-root escape question.

The direct-call surface remains exactly four calls: `FUN_007af0a0`, `FUN_00749340`, `FUN_00900b10`, and child consumer `FUN_007ba860`.

## Gate impact

This closes only the explicit register/storage escape surface of the `ESI` alias inside `FUN_00760b50`:

```text
fun00760b50_exact_selected_wheel_register_alias_subset_complete = true
fun00760b50_exact_selected_wheel_explicit_register_escape_found = false
```

The global register-alias/storage gate stays false because other selected-wheel carriers have not been exhausted. Callee-created aliases, aggregate stores, callbacks and indirect carriers also remain open. Slot3 writer provenance, P1.3D and aggregate P1.3 remain false; external provider count remains 7.

Reproduce against the exact retail executable:

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00760b50_register_alias_pe.py \
  /path/to/SHIFT.exe \
  evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json \
  evidence/p1d_slot3_register_alias_subset_closure.json \
  --output out/p1d_slot3_fun00760b50_register_alias_closure.json
```

Next, continue outside the now-closed `FUN_00758b50` / `FUN_00755950` / `FUN_00755f80` / `FUN_00760b50` register paths: bound only the non-duplicated residual register surface of `FUN_00755a60`, then inspect callee-created selected-wheel aliases. Existing `FUN_00766510` / `FUN_00758fc0` ownership stays with its current P1D tranche.
