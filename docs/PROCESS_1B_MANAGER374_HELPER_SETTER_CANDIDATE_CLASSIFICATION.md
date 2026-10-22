# Process 1B — classify the retail helper-setter candidate

## Scope

This report classifies the single positive write-through candidate in the
bounded `manager+0x374` direct-helper argument probe. It does not close the
global manager-root or helper-setter surfaces.

Authority is PC retail 1.02, PE32 x86, image base `0x00400000`, executable
SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
The pinned Ghidra program has MD5
`705af8b420e5eb1e3834ac43d5533c6b` and language `x86:LE:32:default`.

## Candidate classification

Both the raw retail probe and Ghidra probe identify the same write-through:

```text
materializer: 0x0070fb45  LEA ECX,[ESI+0x374]
callsite:     0x0070fb4f  CALL 0x00533e70
write:        0x00533e72  MOV DWORD PTR [EAX],0
```

The call is inside `FUN_0070fae0`, a 896-byte `__fastcall` constructor. Its
entry receiver is copied from `ECX` to `ESI`. The constructor writes vptr
`0x00b04524` to `[ESI]`. Nearby `.rdata` contains the class string
`Physics Manager` at `0x00b04580`; the constructor passes that string in
`EDX` to `FUN_00647820` during initialization. The exact retail
bytes and complete function body are recorded in
`evidence/p1b_manager374_helper_setter_ghidra_20261022/candidate_retail_disassembly.txt`.

`FUN_00533e70` is a three-instruction helper:

```asm
00533e70: 8b c1                 mov eax,ecx
00533e72: c7 00 00 00 00 00     mov DWORD PTR [eax],0x0
00533e78: c3                    ret
```

At the candidate callsite, `ECX` is the address of the Physics Manager
instance's own field at `+0x374`. The helper stores zero in that field. It
does not load or store the Participants Manager root `0x00bc9fc0`, and it
does not write through the pointer held in Participants Manager `+0x374`.
Equal numeric offsets do not establish object identity.

The compact Ghidra evidence for both complete functions is
`evidence/p1b_manager374_helper_setter_ghidra_20261022/candidate_functions.json`.
The merged candidate frontier remains available in the adjacent Ghidra and
retail JSON reports.

## Ghidra and retail instruction-boundary cross-check

The compact Ghidra stream contains 2,204,481 instructions; retail `objdump`
decodes 2,847,884. The bounded helper-return probe reports 669 raw-retail
direct-call targets that are not instruction starts in that raw stream,
while the Ghidra listing reports one. These counts are acquisition frontiers
from different instruction listings and are not interchangeable.

The new boundary audit compares direct CALL start addresses and targets. It
found 182,626 exact Ghidra/retail CALL matches and 39 Ghidra CALL rows without
the same retail `objdump` CALL boundary. It does not filter either stream or
infer that every mismatch is invalid control flow.

The one unresolved Ghidra helper-return target is `0x00460041 ->
0xe9427dcf`. At `0x0046003f`, retail bytes `8d 55 e8` form
`LEA EDX,[EBP-0x18]`; therefore `0x00460041` lies inside that instruction in
the retail linear decode. Retail next decodes the actual CALL at
`0x00460045 -> 0x004f5eb0`. This is evidence of an overlapping decode. An
alternate control-flow entry into `0x00460041` has not been ruled out here,
so this boundary remains open pending incoming-flow classification.

Machine-readable audit:
`evidence/p1b_manager374_ghidra_retail_call_boundary_audit_20261022.json`.
The audit tool is
`tools/ghidra/audit_p1b_ghidra_retail_call_boundaries.py`.

## Gate state and limits

This classifies only the positive direct-helper candidate above. It does not
close unresolved direct targets, returned-target persistence, indirect
helpers, unrelated opaque root synthesis, external/runtime memory origins,
or generated code. Keep these gates fail-closed:

```text
materialized_helper_mediated_setter_surface_complete = false
global_helper_non_vtable_indirect_setter_surface_complete = false
external_or_unknown_origin_outer_alias_surface_complete = false
global_manager_root_origin_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
external_provider_count = 7
```

## Reproduction

```bash
python3 tools/ghidra/run_p1b_manager374_helper_setter_retail_frontier.py \
  /path/to/SHIFT.exe --out-dir /tmp/p1b-helper-setter-retail

python3 tools/ghidra/audit_p1b_ghidra_retail_call_boundaries.py \
  /path/to/SHIFT.exe /path/to/compact_instruction_stream.jsonl.gz \
  --json-out /tmp/p1b-ghidra-retail-call-boundaries.json

python3 -m pytest -q \
  tests/test_process1b_manager374_ghidra_helper_setter_acquisition.py
```

The focused acquisition tests pass: **8 passed**. No runtime source changed,
so this evidence/tooling update does not rebuild the game runtime.
