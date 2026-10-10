# Process 1A / P1.3A — `FUN_005ffc50` call-next/pop PIC subset

## Scope

The preceding P1.3A contracts close direct/raw pointers, simple straight-line GPR reconstruction, read-only image-backed dwords, and explicit stack locals. One classic x86 PIC construction remains distinct: `call` to the immediately following instruction, then `pop reg` to capture the return address and arithmetically derive another address.

## Retail result

Across **2,847,850** decoded instructions there is exactly **one** direct call-to-next-instruction site:

```text
0x00d31404  call 0x00d31409
0x00d31409  pop ebp
0x00d3140a  sub ebp,0x409
...
0x00d3141a  mov ebx,ebp
0x00d31420  je 0x00d3142b
```

Before the first conditional branch the captured return address deterministically becomes `0x00d31000`, the `.secu` base used by this helper. It does **not** become `FUN_005ffc50` (`0x005ffc50`). The `0x00d31400..0x00d31422` bytes are SHA-locked in evidence.

## Gate effect

Promoted only `p13a_fun005ffc50_call_next_pop_pic_subset_complete=true`.

This does not close other position-independent techniques. In particular FPU-environment EIP acquisition, inter-block reconstruction, writable-memory/runtime callback slots, return-value provenance and encoded/runtime-generated pointers remain fail-closed. Global callback/incoming-indirect, slot0, slot1, stored-alias, runtime selected-wheel-store-negative and aggregate P1.3 gates remain false. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_callnext_pic.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_static_memory_stack_reconstruction.json \
  --output evidence/p1a_p13a_fun005ffc50_callnext_pic.json
pytest -q tests/test_process1a_p13a_fun005ffc50_callnext_pic.py
```

## Next step

Trace writable-memory/runtime callback slots and the remaining FPU/inter-block entry classes. The call-next/pop PIC family no longer needs to be rescanned.
