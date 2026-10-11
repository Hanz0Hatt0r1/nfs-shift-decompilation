# Process 1B: HDVehicle+0x4330 callee LEA ESP-normalized stack alias probe

## Blocker

The immediate `add/sub esp, imm` layer still leaves one concrete stack-address normalization class open: compilers can adjust the stack with `lea esp,[esp+/-imm]`. A selected-slot address spilled into an ESP-relative local can therefore survive while its physical displacement changes.

## Probe

`tools/ghidra/analyze_p1b_hdvehicle_4330_callee_lea_esp_normalized_stack_alias_writers.py` is SHA-locked to authoritative PC retail 1.02 `SHIFT.exe`.

For direct callees entered with exact `0x00b83dc0` / `0x00b83ec0` values in GPRs it tracks:

- fixed EBP/ESP stack aliases;
- immediate `add/sub esp, imm` normalization;
- exact `lea esp,[esp+/-imm]` normalization;
- reloads from the same logical stack local after normalization;
- writes through the recovered exact register alias.

Unsupported dynamic ESP changes terminate the bounded path rather than guessing.

## Gate effect

No semantic gate is promoted. The following remain fail-closed:

- `callee_stack_pointer_normalization_complete`;
- `nested_callee_alias_writer_provenance_complete`;
- `interprocedural_alias_writer_provenance_complete`;
- `runtime_or_alias_writer_provenance_complete`;
- exact memory-derived indirect-call target identity;
- global `indirect_entry_into_carriers`;
- aggregate P1.3.

Provider count remains 7.

## Limits

Register-sized or masked ESP changes, CFG stack merges, nested calls, heap/object replacement, arbitrary runtime mutation and generated/self-modifying code remain open.

## Next

Run on authoritative retail `SHIFT.exe`; classify recovered LEA-normalized writers. If no writer survives, extend only concrete dynamic-stack or nested-call aliases reported by retail evidence.
