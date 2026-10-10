# Process 1A / P1.3A — `FUN_005ffc50` stack-local FNSTENV subset

## Scope

After the direct/raw, simple GPR, read-only/stack and call-next/pop closures, another classic x86 EIP-acquisition mechanism is an x87 environment save followed by reading the saved instruction-pointer field. This contract isolates the exact `FNSTENV` surface in retail PC 1.02 without treating every disassembler decode as proven executable code.

## Retail inventory

Across **2,847,850** decoded instructions, `objdump` reports exactly four `FNSTENV/FSTENV` instructions:

- `0x004177e4 fnstenv [edi+0x41]`;
- `0x0050d063 fnstenv [ebx-0x33333334]`;
- `0x00913763 fnstenv [esp]`;
- `0x00913a1b fnstenv [esp]`.

This pass closes only the two exact stack-local `[esp]` sequences. The non-stack decodes remain outside the claim.

Both stack-local sites have the same 24-byte machine sequence:

```text
sub esp,0x1c
fnstenv [esp]
and DWORD PTR [esp+0x4],0xbcff
or  DWORD PTR [esp+0x4],eax
fldenv [esp]
add esp,0x1c
```

Between `fnstenv` and `fldenv`, no saved environment field is loaded into a GPR. The only memory mutation is the mask/OR at `[esp+0x4]`, after which the environment is restored and the 28-byte temporary storage is immediately discarded. Thus these two sequences do not extract or reconstruct `FUN_005ffc50`.

## Gate effect

Promoted only `p13a_fun005ffc50_fnstenv_stack_restore_subset_complete=true`.

The two non-stack `FNSTENV` decodes, other PIC/inter-block forms, writable-memory/runtime callback slots, return-value provenance, encoded/runtime-generated pointers, global callback/incoming-indirect closure, slot0, slot1, stored aliases and aggregate P1.3 remain fail-closed. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_fnstenv_stack_restore.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_callnext_pic.json \
  --output evidence/p1a_p13a_fun005ffc50_fnstenv_stack_restore.json
pytest -q tests/test_process1a_p13a_fun005ffc50_fnstenv_stack_restore.py
```

## Next step

Trace writable-memory/runtime callback slots and inter-block/return-value entry to `FUN_005ffc50`. The two exact stack-local `FNSTENV` restore sequences no longer need to be treated as EIP-extraction candidates.
