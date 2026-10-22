# Process 1 — bounded original retail primary adapter +0x118 / wrapper 0x0084FCF0

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`. **SHA-256, independently rechecked against `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Scope:** exactly the original executable wrapper `0x0084FCF0–0x0084FD1A`, its adapter primary-vtable pointer, existing bounded constructor/CreateDevice pointer provenance, the **call boundary** into `0x0084F000` (no deep helper analysis), and one adjacent original vtable slot solely for the next task. This is **static PE evidence**, not runtime observation. No global vtable/caller/setter sweep, review of the earlier `+0x114` method, renderer work, guest-state forcing, P-code modifications, code changes, game launch, replay, or PR.

## 1. Exact retail vtable cell and high-level result

The original PE's constructed primary adapter vptr is **`0x00B1BBA8`** (constructor `0x00850109`). The original `.rdata` DWORD at **`0x00B1BCC0 = 0x00B1BBA8+0x118`** has bytes **`F0 FC 84 00`**, i.e. **`DWORD[0x00B1BCC0] = 0x0084FCF0`**. The PE file offset of this DWORD is `0x0071A6C0`. This is the **static adapter method** entry, not the runtime Direct3D9 device's virtual method address.

This wrapper has two entry-to-call paths, not two distinct exits:

1. If **`BYTE[adapter+4] != 0`**, it loads **`ECX=adapter`** and makes the **direct near CALL `0x0084F000`**. The helper's returned EAX is **not examined or returned**. On normal helper return, execution falls through to the *same* underlying-device call as the other path.
2. If **`BYTE[adapter+4] == 0`**, a `JE` skips the helper and directly reaches the common device dispatch.
3. **Both normal paths:** obtain **`D=DWORD[adapter+8]`**, load its dynamic device vptr `V=DWORD[D]`, invoke **`DWORD[V+0x118]`** with `D` and the caller's unchanged second incoming stack DWORD, and return **that COM call's EAX unchanged**. The function ends with `POP ESI; POP EBP; RET 8`.

**API-level result:** the target device method is **`IDirect3DDevice9::ValidateDevice(DWORD *pNumPasses)`**, the official D3D9 COM method index **70** (`70 × 4 = 0x118`). The argument is an **output DWORD pointer** by the external API contract, and the method returns **HRESULT**. Naming it requires the CreateDevice-proven receiver, exact COM receiver+one-pointer argument shape, and the independent ordered interface contract, **not merely the hex slot number**. Official reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-validatedevice ; independent enumeration: https://docs.hsp.moe/Win32API/iface/Windows.Win32.Graphics.Direct3D9/IDirect3DDevice9.html . The actual dynamic D3D9 COM implementation address is **unresolved** from the retail PE.

## 2. Exact incoming ABI, branches, outgoing receiver, cleanup

Entry and frame:

```asm
0084fcf0: 55                    push   ebp
0084fcf1: 8b ec                 mov    ebp,esp
0084fcf3: 56                    push   esi
0084fcf4: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
```

The adapter virtual wrapper uses an **explicit stack receiver**, not incoming `ECX=this`. Its complete formal stack shape after `PUSH EBP; MOV EBP,ESP`:

| Stack location | Original PE operation | Contract interpretation |
|---|---|---|
| `[EBP+0x08]` | `0x0084FCF4: ESI=[EBP+8]`. Test `BYTE[ESI+4]`; optionally `MOV ECX,ESI` before direct helper call; later `EAX=[ESI+8]` | **adapter** receiver on wrapper's incoming stack |
| `[EBP+0x0C]` | `0x0084FD07: EDX=[EBP+0xC]`; `0x0084FD0C: PUSH EDX` | One unchanged DWORD; API-level **`DWORD *pNumPasses`** |

**Branch point:** `0x0084FCF7: CMP BYTE PTR [ESI+4],0` followed by `0x0084FCFB: JE 0x0084FD04`. A **zero** byte jumps directly to device dispatch; **nonzero** continues through `0x0084FCFD: MOV ECX,ESI` and `0x0084FCFF: CALL 0x0084F000`. There is no second test of the byte or of the helper result. The helper is **not** passed a wrapper-stack argument by `PUSH`; ECX is explicitly set to the adapter pointer. ESI was pushed in the prologue and, subject to normal x86 callee-saved ABI, survives the helper call; the PE code later uses it at `0x0084FD04`.

**Device path is common to both conditions:**

```asm
0084fd04: 8b 46 08              mov    eax,DWORD PTR [esi+0x8]  ; D = [adapter+8]
0084fd07: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]  ; output pointer
0084fd0a: 8b 08                 mov    ecx,DWORD PTR [eax]      ; V = [D]
0084fd0c: 52                    push   edx                      ; pNumPasses
0084fd0d: 50                    push   eax                      ; D (COM receiver)
0084fd0e: 8b 81 18 01 00 00     mov    eax,DWORD PTR [ecx+0x118] ; F = [V+0x118]
0084fd14: ff d0                 call   eax
0084fd16: 5e                    pop    esi
0084fd17: 5d                    pop    ebp
0084fd18: c2 08 00              ret    0x8
```

At entry to the *downstream COM method*, after `CALL` pushes return address, its x86 stdcall frame has **`[ESP+4]=D`** and **`[ESP+8]=outputPointer`**. No extra argument is pushed. The COM callee cleans its **own** two-DWORD frame, while the wrapper's **`RET 8`** cleans the original two incoming DWORDs (adapter and output pointer). These are **different** frames; there is no double cleanup.

**Return:** On both paths, `0x0084FD14: CALL EAX` returns to `POP ESI; POP EBP; RET 8`, which **do not modify EAX**. Thus its status is **fully transparent**, including a nonzero HRESULT. There is **no conditional early return**, helper-result check, status coercion, normalisation to zero, or separate helper EAX return. If the helper does not return normally (e.g. fault), the common dispatch need not be reached; such behavior is not demonstrated by the static PE. The actual HRESULT and `*pNumPasses` output are unknown.

The wrapper preserves EBP and ESI, does not allocate stack locals, and uses EAX/ECX/EDX as volatile registers. No additional callee-saved register management is present.

## 3. Helper call: exact proven boundary, limited semantics

**Direct original PE facts** about the helper interaction:

- **Call site:** `0x0084FCFF`, instruction `E8 FC F2 FF FF` resolves to **`0x0084F000`**.
- **Gate:** invoked only when `BYTE[adapter+4] != 0` at `0x0084FCF7`. If the byte is zero, the call is skipped via JE.
- **Receiver:** `0x0084FCFD: MOV ECX,ESI` explicitly passes the **same adapter** in ECX. No additional stack parameters are pushed by this wrapper.
- **Follow-up:** the wrapper unconditionally proceeds to the underlying device dispatch at `0x0084FD04` on ordinary helper return. It neither tests nor preserves helper EAX as its return value.

**Narrow original helper-entry corroboration (no helper-body audit):**

```asm
0084f000: 55                    push   ebp
0084f001: 8b ec                 mov    ebp,esp
0084f003: 83 ec 10              sub    esp,0x10
0084f006: 53                    push   ebx
0084f007: 56                    push   esi
0084f008: 8b f1                 mov    esi,ecx
0084f00a: f6 86 d8 19 00 00 04 test   BYTE PTR [esi+0x19d8],0x4
0084f011: 8b 5e 08              mov    ebx,DWORD PTR [esi+0x8]
0084f014: 57                    push   edi
0084f015: 0f 84 d2 00 00 00     je     0x84f0ed
```

The helper prologue **accepts ECX as its object receiver**, uses it as ESI, and its initial bytes **test bit `0x4` of `BYTE[adapter+0x19D8]`**, a dirty-mask bit set by the previously verified bounded sampler/texture setter. This provides an *evidence-backed possible deferred-state synchronization motivation* for the conditional helper call before validation.

**Important limitations:** the wrapper + this short helper prefix alone **do not prove** that the helper flushes any particular cache slot, performs all deferred setters, succeeds, calls Begin/EndStateBlock, produces Draw* calls, or is executed at runtime. Even if a prior bounded report investigated helper `0x0084F000`, no such downstream runtime effect is inferred for the present wrapper. The helper's complete body and all its external effects are deliberately **out of scope** for this assignment.

## 4. Pointer/device provenance and API-level identification

The earlier byte-proven standard initialization chain is used narrowly: the retail constructor at `0x00850100` places primary vptr `0x00B1BBA8` in `[adapter]` at `0x00850109`, then copies its supplied device pointer to `[adapter+8]` at `0x0085010F`. The established wrapper creation path calls a method consistent with `IDirect3D9::CreateDevice` at `0x0083306C`, retrieves the resulting device pointer from `[EDI]` at `0x00833095`, passes it into adapter helper `0x0084E2C0` via `0x0083309E`, and the helper stores it at `0x0084E2DD` as `[adapter+8]`. The embedded adapter `wrapper+0x1F7C` is published at `[wrapper+0x478]` by `0x008330B7`. This proves **ordinary object provenance** of `adapter+8` as an `IDirect3DDevice9*`, not any live-frame pointer/value.

**Distinct dispatch domains:**
- Static retail **adapter** primary table `+0x118` points to **`0x0084FCF0`** (known original PE address).
- Dynamic underlying **device** vtable `+0x118` points to an **unspecified Direct3D9 COM implementation** (loaded at runtime via `DWORD[DWORD[D]+0x118]`).

Under the standard `IDirect3DDevice9` interface ordering, method **index 69** is `SetSamplerState(Sampler,Type,Value)` and **index 70** is **`ValidateDevice(DWORD *pNumPasses)`**, followed by `SetPaletteEntries` at **index 71**. The current wrapper passes **one pointer-shaped explicit method argument** together with the device receiver and returns raw EAX, exactly the normal x86 stdcall shape of `ValidateDevice`. This alignment of *verified receiver type*, *independent COM slot order*, and *full argument ABI* supports the API identity; the **type** of the output pointer and its direction are API inference from Microsoft rather than typed PE opcodes.

Microsoft's specification describes validation of **currently configured** texture blending operations / render state against device capabilities, returning HRESULT and filling `DWORD* pNumPasses` with a pass count. This **does not draw primitives or execute render passes merely because ValidateDevice was called**. A successful underlying invocation could inspect device state and write `*pNumPasses`; whether such an invocation occurred or succeeded here is **not known**. Source: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-validatedevice .

## 5. Bounded effects, evidence tiers and limits

**Direct original PE-byte findings within `0x0084FCF0–0x0084FD1A`:**
- Read `BYTE[adapter+4]` for helper gate, read `DWORD[adapter+8]` for the underlying receiver, read `DWORD[D]` and `DWORD[device.vptr+0x118]` for dispatch, and read caller's second stack DWORD.
- No direct **memory write** via adapter, cache, queue, valid byte, dirty mask, or output pointer by the wrapper itself; **zero local stores** to `BYTE[adapter+4]`, `adapter+0x19D8`, etc.
- Two possible calls: direct `CALL 0x0084F000` **only** when flag is nonzero, then common indirect **`CALL DWORD[device.vptr+0x118]`** on every normal path. No local BeginStateBlock/EndStateBlock or DrawPrimitive/DrawIndexedPrimitive/Draw* call/import.
- No local null/bounds check of `outputPointer`, no HRESULT test, no device-state validation performed by wrapper instructions themselves.
- The **helper is an outgoing call** and can have downstream effects beyond the wrapper. Reporting **zero wrapper-local writes** is not the same as asserting all external callees are side-effect-free.
- The API-facing output pointer may be written by underlying COM `ValidateDevice`. This external write is **not present as a direct PE store** in this wrapper. Potential alias of the caller-provided pointer into adapter memory is unproven; no universal absence of indirect alias writes is asserted.

**API inference vs PE:** method name `ValidateDevice`, HRESULT return and `DWORD *pNumPasses` [out] semantics are established from official D3D9 documentation coupled to byte-proven interface-pointer provenance and exact slot/ABI. The original PE does **not** resolve the function pointer inside the dynamic device vtable or disclose its HRESULT or pass count.

**Runtime evidence:** no replay, instrumentation, game execution or guest-state forcing was performed. The earlier bounded v757 P-code observation concerned specifically selected Begin/EndStateBlock/Draw targets (reported zero events across 360 frames); it **does not instrument this wrapper**, its helper invocation, or the underlying ValidateDevice COM method. No runtime invocation, draw, flush completion or error code is claimed.

**Unresolved:** concrete live D3D9 device pointer/vptr and COM EIP; whether flag was 0 or nonzero in a frame; helper side effects/return or errors, whether deferred state synchronizes before validation; pass count and HRESULT, caller aliases, real callsites and overall game reachability. These questions require separate evidence and are outside this bounded task.

## 6. Exactly one next evidence-backed target

**`0x0084FA60` — next primary adapter slot `+0x11C`.** The immediately adjacent original `.rdata` cell is **`DWORD[0x00B1BCC4]=0x0084FA60`**, original raw bytes **`60 FA 84 00`**. Narrow original code beginning at `0x0084FA60` reads `DWORD[adapter+8]`, forwards **two method arguments** with explicit device receiver, and loads the dynamic underlying method through **`device.vptr+0x11C`**. This is a justified **single** separate follow-up for exact ABI/API classification and contrasts with the one-argument ValidateDevice forwarding without triggering a broad sweep. **No classification of `0x0084FA60` is asserted as proven by this report.** The previously studied helper `0x0084F000` is **not** proposed as a second target.

## Appendix A — complete original retail block, every instruction and byte, `0x0084FCF0–0x0084FD1A`

```asm
0084fcf0: 55                    push   ebp
0084fcf1: 8b ec                 mov    ebp,esp
0084fcf3: 56                    push   esi
0084fcf4: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0084fcf7: 80 7e 04 00           cmp    BYTE PTR [esi+0x4],0x0
0084fcfb: 74 07                 je     0x84fd04
0084fcfd: 8b ce                 mov    ecx,esi
0084fcff: e8 fc f2 ff ff        call   0x84f000
0084fd04: 8b 46 08              mov    eax,DWORD PTR [esi+0x8]
0084fd07: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084fd0a: 8b 08                 mov    ecx,DWORD PTR [eax]
0084fd0c: 52                    push   edx
0084fd0d: 50                    push   eax
0084fd0e: 8b 81 18 01 00 00     mov    eax,DWORD PTR [ecx+0x118]
0084fd14: ff d0                 call   eax
0084fd16: 5e                    pop    esi
0084fd17: 5d                    pop    ebp
0084fd18: c2 08 00              ret    0x8
```

## Appendix B — narrow original PE constructor / created-device publication

```asm
00850100: 55                    push   ebp
00850101: 8b ec                 mov    ebp,esp
00850103: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00850106: 56                    push   esi
00850107: 8b f1                 mov    esi,ecx
00850109: c7 06 a8 bb b1 00     mov    DWORD PTR [esi],0xb1bba8
0085010f: 89 46 08              mov    DWORD PTR [esi+0x8],eax

00833095: 8b 17                 mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea    ecx,[esi+0x1f7c]
0083309d: 52                    push   edx
0083309e: e8 1d b2 01 00        call   0x84e2c0
0084e2dd: 89 46 08              mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov    DWORD PTR [esi+0x478],eax
```

## Appendix C — adjacent primary-vtable cells and narrow next-method opening (not a new audit)

```text
.rdata VA 0x00B1BCBC: 80 E9 84 00 => 0x0084E980 (adapter +0x114)
.rdata VA 0x00B1BCC0: F0 FC 84 00 => 0x0084FCF0 (adapter +0x118)
.rdata VA 0x00B1BCC4: 60 FA 84 00 => 0x0084FA60 (adapter +0x11C)
```

```asm
0084fa60: 55                    push   ebp
0084fa61: 8b ec                 mov    ebp,esp
0084fa63: 8b 55 10              mov    edx,DWORD PTR [ebp+0x10]
0084fa66: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084fa69: 8b 40 08              mov    eax,DWORD PTR [eax+0x8]
0084fa6c: 8b 08                 mov    ecx,DWORD PTR [eax]
0084fa6e: 52                    push   edx
0084fa6f: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084fa72: 52                    push   edx
0084fa73: 50                    push   eax
0084fa74: 8b 81 1c 01 00 00     mov    eax,DWORD PTR [ecx+0x11c]
0084fa7a: ff d0                 call   eax
0084fa7c: 5d                    pop    ebp
0084fa7d: c2 0c 00              ret    0xc
```

**Publication:** Markdown report only, no source-code edits, runtime/P-code/renderer/guest-state modifications, replay, launch, or PR.
