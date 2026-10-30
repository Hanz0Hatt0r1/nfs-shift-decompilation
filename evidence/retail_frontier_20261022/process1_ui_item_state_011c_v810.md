# Original-PE UI item state callback trace: v810

Date: 2026-10-22. This is a bounded replay of the original SHIFT PC retail
1.02 PE32 x86 executable in the Linux P-code guest runtime. It is not a native
Windows/Wine launch and does not prove the menu or a race was reached.

## Run identity and limits

- Original PE SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Runtime SHA-256:
  `135c2452d882da91a249fb01acd9e5a3deedab42bde826097e43d9eb6aaff54e`
- The v659 override/supplement manifest was validated before launch; its
  SHA-256 is `6977898b7ff79edfb84f9b6f6d9e5ff98d8e073d17d88f345e8a1edb77e73a0e`.
- 360 host frames completed with probe exit 0, 1,750,327 dispatches, 4,733
  unique functions, zero Vulkan validation errors, and no trace truncation.
  The expanded trace used more target slots than v809. The frontier wrapper
  returned status 1 because the dispatch total was lower than v809's; this
  count-only comparison is not evidence of a guest semantic regression.
- `guest_draw_translation=false` and `retail_rendering_proven=false`.
  Host-frame completion and dispatch totals are execution diagnostics, not
  proof of retail rendering, frontend readiness, or race entry.
- v810 log SHA-256:
  `05e4c7f83c37fc690446390e615e0c12a314f1e8af9a2a1a55d263d88f124925`.
- The local log and JSON are retained outside the repository under
  `/home/pes/nfs-shift-recompilation-artifacts/retail-run-20261021/`.

## Observed item and callback

Across 1,120 selected calls to original function `0x005093A0`, owner
`O=0x27DFA5FC` had `DWORD[O+0x14]=9`, `BYTE[O+0xAD]=0`, and readiness
`BYTE[O+0x2D]=0` in every sample. Each selected function call returned EAX 0.

The targeted trace recorded 1,114 calls to the virtual target
`0x004D1F10` from wrapper `0x005088C0`. The target's entry ECX was one of the
registered item addresses, and `DWORD[item+0xE4]=5` in every sample. Its
`DWORD[item+0x11C]` values and returns were:

| `item+0x11C` | Calls | Callback return |
|---:|---:|---:|
| 1 | 4 | 3 |
| 2 | 1,110 | 5 |

The original bytes of `0x004D1F10` read `DWORD[ECX+0x11C]`; value 1 returns 3,
values 3 or 4 return 7, and other values return 5. Thus the repeated return 5
for the main item is consistent with the value 2 observed in the retail guest
memory; this trace does not indicate an interpreter failure in this callback.

For `I=0x27DFAD78`, the sampled state was `DWORD[I+0x11C]=2`. Exact-address
write provenance identifies the last recorded writer at dispatch 461,817 as
`0x00D8CB90`, with ECX/ESI `0x27DFAE68` (`I+0xF0`), writing four bytes at
`0x27DFAE94` (`I+0x11C`) with value 2. The trace attributes that execution to
caller `0x00509F20`; the return address recorded by the provenance layer was
`0x00508DEC`. The writer identity is a runtime observation; this evidence
does not assign a C++ type or explain what later event should change the
field.

Original-PE bytes relevant to the callback and observed writer:

~~~asm
004d1f10: 8b 81 1c 01 00 00  mov    eax,DWORD PTR [ecx+0x11c]
004d1f16: 83 f8 01           cmp    eax,0x1
004d1f19: 75 06              jne    0x4d1f21
004d1f1b: b8 03 00 00 00     mov    eax,0x3
004d1f20: c3                 ret
004d1f21: 83 f8 03           cmp    eax,0x3
004d1f24: 74 0a              je     0x4d1f30
004d1f26: 83 f8 04           cmp    eax,0x4
004d1f29: b8 05 00 00 00     mov    eax,0x5
004d1f2e: 75 05              jne    0x4d1f35
004d1f30: b8 07 00 00 00     mov    eax,0x7
004d1f35: c3                 ret

00d8cb90: 55                 push   ebp
00d8cb91: 8b ec              mov    ebp,esp
00d8cb93: 8b 45 0c           mov    eax,DWORD PTR [ebp+0xc]
00d8cb96: 85 c0              test   eax,eax
00d8cb98: 56                 push   esi
00d8cb99: 8b f1              mov    esi,ecx
00d8cb9b: 74 03              je     0xd8cba0
00d8cb9d: 89 46 0c           mov    DWORD PTR [esi+0xc],eax
00d8cba0: 8b 45 08           mov    eax,DWORD PTR [ebp+0x8]
00d8cba3: 8b ca              mov    ecx,edx
00d8cba5: 89 46 08           mov    DWORD PTR [esi+0x8],eax
00d8cba8: e8 b3 ad 8a ff    call   0x637960
00d8cbad: eb 0f              jmp    0xd8cbbe
00d8cbbe: 8d 4e 10           lea    ecx,[esi+0x10]
00d8cbc1: 8b d0              mov    edx,eax
00d8cbc3: e8 28 94 8a ff    call   0x635ff0
00d8cbc8: eb 07              jmp    0xd8cbd1
00d8cbd1: c6 46 20 00        mov    BYTE PTR [esi+0x20],0x0
00d8cbd5: c7 46 2c 02 00 00 00 mov DWORD PTR [esi+0x2c],0x2
00d8cbdc: c7 46 24 00 00 00 00 mov DWORD PTR [esi+0x24],0x0
00d8cbe3: c7 46 28 00 00 00 00 mov DWORD PTR [esi+0x28],0x0
00d8cbea: c6 46 04 01        mov    BYTE PTR [esi+0x4],0x1
00d8cbee: 5e                 pop    esi
00d8cbef: 5d                 pop    ebp
00d8cbf0: c2 08 00           ret    0x8
~~~

`0x00D8CB90` is in section `.secu`, not `.text`. The observed ESI value makes
`ESI+0x2C` equal the item field at `I+0x11C`. The bytes therefore agree with
the runtime writer provenance for this invocation. The skipped padding bytes
inside the function's laid-out ranges are INT3 fill and are omitted above;
the complete executed instruction sequence and the terminating `ret 0x8` are
shown.

## Conclusion and remaining blocker

The callback returns 5 because its original input field is 2. The last
recorded writer explicitly initializes that field to 2 from an embedded
subobject. The bounded trace does not identify a later state transition or
prove that the value is supposed to change in this run. The next required
evidence is a static/runtime provenance audit of other writers and the
producer that would move this observed item out of value 2; no guest state
should be forced from this trace.
