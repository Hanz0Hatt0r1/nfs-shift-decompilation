# Process 1b — bounded UI readiness guard 0x00554050 (retail PE, v783 context)

**Date:** 2026-10-22. **Original executable:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **SHA-256, independently checked with `sha256sum /mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Strict scope:** complete static block `0x00554050–0x00554057`, direct call-site/branch in writer `0x005092F0`, and the *existing user-supplied* v783 observation for one object. No global caller/writer sweep, no list helpers, no source changes, runtime changes, P-code, renderer, guest-state forcing, game execution, new trace or replay. The earlier report `process-reports/2026-10-22-process1b-ui-ready-predicate-005092f0-v783.md` is accepted as contextual evidence and is not reaudited.

## 1. Exact byte-grounded result

The **entire retail guard** is only three instructions:

~~~asm
00554050: 83 79 0c 00           cmp    DWORD PTR [ecx+0xc],0x0
00554054: 0f 94 c0              sete   al
00554057: c3                    ret
~~~

The original binary independently disassembled via `objdump -D -M intel -w --start-address=0x00554050 --stop-address=0x00554060 /mnt/data/SHIFT.exe` reproduces these exact bytes. Padding at `0x00554058` and following is `INT3`, not part of the function.

**Predicate as precisely implemented:** let `P=ECX` and `X=DWORD[P+0xC]` (32-bit little-endian load). Instruction `CMP X,0` sets the x86 condition flags including `ZF=(X==0)`, then `SETE AL` writes **exactly one byte**, `AL = 1` if `X==0` and `AL=0` otherwise. It is a **zero predicate**, not a nonzero predicate. There is **no branch inside the guard**, no source-level type check, no bounds validation and no memory write.

**EAX granularity is critical:** `SETE AL` updates **only bits 7..0 of EAX**, not the full EAX DWORD. Bits 31..8 remain the values already present on entry. `CMP` does not modify EAX; `RET` does not normalize it. Hence it is correct to report **`AL=1` or `AL=0`** and incorrect to claim **`EAX=1` or `EAX=0`** from this three-instruction body alone. The following *writer* tests `AL`, so upper EAX bits do not affect that caller's gate. If the original EAX was `0x12345678`, the zero-field path would produce `0x12345601` and the nonzero-field path `0x12345600`; these are illustrative bitwise examples, **not replay values**.

## 2. Exact ABI, inputs, return and side effects

| Element | Original PE fact | Bounded interpretation |
|---|---|---|
| `ECX` on entry | Used as base pointer in `CMP DWORD[ECX+0xC],0` | Sole proven register input |
| `[ESP]` on entry | Return address consumed by `RET` | No explicit incoming stack arguments; ordinary `RET` (no `RET imm16`) |
| `EDX`, other GPRs | Not referenced | Not proven inputs |
| `AL` on exit | Set to 1 iff read DWORD is zero | Complete observable boolean result used by writer |
| EAX upper 24 bits | No instruction writes them | Preserved from entry; **not fixed by this guard** |
| EFLAGS | `CMP` updates flags; `SETE` consumes `ZF` | Flags are affected; no subsequent arithmetic normalizes them |
| Memory | Only a DWORD **read** at `[ECX+0x0C]` | No memory store, object initialization, readiness-field write, queued update or call |

No function prologue is needed: this leaf method uses incoming ECX directly, emits no `PUSH`, `POP` or nested `CALL`, and uses **plain `RET`**. On normal return the caller regains its stack with only the return address consumed. No incoming stack parameter count or class name can be determined beyond this actual use. Invalid ECX or an unmapped `ECX+0xC` address could fault at the memory read; there is no local recovery.

## 3. Precise relationship to caller 0x005092F0

The accepted writer function uses entry **`ECX=O`**, moves it to EDI, computes `EBX=O+8` and passes **`ECX=EBX=O+8`** into this guard. Therefore the direct guard memory access is:

~~~text
guard ECX          = O + 0x08
guard [ECX+0x0C]  = DWORD[O+0x14]
writer readiness   = BYTE[O+0x2D] (separate field)
~~~

Narrow relevant original PE callsite:

~~~asm
005092f6: 8b f9                 mov    edi,ecx
005092f8: 8d 5f 08              lea    ebx,[edi+0x8]
005092fb: 8b cb                 mov    ecx,ebx
005092fd: e8 4e ad 04 00        call   0x554050
00509302: 84 c0                 test   al,al
00509304: 74 08                 je     0x50930e
00509306: 5f                    pop    edi
00509307: 33 c0                 xor    eax,eax
00509309: 5b                    pop    ebx
0050930a: 8b e5                 mov    esp,ebp
0050930c: 5d                    pop    ebp
0050930d: c3                    ret
0050930e: 56                    push   esi
0050930f: 8d 55 fc              lea    edx,[ebp-0x4]
00509312: 8b cb                 mov    ecx,ebx
00509314: c6 47 2d 00           mov    BYTE PTR [edi+0x2d],0x0
~~~

**Truth table, original exact byte behavior:**

| Value of `DWORD[O+0x14]` during `CMP` | Guard `ZF` | Guard `AL` | Writer `TEST AL,AL; JE` | Writer-local readiness-byte outcome |
|---|---:|---:|---|---|
| `0` | 1 | 1 | `JE` not taken, early `EAX=0; RET` | **Does not execute `BYTE[O+0x2D]=0`** on this invocation |
| Nonzero, any 32-bit pattern | 0 | 0 | `JE 0x0050930E` taken | **Executes `BYTE[O+0x2D]=0`** at `0x00509314` before list traversal |

There is no off-by-eight ambiguity here: **guard +0xC is writer object +0x14**, because caller supplies **O+8**, not O directly.

Notice the counterintuitive polarity: the guard returns **true** for a zero field, so the writer **skips reset** for zero and **resets readiness** for nonzero. The guard's byte result is not a true readiness flag itself, and the writer's return codes cannot be identified with the guard EAX's entire 32-bit value. The previous writer report verified that its own complete block does not set `O+0x2D` to 1.

## 4. Source/initialization of DWORD[O+0x14]: unresolved

**Nothing in the full three-instruction guard**:
- stores into `DWORD[O+0x14]` or creates O;
- reveals whether that DWORD is a pointer, a size/count, bitset, ownership marker, or another internal field;
- names a constructor, initializer, setter or producer of `O+0x14`;
- bounds or validates the DWORD;
- proves a unique writer of that field anywhere in the PE.

The **caller-only** snippet likewise supplies a pointer and branches on AL; it contains no source store or constructor trace for `O+0x14`. A comparison to zero is not a proof of the value's source or semantic name. Finding the producer would require a **separately scoped** provenance investigation; this assignment intentionally does not perform a global writer or caller scan.

## 5. Direct PE vs v783 controlled observation vs inference

**Original PE-byte facts verified in this task:** `CMP DWORD[ECX+0xC],0`, `SETE AL`, `RET`; one input register and one DWORD memory read; only AL is fully defined in the return value, with high EAX bits preserved; no local stores/branches/calls. The narrow direct caller passes O+8 and checks AL; the exact writer store at `0x00509314` is `BYTE[O+0x2D]=0` when **O+0x14 was read nonzero**, assuming normal execution of the shown call and control-flow instructions.

**User-provided v783 fact, not reproduced in this task:** controlled replay of original PE **360 frames, exit code 0, Vulkan validation errors 0**; in `0x0054BB20`, `DWORD[param+0x1F04]=0` and progress reached **30**; children `0x00508EA0` and `0x00508E90` returned zero **1010** times each; `0x00508EC0` had no calls. For object **O=`0x27DFA5FC`** the observed byte `O+0x2D` was zero and its last recorded write was one-byte zero from **writer `0x005092F0`**, dispatch **461058**, caller **`0x0054B8B0`**, return **`0x0054BAC8`**, thread **`0x00175C45`**. These facts describe only that specific replay, not gameplay/menu readiness in general.

**Combined bounded implication:** if the recorded last write is the byte store at `0x00509314` from the actual original code, then that *writer invocation* must have followed the **AL=0**, **guard-read-nonzero** path: the DWORD at **`O+0x14` was nonzero when `0x00554050` executed the CMP**. This conclusion narrows its zero/nonzero predicate at that moment. It **does not give the numerical DWORD value**, or identify its writer/initializer, or show why that field was nonzero.

**Inference only / not established:** the name “readiness” is a working label based on the observed field usage. This predicate does not prove causality of progress=30, the zero-returning children, absence of other readiness-positive stores, actual menu/race scene, Draw* dispatches, or universal runtime behavior. No such claim is made.

## 6. Exactly one next evidence-backed target

**Passive, read-only capture at original guard EIP `0x00554050`**, in a **separate future bounded validation task**, for the *specific v783-observed writer object* **O=`0x27DFA5FC`** on the branch at writer `0x005092FD`: record **`ECX`**, **`DWORD[ECX+0x0C]`** and the returned **`AL`**, correlating to the existing writer dispatch and thread. This is directly evidence-backed by the **literal PE CMP** and a real observed zero-store caller in v783; it is the one closest way to obtain the **actual missing DWORD value** while avoiding a global sweep or speculative producer identification. Any future observation must be **read-only**, never force guest-state or write `O+0x14`. **No such runtime capture is performed or claimed here.**

**No second next target** or generic writer/caller enumeration is proposed.

## Appendix A — complete original retail guard (`0x00554050–0x00554057`)

~~~asm
00554050: 83 79 0c 00           cmp    DWORD PTR [ecx+0xc],0x0
00554054: 0f 94 c0              sete   al
00554057: c3                    ret
~~~

## Appendix B — narrow directly linked writer branch, original machine bytes (not reanalysis)

~~~asm
005092f6: 8b f9                 mov    edi,ecx
005092f8: 8d 5f 08              lea    ebx,[edi+0x8]
005092fb: 8b cb                 mov    ecx,ebx
005092fd: e8 4e ad 04 00        call   0x554050
00509302: 84 c0                 test   al,al
00509304: 74 08                 je     0x50930e
00509306: 5f                    pop    edi
00509307: 33 c0                 xor    eax,eax
00509309: 5b                    pop    ebx
0050930a: 8b e5                 mov    esp,ebp
0050930c: 5d                    pop    ebp
0050930d: c3                    ret
0050930e: 56                    push   esi
0050930f: 8d 55 fc              lea    edx,[ebp-0x4]
00509312: 8b cb                 mov    ecx,ebx
00509314: c6 47 2d 00           mov    BYTE PTR [edi+0x2d],0x0
~~~

**Report only**; no code/P-code/runtime/guest state/renderer changes, replay, global search or PR.
