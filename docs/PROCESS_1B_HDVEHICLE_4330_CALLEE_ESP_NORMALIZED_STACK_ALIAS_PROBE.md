# Process 1B: HDVehicle+0x4330 callee ESP-normalized stack alias writer probe

## Blocker

The stack-alias probes cover fixed `[ebp+off]` / `[esp+off]` locals, but exact selected-slot addresses can survive stack-frame movement when `esp` is adjusted between spill and reload.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_esp_normalized_stack_alias_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For direct callees entered with an exact `0x00b83dc0` or `0x00b83ec0` value live in a GPR, it tracks:

- fixed EBP locals;
- ESP locals in a logical coordinate system normalized across immediate `sub esp, imm` / `add esp, imm`;
- spills and reloads through those logical stack slots;
- writes through the recovered exact alias.

The current bound remains straight-line and stops at branches, jumps, nested calls, returns, traps, or non-immediate ESP adjustments.

## Gate effect

No semantic gate is promoted. These remain fail-closed:

- `callee_stack_pointer_normalization_complete`;
- `nested_callee_alias_writer_provenance_complete`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact memory-derived indirect CALL target identity;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

LEA-based ESP changes, dynamic stack adjustments, CFG stack merges, nested calls, heap/object replacement, arbitrary runtime mutation and generated/self-modifying code remain open.

## Next

Run on authoritative `SHIFT.exe`; classify any recovered ESP-normalized writers. Extend only surviving LEA/dynamic-stack or nested-call alias classes reported by retail evidence.
