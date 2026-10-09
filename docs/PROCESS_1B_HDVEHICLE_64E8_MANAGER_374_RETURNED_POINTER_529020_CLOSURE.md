# Process 1B: returned computed `+0x374` pointer closure

`FUN_00529020` is the sole computed-address materializer that returns its `base+0x374` pointer. The retail whole-image control-transfer scan finds one direct transfer to the function (`0x0051f051`), no direct jumps, and no absolute pointer-cell occurrence of `0x00529020` anywhere in the PE.

The only caller immediately dereferences the returned pointer once:

```text
0x0051f051  call FUN_00529020
0x0051f056  mov eax,[eax]
0x0051f058  mov ecx,[esi+0x384]
0x0051f05e  mov [esi+0x390],eax
```

The pointer itself is never written through, stored, forwarded or returned again. Therefore receiver identity does not need to be guessed: even if the producer returned some `base+0x374`, this complete consumer surface only reads the pointee value.

After the previously merged direct-write rejection, this closes the returned-pointer class and leaves exactly 17 callee-forwarding computed-address paths. `manager+0x374 == HDVehicle+0x4330`, `0x004b86cf`, P1.3 and provider removal remain fail-closed; provider count remains 7.
