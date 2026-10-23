# Process 1b: old-resource body 0x0064F090 — bounded original PE audit

Date: 2026-10-22. Source: original Need for Speed SHIFT PC retail 1.02 PE32 x86, ImageBase `0x00400000`. SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, independently confirmed by `sha256sum /mnt/data/SHIFT.exe`. Original disassembly, entire `0x0064F090–0x0064F1E7` inclusive (size 0x158; end-exclusive 0x0064F1E8), independently verified via bounded GNU objdump. Appendix A reproduces all 116 instructions with original bytes.

Scope: only full body `0x0064F090` and ABI/call boundary of direct callees. Do not infer callee side effects or class identity; no global caller/writer/vtable search. v791 original PE P-code guest run is a separate supplied finite observation, not rerun here. No code/runtime/P-code/renderer/guest-state edits, replay, live Windows/Wine execution, or menu/race/draw proof.

## 1. Exact ABI, receiver identity, stack, returns

Established original caller path: setup `0x00474D70` calls cleanup `0x00508E40` only if old `DWORD[O+0x30]!=0`; cleanup further tests `BYTE[O+0x3C]==0` and then passes `ECX=old DWORD[O+0x38]`, `EDX=old DWORD[O+0x30]` to wrapper `0x0064F250`. The wrapper tests EDX, pushes 0, then EDX, then performs `CALL 0x0064F090` at `0x0064F257`. Thus at function entry:

| Input | Proven value |
|---|---|
| ECX | `C=old DWORD[O+0x38]`, NOT original owner O |
| EDX | `A=old DWORD[O+0x30]`, nonzero for the established upstream path |
| [EBP+8] (first stack DWORD) | `A`, pushed second by wrapper |
| [EBP+0xC] (second stack DWORD) | `B=0`, pushed first by wrapper |
| [EBP+4] (return EIP) | `0x0064F25C` |

Entry `PUSH EBP; MOV EBP,ESP; SUB ESP,8; PUSH ESI; MOV ESI,ECX` yields ESI=C. First call `0x0064F099` gets ECX=C; incoming EDX=A has not yet been overwritten by this function, but the body does not use that original register as an independent semantic parameter before the first external call. Its two stack DWORDs are demonstrated inputs. No typed C++ method signature is proven.

All **three** normal exits use **RET 8**: `0x0064F154`, `0x0064F1AC` and `0x0064F1E5`. Callee cleanup is eight bytes, exactly the two wrapper-pushed DWORDs. Early `AL!=0` jumps directly from `0x0064F0A0` to `0x0064F1E1`, popping ESI only: EBX and EDI were not saved on that branch. Other paths pop EDI, EBX, ESI before RET 8. The outer wrapper has plain RET and returns to cleanup `0x00508E5A`. This body has **no uniform fixed EAX**: the early path propagates full EAX from `0x006476C0`, while other paths may propagate a later callee's EAX. There is no final forced boolean or HRESULT.

## 2. Complete branches and direct state changes

- `0x0064F099` calls `0x006476C0`. If returned **AL!=0**, `0x0064F0A0 JNE` exits directly via `0x0064F1E1` without any subsequent direct C-relative access.
- On AL=0, `0x0064F0A7` reads `DWORD[C+0x110]`; shift right 10 and mask bit0 make `BL=(value>>10)&1`. It writes local `DWORD[EBP-8]=C`, `BYTE[EBP-4]=BL`, `BYTE[EBP-3]=AL=0`. The `JE` at `0x0064F0BC` consumes **ZF from AND BL,1**, not from the initial TEST AL. Only if BL=1, call `0x00403CC0` with ECX=C, EDX=0x100 and then set local `BYTE[EBP-3]=1` regardless of that call's EAX.
- `0x0064F0CE` obtains second stack arg B; `0x0064F0D1` reads `DWORD[C+0x2C]` into EDX. `0x0064F0DB` calls `0x0062E2C0` with ECX=A, EDX=DWORD[C+0x2C], one pushed B. If EAX=R!=0, increment `DWORD[C+0xF4]`, read `DWORD[R]` and forward R plus DWORD[R] to shared `0x0064F270` call via `0x0064F1C8`.
- If the first lookup returns EAX=0, `0x0064F0F4` writes only **DL=BYTE(B)**; full EDX is NOT proven zero (the earlier callee may have clobbered its high 24 bits). `0x0064F0F9` calls `0x0062E410` with ECX=A, DL=BYTE(B), no pushed args; result EAX becomes R. If R=0, fallback `0x0064F1AF`.
- For R!=0, global `DWORD[0x00B8891C]` yields pointer G; signed bytes `G+0,G+1,G+2,G+3` are combined using MOVSX/SHL/OR into DWORD D. Compare `DWORD[R+8]` with D, then `DWORD[R]` with C. Mismatch in the first goes to fallback.
- If `DWORD[R+8]==D` but `DWORD[R]!=C`, call `0x00404260` with ECX=&[EBP-8], then call **`0x0064F250`** at `0x0064F141` with ECX=DWORD[R], EDX=A and no pushed args. The wrapper can then **re-enter `0x0064F090`** with ECX=DWORD[R], stack args A and 0. Call `0x00404260` again with the local pointer, then exit RET 8 at `0x0064F154`. This is a potential *indirect recursive call chain*, not evidence that recursion happened in v791.
- If both record comparisons match, increment `DWORD[C+0xF4]` and test `BYTE[C+0x24]`. For zero, call `0x00404260` with ECX=&[EBP-8] and return via `0x0064F1AC`. For nonzero, decrement `DWORD[C+0xE4]` (ADD -1), store **`DWORD[R+8]=0`**, call `0x00404260` with the local receiver, then call `0x0063BB60` with ECX=C+0x140, EDX=DWORD[R+4]. If its returned AL=0, push C+0x30, DWORD[R+4], 0xAEE94C and call `0x008F3DF0`. Here **the original caller itself cleans 12 bytes** with `ADD ESP,0xC`. Then call `0x00404260` with local pointer, exit RET 8.
- Fallback `0x0064F1AF` calls `0x00657560` with ECX=C, EDX=A, one pushed A. If EAX!=0, increment `DWORD[C+0xF4]`, push 0 then EAX, call `0x0064F270` with ECX=C. If EAX==0, skip the handler.
- Final `0x0064F1CF` tests BL, then local `BYTE[EBP-3]`. Only when **both nonzero** directly **`MOV DWORD[C],0`** at `0x0064F1D9`; then return via `0x0064F1E5`. BL=1 and local marker=1 are conditions for the store, not proof that the nested helper succeeded.

**Receiver-relative direct memory accesses (C is NOT O):**

| EIP(s) | Exact operation | Conditional path |
|---|---|---|
| `0x0064F0A7` | READ DWORD[C+0x110] | First AL==0 |
| `0x0064F0D1` | READ DWORD[C+0x2C] | Lookup path |
| `0x0064F0E4`, `0x0064F157`, `0x0064F1BE` | READ-MODIFY-WRITE DWORD[C+0xF4] +=1 | Separate success branches |
| `0x0064F15E` | READ BYTE[C+0x24] | Matching R |
| `0x0064F164` | READ-MODIFY-WRITE DWORD[C+0xE4] -=1 | Matching R and byte!=0 |
| `0x0064F1D9` | WRITE DWORD[C]=0 | BL!=0 and local marker!=0 |
| `0x0064F17A` | LEA C+0x140 | Address computation only, no direct read/write |
| `0x0064F18C` | ADD ESI,0x30, pointer becomes C+0x30 | Address computation only, passed on stack |

**Other direct memory accesses:** READ incoming [EBP+8] and [EBP+0xC]; WRITE locals [EBP-8] DWORD, [EBP-4] BYTE and [EBP-3] BYTE; final READ [EBP-3]; READ global DWORD [0x00B8891C] and pointed bytes [G+0..3]; READ DWORD[R], DWORD[R+4], DWORD[R+8]; **WRITE DWORD[R+8]=0** once on matching nonzero-C+24 branch. PUSH/CALL implicitly write return addresses/arguments to stack; POP/RET read them. No further explicit owner-O addressing exists.

## 3. Every direct outgoing call boundary (no callee body audit)

| Callsite → target | Return EIP | Provable outgoing registers/stack args |
|---|---|---|
| `0x64F099 → 0x6476C0` | `0x64F09E` | ECX=C; EDX=A on entry; 0 pushed |
| `0x64F0C5 → 0x403CC0` | `0x64F0CA` | ECX=C, EDX=0x100; 0 pushed |
| `0x64F0DB → 0x62E2C0` | `0x64F0E0` | ECX=A, EDX=DWORD[C+0x2C]; 1 pushed B |
| `0x64F0F9 → 0x62E410` | `0x64F0FE` | ECX=A; DL=BYTE(B), high EDX unknown; 0 pushed |
| `0x64F137 → 0x404260` | `0x64F13C` | ECX=&[EBP-8]; 0 pushed |
| `0x64F141 → 0x64F250` | `0x64F146` | ECX=DWORD[R], EDX=A; 0 pushed; possible indirect recursion |
| `0x64F149 → 0x404260` | `0x64F14E` | ECX=&[EBP-8]; 0 pushed |
| `0x64F172 → 0x404260` | `0x64F177` | ECX=&[EBP-8] retained from 0x64F132; 0 pushed |
| `0x64F180 → 0x63BB60` | `0x64F185` | ECX=C+0x140; EDX=DWORD[R+4]; 0 pushed |
| `0x64F196 → 0x8F3DF0` | `0x64F19B` | 3 stack args: first 0xAEE94C, second DWORD[R+4], third C+0x30; caller ADD ESP,0xC |
| `0x64F1A1 → 0x404260` | `0x64F1A6` | ECX=&[EBP-8]; 0 pushed |
| `0x64F1B5 → 0x657560` | `0x64F1BA` | ECX=C, EDX=A, 1 pushed A |
| `0x64F1CA → 0x64F270` | `0x64F1CF` | ECX=C, 2 pushed; first DWORD[R], second R (initial lookup), OR first returned EAX from 0x657560, second 0 (fallback) |

Only the `0x8F3DF0` call has **explicit caller-side ESP cleanup**, 12 bytes. For `0x62E2C0` and `0x657560` (one pushed DWORD each), and `0x64F270` (two pushed DWORDs), the lack of caller-side cleanup implies callee/equivalent stack balancing on normally returning paths. The *literal* callee RET opcode is unknown and not claimed.

## 4. Bounded owner alias and replay limits

The established **owner O** is the UI setup receiver; **C=old DWORD[O+0x38]**, a potentially unrelated pointer. This function writes only **C fields** (+0xF4, +0xE4, C first DWORD) and a candidate **R+8**. It **does not directly address original owner DWORD[O] (vptr), DWORD[O+0x14] (list count), or BYTE[O+0x2D] (readiness)**. Writing DWORD[C]=0 is not a proved vptr write to O.

An arbitrary C/R pointer can alias O or point to reachable structures; callee effects can also write memory. Neither aliasing nor its absence is proven from the given code. No outgoing callee implementation was analyzed or designated a destructor/free/COM Release. The evidence supports old-state-related lookup/adjustment behavior, **not proof of ownership semantics or cleanup success**.

The supplied **v791 original PE P-code guest replay** separately observed list count 9 and readiness-byte zero, but has **no event establishing this cleanup chain or any call in this body actually executed**. No native Windows/Wine game launch, drawn menu, race, or retail rendering is asserted.

## 5. Exactly one next evidence-backed target

**`0x0064F270`** — the sole next target. The original body calls it from **`0x0064F1CA`** on two convergent success paths with **ECX=C** and two explicitly pushed args: (first DWORD[R], second R) or (first EAX from `0x00657560`, second 0). It follows direct increments of `C+0xF4` and is the narrowest next boundary for investigating how those candidate records are handled. Its body is **not examined in this task**; no other future target or global sweep is proposed.

## Appendix A — complete original 0x0064F090–0x0064F1E7 (116 decoded instructions, size 0x158)

~~~asm
0064f090: 55                    push   ebp
0064f091: 8b ec                 mov    ebp,esp
0064f093: 83 ec 08              sub    esp,0x8
0064f096: 56                    push   esi
0064f097: 8b f1                 mov    esi,ecx
0064f099: e8 22 86 ff ff        call   0x6476c0
0064f09e: 84 c0                 test   al,al
0064f0a0: 0f 85 3b 01 00 00     jne    0x64f1e1
0064f0a6: 53                    push   ebx
0064f0a7: 8b 9e 10 01 00 00     mov    ebx,DWORD PTR [esi+0x110]
0064f0ad: c1 eb 0a              shr    ebx,0xa
0064f0b0: 80 e3 01              and    bl,0x1
0064f0b3: 89 75 f8              mov    DWORD PTR [ebp-0x8],esi
0064f0b6: 88 5d fc              mov    BYTE PTR [ebp-0x4],bl
0064f0b9: 88 45 fd              mov    BYTE PTR [ebp-0x3],al
0064f0bc: 74 10                 je     0x64f0ce
0064f0be: ba 00 01 00 00        mov    edx,0x100
0064f0c3: 8b ce                 mov    ecx,esi
0064f0c5: e8 f6 4b db ff        call   0x403cc0
0064f0ca: c6 45 fd 01           mov    BYTE PTR [ebp-0x3],0x1
0064f0ce: 8b 45 0c              mov    eax,DWORD PTR [ebp+0xc]
0064f0d1: 8b 56 2c              mov    edx,DWORD PTR [esi+0x2c]
0064f0d4: 57                    push   edi
0064f0d5: 8b 7d 08              mov    edi,DWORD PTR [ebp+0x8]
0064f0d8: 50                    push   eax
0064f0d9: 8b cf                 mov    ecx,edi
0064f0db: e8 e0 f1 fd ff        call   0x62e2c0
0064f0e0: 85 c0                 test   eax,eax
0064f0e2: 74 10                 je     0x64f0f4
0064f0e4: 83 86 f4 00 00 00 01  add    DWORD PTR [esi+0xf4],0x1
0064f0eb: 8b 08                 mov    ecx,DWORD PTR [eax]
0064f0ed: 50                    push   eax
0064f0ee: 51                    push   ecx
0064f0ef: e9 d4 00 00 00        jmp    0x64f1c8
0064f0f4: 8a 55 0c              mov    dl,BYTE PTR [ebp+0xc]
0064f0f7: 8b cf                 mov    ecx,edi
0064f0f9: e8 12 f3 fd ff        call   0x62e410
0064f0fe: 8b f8                 mov    edi,eax
0064f100: 85 ff                 test   edi,edi
0064f102: 0f 84 a7 00 00 00     je     0x64f1af
0064f108: a1 1c 89 b8 00        mov    eax,ds:0xb8891c
0064f10d: 0f be 08              movsx  ecx,BYTE PTR [eax]
0064f110: 0f be 50 01           movsx  edx,BYTE PTR [eax+0x1]
0064f114: c1 e1 08              shl    ecx,0x8
0064f117: 0b d1                 or     edx,ecx
0064f119: 0f be 48 02           movsx  ecx,BYTE PTR [eax+0x2]
0064f11d: 0f be 40 03           movsx  eax,BYTE PTR [eax+0x3]
0064f121: c1 e2 08              shl    edx,0x8
0064f124: 0b d1                 or     edx,ecx
0064f126: c1 e2 08              shl    edx,0x8
0064f129: 0b d0                 or     edx,eax
0064f12b: 39 57 08              cmp    DWORD PTR [edi+0x8],edx
0064f12e: 75 7f                 jne    0x64f1af
0064f130: 39 37                 cmp    DWORD PTR [edi],esi
0064f132: 8d 4d f8              lea    ecx,[ebp-0x8]
0064f135: 74 20                 je     0x64f157
0064f137: e8 24 51 db ff        call   0x404260
0064f13c: 8b 55 08              mov    edx,DWORD PTR [ebp+0x8]
0064f13f: 8b 0f                 mov    ecx,DWORD PTR [edi]
0064f141: e8 0a 01 00 00        call   0x64f250
0064f146: 8d 4d f8              lea    ecx,[ebp-0x8]
0064f149: e8 12 51 db ff        call   0x404260
0064f14e: 5f                    pop    edi
0064f14f: 5b                    pop    ebx
0064f150: 5e                    pop    esi
0064f151: 8b e5                 mov    esp,ebp
0064f153: 5d                    pop    ebp
0064f154: c2 08 00              ret    0x8
0064f157: 83 86 f4 00 00 00 01  add    DWORD PTR [esi+0xf4],0x1
0064f15e: 80 7e 24 00           cmp    BYTE PTR [esi+0x24],0x0
0064f162: 74 3d                 je     0x64f1a1
0064f164: 83 86 e4 00 00 00 ff  add    DWORD PTR [esi+0xe4],0xffffffff
0064f16b: c7 47 08 00 00 00 00  mov    DWORD PTR [edi+0x8],0x0
0064f172: e8 e9 50 db ff        call   0x404260
0064f177: 8b 57 04              mov    edx,DWORD PTR [edi+0x4]
0064f17a: 8d 8e 40 01 00 00     lea    ecx,[esi+0x140]
0064f180: e8 db c9 fe ff        call   0x63bb60
0064f185: 84 c0                 test   al,al
0064f187: 75 15                 jne    0x64f19e
0064f189: 8b 4f 04              mov    ecx,DWORD PTR [edi+0x4]
0064f18c: 83 c6 30              add    esi,0x30
0064f18f: 56                    push   esi
0064f190: 51                    push   ecx
0064f191: 68 4c e9 ae 00        push   0xaee94c
0064f196: e8 55 4c 2a 00        call   0x8f3df0
0064f19b: 83 c4 0c              add    esp,0xc
0064f19e: 8d 4d f8              lea    ecx,[ebp-0x8]
0064f1a1: e8 ba 50 db ff        call   0x404260
0064f1a6: 5f                    pop    edi
0064f1a7: 5b                    pop    ebx
0064f1a8: 5e                    pop    esi
0064f1a9: 8b e5                 mov    esp,ebp
0064f1ab: 5d                    pop    ebp
0064f1ac: c2 08 00              ret    0x8
0064f1af: 8b 55 08              mov    edx,DWORD PTR [ebp+0x8]
0064f1b2: 52                    push   edx
0064f1b3: 8b ce                 mov    ecx,esi
0064f1b5: e8 a6 83 00 00        call   0x657560
0064f1ba: 85 c0                 test   eax,eax
0064f1bc: 74 11                 je     0x64f1cf
0064f1be: 83 86 f4 00 00 00 01  add    DWORD PTR [esi+0xf4],0x1
0064f1c5: 6a 00                 push   0x0
0064f1c7: 50                    push   eax
0064f1c8: 8b ce                 mov    ecx,esi
0064f1ca: e8 a1 00 00 00        call   0x64f270
0064f1cf: 84 db                 test   bl,bl
0064f1d1: 74 0c                 je     0x64f1df
0064f1d3: 80 7d fd 00           cmp    BYTE PTR [ebp-0x3],0x0
0064f1d7: 74 06                 je     0x64f1df
0064f1d9: c7 06 00 00 00 00     mov    DWORD PTR [esi],0x0
0064f1df: 5f                    pop    edi
0064f1e0: 5b                    pop    ebx
0064f1e1: 5e                    pop    esi
0064f1e2: 8b e5                 mov    esp,ebp
0064f1e4: 5d                    pop    ebp
0064f1e5: c2 08 00              ret    0x8
~~~

## Appendix B — immediate call chain, not a new caller audit

~~~asm
00508e52: 8b 4e 38              mov    ecx,DWORD PTR [esi+0x38]
00508e55: e8 f6 63 14 00        call   0x64f250
00508e5a: 89 5e 30              mov    DWORD PTR [esi+0x30],ebx
0064f250: 85 d2                 test   edx,edx
0064f252: 74 08                 je     0x64f25c
0064f254: 6a 00                 push   0x0
0064f256: 52                    push   edx
0064f257: e8 34 fe ff ff        call   0x64f090
0064f25c: c3                    ret
~~~

Report only, no source/runtime/P-code/guest-state/renderer edits, no new replay.
