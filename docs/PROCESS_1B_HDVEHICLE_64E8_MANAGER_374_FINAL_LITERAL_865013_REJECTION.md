# Process 1B: final literal `manager+0x374` site rejection

## Scope

This slice closes the final literal `[base+0x374]` receiver candidate left after the merged manager+0x374 inventory/rejection contracts: `0x00865013` in `FUN_00864c10`.

## Machine proof

`FUN_00864c10` captures its first stack argument as the target receiver:

```text
0x00864c67  mov esi,[ebx+0x8]
```

Before the later `0x00865013 fstp dword [esi+0x374]`, the same receiver is used for a virtual dispatch:

```text
0x00864c87  mov eax,[esi]
0x00864c89  mov eax,[eax+0x20]
0x00864c8c  lea edx,[ebp-0x220]
0x00864c92  mov ecx,esi
0x00864c94  call eax
```

There is no stack argument pushed for this dispatch.

The exact Participants Manager root vptr is `0x00ab9190`. Its slot `+0x20` is cell `0x00ab91b0`, resolving to `FUN_006383c0`:

```text
0x006383c0  push ebp
0x006383c1  mov ebp,esp
0x006383c3  mov ecx,[ebp+0x8]
0x006383c6  call 0x00641700
0x006383cc  ret 4
```

That target requires one stack argument and consumes it with `ret 4`. The callsite at `0x00864c94` supplies no stack argument and instead passes a buffer through EDX. Therefore the receiver at `0x00864c94` cannot be the Participants Manager root; otherwise exact vtable dispatch would be ABI-incompatible with the executed callsite.

The same ESI remains the base of `0x00865013`, so that store cannot be `manager+0x374`.

## Result

The exhaustive literal `[base+0x374]` receiver worklist is now closed: zero literal sites remain capable of writing the Participants Manager `+0x374` slot.

This does **not** close computed-address forms that may reach the same field, and it does not yet reject the final `0x004b86cf` HDVehicle+0x64e8 candidate. Provider count remains 7 and P1.3 remains fail-closed.
