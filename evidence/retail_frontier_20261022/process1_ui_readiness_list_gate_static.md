# Original-PE UI readiness list gate: static follow-up

Date: 2026-10-22. This is a static analysis of the original SHIFT PC retail
1.02 PE32 x86, not a new replay and not a P-code or renderer change.

## Binary and bounded runtime evidence

- Original PE SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- The original PE at `/home/pes/ghidra_projects/SHIFT-retail-analysis.exe`
  was hash-checked before disassembly. The instructions below are from its
  `.text` section.
- Existing v789/v790 evidence observes nine list items under owner
  `O=0x27DFA5FC`; v790 observes a query of item `I=0x27DFAD78` returning 5.
  See [v789/v790](process1_ui_list_callback_trace_v789_v790.md).
- Existing v795 evidence separately traces the same item address through
  `0x00508C70`, returning 5.
  See [v795](process1_status_chain_v795.md).
- Existing v796 evidence observes `O=0x27DFA5FC`, a zero readiness byte at
  `O+0x2D`, and `0x005092F0` as its last recorded writer. These are separate
  bounded runs; the records do not prove the same item status was present in
  every v796 call.
  See [v796](process1_owner_readiness_v796.md).
- The referenced runs used the original PE inside the Linux P-code runtime.
  Their host-frame completion and dispatch totals do not prove a visible menu,
  race entry, or retail rendering.

## Original-byte gate in `0x005093A0`

The original code reaches its item loop only on the `0x0050950D` path. For each
list item, it reads the item's `+0xE4` state. State 5 dispatches the item's
vtable slot `+0x10` through `0x005088C0`:

~~~asm
0050950d: 83 f8 01             cmp    eax,0x1
00509510: 0f 85 94 01 00 00    jne    0x5096aa
00509516: 8d 73 08             lea    esi,[ebx+0x8]
0050951e: c7 45 f8 00 00 00 00 mov    DWORD PTR [ebp-0x8],0x0
00509525: 88 45 ff             mov    BYTE PTR [ebp-0x1],al
00509528: 88 45 fd             mov    BYTE PTR [ebp-0x3],al
0050952b: c6 45 fe 00          mov    BYTE PTR [ebp-0x2],0x0
0050952f: c6 45 fc 00          mov    BYTE PTR [ebp-0x4],0x0
00509533: e8 48 46 17 00       call   0x67db80
00509538: 8b 38                mov    edi,DWORD PTR [eax]
0050953a: 8d 55 f4             lea    edx,[ebp-0xc]
0050953d: 8b ce                mov    ecx,esi
0050953f: e8 6c c9 fe ff       call   0x4f5eb0
00509544: 3b 38                cmp    edi,DWORD PTR [eax]
00509546: 0f 95 c0             setne  al
00509549: 84 c0                test   al,al
0050954b: 0f 84 43 01 00 00    je     0x509694
00509551: e8 1a 23 f0 ff       call   0x40b870
00509556: 8b 10                mov    edx,DWORD PTR [eax]
00509558: 8b c8                mov    ecx,eax
0050955a: 8b 42 48             mov    eax,DWORD PTR [edx+0x48]
0050955d: ff d0                call   eax
0050955f: 83 f8 01             cmp    eax,0x1
00509562: 0f 84 42 01 00 00    je     0x5096aa
00509568: 8b 77 0c             mov    esi,DWORD PTR [edi+0xc]
0050956b: 8b 86 e4 00 00 00    mov    eax,DWORD PTR [esi+0xe4]
00509571: 83 f8 07             cmp    eax,0x7
00509574: 77 12                ja     0x509588
00509576: ff 24 85 d8 96 50 00 jmp    DWORD PTR [eax*4+0x5096d8]
0050957d: 8b ce                mov    ecx,esi
0050957f: e8 3c f3 ff ff       call   0x5088c0
00509584: c6 45 fd 00          mov    BYTE PTR [ebp-0x3],0x0
00509588: c6 45 ff 00          mov    BYTE PTR [ebp-0x1],0x0
0050958c: 8b 47 04             mov    eax,DWORD PTR [edi+0x4]
0050958f: 85 c0                test   eax,eax
00509591: 74 02                je     0x509595
00509593: 8b f8                mov    edi,eax
00509595: 8d 55 f4             lea    edx,[ebp-0xc]
00509598: 8d 4b 08             lea    ecx,[ebx+0x8]
0050959b: e8 10 c9 fe ff       call   0x4f5eb0
005095a0: 3b 38                cmp    edi,DWORD PTR [eax]
005095a2: 75 ad                jne    0x509551
005095a4: 80 7d fd 00          cmp    BYTE PTR [ebp-0x3],0x0
005095a8: 0f 84 e0 00 00 00    je     0x50968e
005095ae: 8b 4d f8             mov    ecx,DWORD PTR [ebp-0x8]
005095b1: 85 c9                test   ecx,ecx
005095b3: 0f 84 d5 00 00 00    je     0x50968e
005095b9: 80 7d fe 00          cmp    BYTE PTR [ebp-0x2],0x0
005095bd: 0f 85 cb 00 00 00    jne    0x50968e
005095c3: 80 7d fc 00          cmp    BYTE PTR [ebp-0x4],0x0
005095c7: 0f 85 c1 00 00 00    jne    0x50968e
005095cd: e9 fa 33 f2 ff       jmp    0x42c9cc
0042c9cc: 80 bb ad 00 00 00 00 cmp    BYTE PTR [ebx+0xad],0x0
0042c9d3: e9 fc cb 0d 00       jmp    0x5095d4
005095d4: 0f 84 af 00 00 00    je     0x509689
005095da: 8b 13                mov    edx,DWORD PTR [ebx]
005095dc: 8b 42 14             mov    eax,DWORD PTR [edx+0x14]
005095df: 8b cb                mov    ecx,ebx
005095e1: c6 43 2d 01          mov    BYTE PTR [ebx+0x2d],0x1
005095e5: ff d0                call   eax
0050968e: 80 7d ff 00          cmp    BYTE PTR [ebp-0x1],0x0
00509692: 74 16                je     0x5096aa
00509694: 80 bb ad 00 00 00 00 cmp    BYTE PTR [ebx+0xad],0x0
0050969b: c6 43 2d 01          mov    BYTE PTR [ebx+0x2d],0x1
0050969f: 74 09                je     0x5096aa
005096a1: 8b 13                mov    edx,DWORD PTR [ebx]
005096a3: 8b 42 14             mov    eax,DWORD PTR [edx+0x14]
005096a6: 8b cb                mov    ecx,ebx
005096a8: ff d0                call   eax
005096aa: 5f                   pop    edi
005096ab: 5e                   pop    esi
005096ac: 33 c0                xor    eax,eax
005096ae: 5b                   pop    ebx
005096af: 8b e5                mov    esp,ebp
005096b1: 5d                   pop    ebp
005096b2: c3                   ret
~~~

The incoming `EAX==1` condition at `0x00509510` means `AL=1` when the loop
locals are initialized at `0x00509525`. The comparison at `0x00509544` then
tests whether the list head equals its sentinel. Each executed item iteration
clears `BYTE [EBP-1]` at `0x00509588`. On the ordinary fallthrough path,
`0x00509692` skips the readiness store when that byte is zero, so this
particular store at `0x0050969B` requires the list loop not to execute.

There is a separate direct store path. If the per-item conditions at
`0x005095A4–0x005095C7` all pass, the function jumps to `0x0042C9CC`; that
block tests owner byte `+0xAD` and jumps to `0x005095D4`. When `+0xAD` is
nonzero, `0x005095D4` falls through to another `BYTE[owner+0x2D]=1` store at
`0x005095E1`. When `+0xAD` is zero, it branches to the ordinary final check.
Thus list emptiness is required for the ordinary store but is not a global
precondition for every store in this function.

For item state 5, the loop calls `0x005088C0` at `0x0050957F` and clears the
separate local byte `BYTE[EBP-3]` at `0x00509584`. After the loop,
`0x005095A8` branches directly to the final check, bypassing the alternate
`0x0042C9CC` store path. Because the iteration also cleared `BYTE[EBP-1]`,
this state-5 route skips the ordinary store as well. The static wrapper
`0x005088C0` calls the item's virtual slot `+0x10` and stores its return in
item `+0xE4`; the call target and its effect are not determined by these
bytes.

The initial gate and the distinct state-3 callback path are part of the same
function, but this report does not infer their runtime outcomes from the
bounded runs. Other `+0x2D` operands found in the decompilation export belong
to other functions and have not been identified as writes to this owner.

## Conclusion and next evidence

The original bytes expose two candidate ways this function can set the
readiness byte and show how an item in state 5 bypasses both stores for that
call. This is consistent with v796's zero readiness byte and v789's nine-item
list; v790/v795 separately observe a query result of 5 for one item. The runs
do not prove that the same state-5 item took this branch during v796, or that
its virtual callback caused the readiness observation. The `+0xAD` branch and
the exact `+0x10` callback target remain runtime questions. No guest field
should be forced from this evidence.

The next useful runtime trace is the exact owner and item sequence through
`0x005093A0`: record list emptiness, each `item+0xE4` value, and the target and
return of the vtable `+0x10` call made by `0x005088C0`. This would determine
whether that callback advances or retains the observed status-5 item without
changing guest state.
