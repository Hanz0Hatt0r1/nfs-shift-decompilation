# Process 1B — local analysis of `0x004b86cf`

## Scope

This closes only the instruction-local behavior of the remaining literal
`HDVehicle+0x64e8` candidate. It does not prove that every runtime value of
`manager+0x374` is or is not `HDVehicle+0x4330`.

Authority is PC retail 1.02, PE32 x86, image base `0x00400000`, executable
SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
The analyzed Ghidra program is `SHIFT.exe`, MD5
`705af8b420e5eb1e3834ac43d5533c6b`, language `x86:LE:32:default`.

## Complete containing function

Ghidra's pinned retail listing identifies `FUN_004b8660` as a 149-byte
`__stdcall` function with one stack argument, `char param_1`; its epilogue is
`RET 0x4`. The complete decoded instruction body is:

```asm
004b8660: 55                    PUSH EBP
004b8661: 8b ec                 MOV EBP,ESP
004b8663: 56                    PUSH ESI
004b8664: e8 67 14 fd ff        CALL 0x00489ad0
004b8669: 8b b0 74 03 00 00     MOV ESI,dword ptr [EAX + 0x374]
004b866f: 85 f6                 TEST ESI,ESI
004b8671: 74 7d                 JZ 0x004b86f0
004b8673: 53                    PUSH EBX
004b8674: bb 01 00 00 00        MOV EBX,0x1
004b8679: 39 9e b8 21 00 00     CMP dword ptr [ESI + 0x21b8],EBX
004b867f: 74 6e                 JZ 0x004b86ef
004b8681: e8 2a b9 fd ff        CALL 0x00493fb0
004b8686: d9 80 e4 0d 00 00     FLD float ptr [EAX + 0xde4]
004b868c: d9 9e d0 21 00 00     FSTP float ptr [ESI + 0x21d0]
004b8692: 84 1d 30 d0 bb 00     TEST byte ptr [0x00bbd030],BL
004b8698: 75 1d                 JNZ 0x004b86b7
004b869a: 09 1d 30 d0 bb 00     OR dword ptr [0x00bbd030],EBX
004b86a0: b9 00 c6 bb 00        MOV ECX,0x00bbc600
004b86a5: e8 e6 7d f5 ff        CALL 0x00410490
004b86aa: 68 60 ae a9 00        PUSH 0x00a9ae60
004b86af: e8 ff 88 44 00        CALL 0x00900fb3
004b86b4: 83 c4 04              ADD ESP,0x4
004b86b7: 83 3d 10 c6 bb 00 0a  CMP dword ptr [0x00bbc610],0xa
004b86be: 7d 06                 JGE 0x004b86c6
004b86c0: 80 7d 08 00           CMP byte ptr [EBP + 0x8],0x0
004b86c4: 74 0f                 JZ 0x004b86d5
004b86c6: 83 be b8 21 00 00 03  CMP dword ptr [ESI + 0x21b8],0x3
004b86cd: 74 06                 JZ 0x004b86d5
004b86cf: 89 9e b8 21 00 00     MOV dword ptr [ESI + 0x21b8],EBX
004b86d5: 8b b6 00 01 00 00     MOV ESI,dword ptr [ESI + 0x100]
004b86db: e8 d0 b8 fd ff        CALL 0x00493fb0
004b86e0: 53                    PUSH EBX
004b86e1: 6a 00                 PUSH 0x0
004b86e3: 56                    PUSH ESI
004b86e4: 8d 88 40 05 00 00     LEA ECX,[EAX + 0x540]
004b86ea: e8 d1 3c 00 00        CALL 0x004bc3c0
004b86ef: 5b                    POP EBX
004b86f0: 5e                    POP ESI
004b86f1: 5d                    POP EBP
004b86f2: c2 04 00              RET 0x4
```

## Instruction-local behavior

`ESI` is loaded from `FUN_00489ad0()`'s singleton field `+0x374`. A null
pointer returns without reaching the candidate store. If the pointed object's
`+0x21b8` value is already `1`, the function also returns before the store.
Otherwise the function copies a float from the object returned by
`FUN_00493fb0()` into `[ESI+0x21d0]`, then reaches the state update only when
`DAT_00bbc610 >= 10` or `param_1 != 0`. The update is skipped if
`[ESI+0x21b8] == 3`; otherwise `0x004b86cf` writes the constant `1`.

Therefore this instruction mutates a field of the object currently referenced
by `manager+0x374`; it does not change that singleton pointer or select an
object. The state-field label/gameplay meaning is not established here.

## Receiver identity and gate effect

The only proven nonzero exact-manager writer stores a selected allocator-owned
`manager+0x2a0` collection entry in `manager+0x374` after a successful
transition and entry-state check. That population path is disjoint from the
fixed global `HDVehicle+0x4330` subobject. Thus, **on that proven assignment
path**, this function's write is to the collection entry and cannot be the
`HDVehicle+0x64e8` write.

Other independent root-origin, helper-returned, escaped-alias and
non-vtable-setter paths remain open. The local analysis therefore does not
close the global pointer identity question. Keep these gates fail-closed:

```text
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
external_provider_count = 7
```

## Next

Reduce the remaining independent/unknown manager-root origin and helper-setter
classes. Revisit the global `manager+0x374 -> HDVehicle+0x4330` identity only
after those sources are bounded; do not infer identity from equal offsets.
