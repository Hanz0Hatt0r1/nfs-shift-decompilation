# Process 1A / P1.3A — base/index-addressed writable `.data` near-transfer subset

## Result

This subset extends the `FUN_005ffc50` writable-memory provenance frontier beyond direct absolute loads. The PC retail 1.02 disassembly contains **63** `MOV r32,[base/index expression]` loads whose effective addresses can be resolved exactly, before the load, into writable `.data` (`0x00b81000..0x00bbc600`). They resolve to **51 unique effective addresses**.

Destination-register distribution is: EAX 37, ECX 10, EDX 5, ESI 5, EBX 4, EDI 2. A bounded 16-decoded-instruction same-register follow finds **0 indirect CALL/JMP transfers**. The 63 paths terminate as 58 other control transfers and 5 destination-register clobbers.

Examples from the recovered inventory include `0x0041b842 ecx,[esi*4+0xb81618]`, `0x00553240 eax,[esi] -> 0x00b83dc0`, `0x00553997 esi,[edi-0xc] -> 0x00b83ec4`, `0x008addc4 ecx,[eax] -> 0x00b94a10`, and `0x00a61ab3 eax,[esi+0x4] -> 0x00bbbd10`.

## Boundaries

The analysis uses straight-line exact GPR constant propagation solely to evaluate effective addresses. Unknown base/index values are excluded rather than guessed. After a qualifying load, only the original destination register is followed; copies, arithmetic/LEA transforms, stack spill/reload, and inter-block propagation are deliberately not promoted here.

Therefore only `p13a_fun005ffc50_base_indexed_data_same_register_near_transfer_subset_complete` becomes true. All aggregate writable-source, callback-entry, slot0/slot1 and P1.3-complete gates remain false. External provider count remains 7.

## Reproduction

Run:

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_near_transfer.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_absolute_data_esp_normalization.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_near_transfer.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_near_transfer.py
```

The analyzer asserts the PC retail 1.02 SHA-256, upstream contract, 2,847,850 decoded instructions, the exact 63/51 inventory, register distribution, zero same-register indirect transfers, and 58/5 termination split.

## Next

Propagate the 63 base/index-addressed loads through GPR copies/transforms, then stack and bounded inter-block carriers. Those gates remain fail-closed until separately proven.
