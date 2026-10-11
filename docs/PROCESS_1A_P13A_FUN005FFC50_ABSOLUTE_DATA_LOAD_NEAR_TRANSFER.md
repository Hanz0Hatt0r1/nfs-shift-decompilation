# Process 1A / P1.3A — absolute `.data` load to near register transfer

## Scope

The direct-absolute writable composition closes instructions that transfer through an absolute `.data` slot directly. A distinct shape first loads the **contents** of an absolute writable slot into a GPR and later transfers through that same register.

This contract scans `mov <32-bit GPR>, ds:<absolute .data memory>` and follows only that loaded register for the next 16 decoded instructions. The window stops at any other call/jump, conditional branch/loop/return/trap, or a write/clobber of the loaded register or its subregister.

## Corrected load inventory

Across **2,847,850** decoded instructions there are **1,786** actual absolute `.data` memory-content loads from **434** unique slots:

- `EAX`: 1,125;
- `ECX`: 326;
- `EDX`: 186;
- `ESI`: 51;
- `EDI`: 72;
- `EBX`: 25;
- `EBP`: 1.

Encoding forms are 1,125 accumulator/moffs loads and 661 ModRM absolute loads.

A broader preliminary lexical count also included instructions that load a `.data` **address as an immediate**. Those are not memory-content loads and are deliberately excluded here.

## Retail result

Within the 16-instruction same-register near-use subset:

- exact `call reg` / `jmp reg` after the absolute `.data` load: **0**;
- windows ending at another control transfer: 1,355;
- windows ending at a register clobber: 413;
- windows reaching the 16-instruction limit: 18.

Synthetic tests prove a positive `mov eax,ds:<slot>; ...; call eax` is detected and an intervening `xor ecx,ecx` terminates provenance.

## Gate effect

Promoted only `p13a_fun005ffc50_absolute_data_load_near_register_transfer_subset_complete=true`.

This does not close register copies, spill/reload, arithmetic transforms, inter-block carry, base/index-addressed writable memory, alias writes, heap/runtime-generated pointers, or global writable-memory entry. All global callback/P1.3 gates remain fail-closed and provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_absolute_data_load_near_transfer.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_direct_absolute_writable_slots.json \
  --output evidence/p1a_p13a_fun005ffc50_absolute_data_load_near_transfer.json
pytest -q tests/test_process1a_p13a_fun005ffc50_absolute_data_load_near_transfer.py
```

## Next step

Trace copied/transformed/inter-block values loaded from writable memory, then base/index-addressed and alias sources. The direct absolute `.data` load → same-register near-transfer subset no longer needs to be rescanned.
