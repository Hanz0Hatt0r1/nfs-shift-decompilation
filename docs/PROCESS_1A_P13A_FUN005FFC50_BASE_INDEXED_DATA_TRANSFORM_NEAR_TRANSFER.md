# Process 1A / P1.3A — base/index writable `.data` copy/transform near-transfer subset

## Result

Starting from the verified 63 exact base/index-addressed writable `.data` loads (51 effective addresses), this subset follows same-window GPR copies and selected dependency-preserving transforms for 16 decoded instructions.

Retail PC 1.02 contains exactly **1 GPR copy event** from one load and **4 transform events** from three loads across four unique transform sites. Transform mix: `imul` 1, `add` 1, `sar` 1, `and` 1. No tainted or transformed register reaches an indirect `call`/`jmp`.

The concrete events are:

- load `0x008113a0` -> copy at `0x008113a9` (`mov ecx,edi`);
- load `0x00553997` -> `imul esi,esi,0x2c` at `0x0055399d`, then `add esi,0xbbeb78` at `0x005539a6`;
- load `0x0098952b` -> `sar ebx,1` at `0x0098952d`;
- load `0x009f71a8` -> `and eax,0xff` at `0x009f71af`.

Termination inventory is 59 other control transfers and 4 cases where all tainted GPRs are clobbered.

## Boundary

Promoted only `p13a_fun005ffc50_base_indexed_data_copy_transform_near_transfer_subset_complete=true`. Stack spill/reload, memory aliases, inter-block/phi carry, aggregate writable-source/callback/slot0/slot1/P1.3 gates remain fail-closed. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_transform_near_transfer.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_base_indexed_data_near_transfer.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_transform_near_transfer.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_transform_near_transfer.py
```

## Next

Trace stack spill/reload and bounded inter-block carry for the remaining base/index-derived writable-memory provenance.
