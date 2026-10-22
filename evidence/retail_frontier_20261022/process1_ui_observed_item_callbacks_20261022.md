# Retail UI list-item callback handlers: bounded original-PE audit

**Binary:** Need for Speed SHIFT PC retail 1.02, original `SHIFT.exe` PE32 x86, ImageBase `0x00400000`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. This hash was independently confirmed against the local game-data copy. **Scope:** the helper `0x00508860` and only its four callback targets observed in v789: `0x005AA830`, `0x0054B510`, `0x0054AEA0`, and `0x0054AA10`. This is static original-byte analysis; no new replay or game launch was performed.

## Runtime observation being followed up

The existing v789 report records nine `0x00508860` calls from `0x005092F0`, with item pointers in ECX and owner `O=0x27DFA5FC` in EDX. Six calls target `0x005AA830`; one each target `0x0054B510`, `0x0054AEA0`, and `0x0054AA10`. All returned EAX zero. The helper then wrote `item+0xE4=0` and `item+0xEC=1`. In v791, the distinct owner readiness updater `0x005092F0` cleared `BYTE[O+0x2D]` after its guard observed `DWORD[O+0x14]=9`. These are finite P-code guest observations, not native Windows/Wine execution or proof of a rendered retail menu.

## Direct helper `0x00508860`

At entry, ECX is item pointer `I`, EDX is owner `O`; the helper saves `I`, stores `O` into `DWORD[I+0xE8]`, and dispatches through the item's vtable slot `+4` with ECX still `I`. If the callback returns zero, it stores that EAX to `DWORD[I+0xE4]` and writes `BYTE[I+0xEC]=1`. It has no direct store to owner `O+0x14`, `O+0x2D`, or `O`'s vptr; it does not directly unlink or decrement the owner's list.

~~~asm
00508860: 56                   push   esi
00508861: 8b f1                mov    esi,ecx
00508863: 8b 06                mov    eax,DWORD PTR [esi]
00508865: 89 96 e8 00 00 00    mov    DWORD PTR [esi+0xe8],edx
0050886b: 8b 50 04             mov    edx,DWORD PTR [eax+0x4]
0050886e: ff d2                call   edx
00508870: 85 c0                test   eax,eax
00508872: 75 0d                jne    0x508881
00508874: 89 86 e4 00 00 00    mov    DWORD PTR [esi+0xe4],eax
0050887a: c6 86 ec 00 00 00 01 mov    BYTE PTR [esi+0xec],0x1
00508881: 5e                   pop    esi
00508882: c3                   ret
~~~

## Observed callback target bodies

`0x005AA830` has no explicit memory access and returns zero:

~~~asm
005aa830: 33 c0                xor    eax,eax
005aa832: c3                   ret
~~~

The other three targets each initialize fields relative to their own ECX receiver `I`, inspect a byte at offset `+0x104` of a pointer returned by `0x0040B870`, conditionally set `BYTE[I+0xED]=1`, then return zero. Their direct receiver-relative writes are only `DWORD[I+0x0C]`, `DWORD[I+0x04]`, and conditionally `BYTE[I+0xED]`:

~~~asm
0054b510: 56                   push   esi
0054b511: 8b f1                mov    esi,ecx
0054b513: 68 9c c6 ac 00       push   0xacc69c
0054b518: 8d 4e 10             lea    ecx,[esi+0x10]
0054b51b: e8 c0 74 0e 00       call   0x6329e0
0054b520: e8 5b ca fb ff       call   0x507f80
0054b525: 05 58 17 00 00       add    eax,0x1758
0054b52a: b9 28 a8 aa 00       mov    ecx,0xaaa828
0054b52f: 89 46 0c             mov    DWORD PTR [esi+0xc],eax
0054b532: e8 69 2c 0e 00       call   0x62e1a0
0054b537: 89 46 04             mov    DWORD PTR [esi+0x4],eax
0054b53a: e8 31 03 ec ff       call   0x40b870
0054b53f: 80 b8 04 01 00 00 00 cmp    BYTE PTR [eax+0x104],0x0
0054b546: 75 07                jne    0x54b54f
0054b548: c6 86 ed 00 00 00 01 mov    BYTE PTR [esi+0xed],0x1
0054b54f: 33 c0                xor    eax,eax
0054b551: 5e                   pop    esi
0054b552: c3                   ret

0054aea0: 56                   push   esi
0054aea1: 8b f1                mov    esi,ecx
0054aea3: 68 98 c5 ac 00       push   0xacc598
0054aea8: 8d 4e 10             lea    ecx,[esi+0x10]
0054aeab: e8 30 7b 0e 00       call   0x6329e0
0054aeb0: e8 cb d0 fb ff       call   0x507f80
0054aeb5: 05 58 17 00 00       add    eax,0x1758
0054aeba: b9 28 a8 aa 00       mov    ecx,0xaaa828
0054aebf: 89 46 0c             mov    DWORD PTR [esi+0xc],eax
0054aec2: e8 d9 32 0e 00       call   0x62e1a0
0054aec7: 89 46 04             mov    DWORD PTR [esi+0x4],eax
0054aeca: e8 a1 09 ec ff       call   0x40b870
0054aecf: 80 b8 04 01 00 00 00 cmp    BYTE PTR [eax+0x104],0x0
0054aed6: 75 07                jne    0x54aedf
0054aed8: c6 86 ed 00 00 00 01 mov    BYTE PTR [esi+0xed],0x1
0054aedf: 33 c0                xor    eax,eax
0054aee1: 5e                   pop    esi
0054aee2: c3                   ret

0054aa10: 56                   push   esi
0054aa11: 8b f1                mov    esi,ecx
0054aa13: 68 34 c5 ac 00       push   0xacc534
0054aa18: 8d 4e 10             lea    ecx,[esi+0x10]
0054aa1b: e8 c0 7f 0e 00       call   0x6329e0
0054aa20: e8 5b d5 fb ff       call   0x507f80
0054aa25: 05 6c 17 00 00       add    eax,0x176c
0054aa2a: b9 0c 4c ac 00       mov    ecx,0xac4c0c
0054aa2f: 89 46 0c             mov    DWORD PTR [esi+0xc],eax
0054aa32: e8 69 37 0e 00       call   0x62e1a0
0054aa37: 89 46 04             mov    DWORD PTR [esi+0x4],eax
0054aa3a: e8 31 0e ec ff       call   0x40b870
0054aa3f: 80 b8 04 01 00 00 00 cmp    BYTE PTR [eax+0x104],0x0
0054aa46: 75 07                jne    0x54aa4f
0054aa48: c6 86 ed 00 00 00 01 mov    BYTE PTR [esi+0xed],0x1
0054aa4f: 33 c0                xor    eax,eax
0054aa51: 5e                   pop    esi
0054aa52: c3                   ret
~~~

## Bounded conclusion and next target

The static bodies match the v789 return-value observation. The helper and these four callback bodies contain no direct store to original owner readiness `O+0x2D` or list count `O+0x14`; only the three nontrivial callbacks directly update fields of their item receiver. This does **not** prove the helper callees have no aliased or asynchronous effects, does not explain why the count remains 9, and does not identify a positive writer for `O+0x2D`.

**One next target: `0x00508C70`.** In v790, one post-traversal query through `0x005088A0` entered `0x00508C70` and returned 5; v791 separately recorded five `0x005088A0` queries returning 5, without recording their nested targets. `0x005088A0` stores its returned EAX into an item's `+0xE4`. The status semantics remain unknown, making `0x00508C70` the narrowest next test of whether item state can affect the readiness lifecycle.

No guest state was forced. No native launch, visible menu, retail draw, or race is claimed.
