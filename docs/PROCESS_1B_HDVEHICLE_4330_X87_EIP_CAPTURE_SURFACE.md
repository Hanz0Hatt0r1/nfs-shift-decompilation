# Process 1B — HDVehicle+0x4330 x87 EIP-capture surface

This P1.3B slice follows the canonical call/pop closure by checking the classic x87 `FSTENV/FNSTENV` address-acquisition family.

`objdump -d -M intel` yields four apparent environment-save sites. Each is adjudicated against retail bytes and Ghidra function ownership rather than accepted from linear decoding alone.

## `0x004177e4`

This is inline switch-table data, not an instruction. `FUN_004175b9` dispatches at `0x004175d0` through `JMP DWORD PTR [ECX*4+0x004177e4]`. The 11 dwords beginning at `0x004177e4` are branch targets inside the same function. Ghidra has no function owning the apparent `FNSTENV` decode.

## `0x0050d063`

This is an unowned decode inside `INT3` padding between `thunk_FUN_004eb550` (`0x0050d030..34`) and `thunk_FUN_0040cc70` (`0x0050d070..74`). There is no direct decoded control-flow target to `0x0050d063`.

## Real x87 environment saves

The remaining two sites are real instructions:

- `0x00913763` in `FUN_00913576`;
- `0x00913a1b` in `FUN_0091382e`.

Both have the same bounded machine sequence:

```text
sub esp,0x1c
fnstenv [esp]
and dword [esp+4],0xbcff
or  dword [esp+4],eax
fldenv [esp]
add esp,0x1c
...
ret
```

The saved environment is modified/reloaded in place. No saved instruction-pointer field is loaded into a GPR or otherwise extracted for address construction.

## Result

Decoded `FSTENV/FNSTENV` surface: 4 sites → 2 non-instruction false decodes + 2 real save/modify/reload sites → **0 saved-EIP extractions**.

This closes the x87 environment-based EIP-capture subset only. Other noncanonical address synthesis, runtime copies, transformed constants and encoded pointers remain open, so indirect-entry/global manager/P1.3/provider gates remain fail-closed and provider count remains 7.
