# Process 1 — original retail primary adapter +0x10C / wrapper 0x0084E900

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **SHA-256, checked against mounted original `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Scope:** one original executable function `0x0084E900–0x0084E923`, its specific primary-adapter vtable DWORD, and the previously established short constructor/device-pointer path. No source or runtime/P-code/renderer/guest-state changes, replay, launch, global vtable sweep, caller enumeration or setter search. Neighboring +0x108 is accepted as prior context and **not** reanalyzed. Primary proof: SHA-verified original PE disassembled with GNU `objdump -D -Mintel -w`; vtable values independently read as little-endian DWORDs from original PE `.rdata`. External official D3D9 interface contract is only used for the qualified API naming.

## 1. Answer and exact PE vtable identity

**Retail-byte proven:** constructor `0x00850100` writes `DWORD[adapter]=0x00B1BBA8` at `0x00850109`. Original `.rdata` at **`0x00B1BCB4 = 0x00B1BBA8+0x10C`**, file offset **`0x0071A6B4`**, contains raw bytes **`00 E9 84 00`**, i.e. **`DWORD[0x00B1BCB4]=0x0084E900`**. This is a statically resolved **adapter** primary-vtable target, not the address of the method in the dynamic **device** vtable.

The full wrapper has **one unconditional indirect CALL**, no branch, and no memory store. It accepts `adapter` plus three explicit DWORD method inputs; it obtains `device=DWORD[adapter+8]` and dispatches through `DWORD[DWORD[device]+0x10C]`. It forwards all inputs unchanged, cleans the original four input DWORDs via **`RET 0x10`**, and propagates EAX from the underlying device call without checking or changing it.

**Qualified API identification:** for an `IDirect3DDevice9*` produced by the previously established CreateDevice path, interface slot **67** (`0x10C / 4`) is **`IDirect3DDevice9::SetTextureStageState(DWORD Stage, D3DTEXTURESTAGESTATETYPE Type, DWORD Value)`**, which returns HRESULT. Identification is supported by the proven COM object type, official ordered interface slot and three DWORD inputs. **PE instructions alone do not contain the API name or C++ enum type**, and the underlying implementation is a **dynamic COM method** with no determined runtime EIP. Official Microsoft reference: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-settexturestagestate .

## 2. Incoming x86 ABI and outgoing COM stack

The complete original machine-code block is in Appendix A, including the final RET and every instruction byte. Entry:

| Stack at wrapper entry (after frame creation) | Exact original operation | API-level interpretation |
|---|---|---|
| `[EBP+0x08]` | `0x0084E906: EAX=[EBP+8]`; `0x0084E909: EAX=DWORD[EAX+8]` | explicit stack **adapter receiver**; device loaded from adapter+8 |
| `[EBP+0x0C]` | `0x0084E913: EDX=[EBP+0x0C]`; `0x0084E916: PUSH EDX` | first argument, `DWORD Stage` |
| `[EBP+0x10]` | `0x0084E90F: EDX=[EBP+0x10]`; `0x0084E912: PUSH EDX` | second argument, `D3DTEXTURESTAGESTATETYPE Type` |
| `[EBP+0x14]` | `0x0084E903: EDX=[EBP+0x14]`; `0x0084E90E: PUSH EDX` | third argument, `DWORD Value` |

**Exact execution sequence** (all byte-grounded):

1. `0x0084E900: PUSH EBP`, `0x0084E901: MOV EBP,ESP`. No stack locals and no use of entry ECX as adapter receiver.
2. `0x0084E903` loads third argument into EDX, `0x0084E906` loads adapter, `0x0084E909` reads `D=DWORD[adapter+8]`, and `0x0084E90C` obtains dynamic underlying device vptr `V=DWORD[D]` in ECX.
3. Four outgoing pushes, in **right-to-left** order: `0x0084E90E PUSH arg3`; `0x0084E912 PUSH arg2`; `0x0084E916 PUSH arg1`; `0x0084E917 PUSH D`.
4. `0x0084E918: EAX=DWORD[V+0x10C]`; `0x0084E91E: CALL EAX`.
5. `0x0084E920: POP EBP`; `0x0084E921: RET 0x10`, encoded `C2 10 00` through `0x0084E923`. The wrapper is callee-cleanup: **16 bytes**, namely adapter plus three arguments.

For the **underlying COM call**, the callee's stack after CALL supplies `[ESP+4]=D`, `[ESP+8]=Stage`, `[ESP+0x0C]=Type`, `[ESP+0x10]=Value`. Under standard x86 COM stdcall the downstream call cleans its **separate four-DWORD outgoing stack frame**; the wrapper later cleans its own original four-DWORD entry frame, not the same arguments twice. This exact stack frame distinguishes the forwarding from a direct `ECX=this` call.

**Return/HRESULT:** nothing modifies EAX between `CALL EAX` and `RET 0x10`, so the result is unmodified EAX. The **HRESULT type** comes from the D3D9 interface contract, not from an explicit branch or tagged return in PE. No check for HRESULT sign, equality, failure or D3D_OK; no retry, conversion to bool, extra status/caching code or alternative return.

## 3. Bounded object provenance and interface identification

The original constructor `0x00850100` uses ECX for *construction-time* adapter pointer, stores primary vptr `0x00B1BBA8` to `[adapter]` at `0x00850109`, and copies its stack-supplied device pointer into `[adapter+8]` at `0x0085010F`. The prior narrow, byte-verified initialization route has an `IDirect3D9::CreateDevice`-compatible call at `0x0083304D–0x0083306C`, obtains device output from `[EDI]` at `0x00833095`, passes it at `0x0083309E` into helper `0x0084E2C0` for embedded adapter `wrapper+0x1F7C`, and stores it at `0x0084E2DD` as `[adapter+8]`. The embedded pointer is published at `0x008330B7` as `[wrapper+0x478]`.

The limited identity join is therefore:

```text
IDirect3D9::CreateDevice-produced IDirect3DDevice9* D
  → adapter construction/helper publication
  → DWORD[adapter+8] = D
  → wrapper 0x0084E909 reads D
  → V = DWORD[D] (dynamic device vtable)
  → F = DWORD[V+0x10C] (dynamic device method)
  → CALL F(D, arg1, arg2, arg3)
```

The adapter's fixed **primary table** is distinguished from the device's **dynamically allocated/installed table**. No assertion is made that a live object still has the same vptr, that the wrapper executed, or that the COM method has a static PE EIP. Validity of any actual receiver and values in a running game is **unresolved**.

Official D3D9 method identity is corroborated by exactly three **input** parameters and index 67 immediately following `GetTextureStageState` (slot 66), but **this report does not classify the neighboring wrapper** beyond that ordering. In API terms, `SetTextureStageState` sets a texture stage state; the original wrapper simply delegates and does **not** itself update the adapter's state-cache fields. The Microsoft API specifies zero-based Stage values from 0 to 7 for the actual device contract; **this original wrapper does not implement that bounds check**.

## 4. Local branches, writes, state and Draw* boundary

The complete target includes:
- **0 branches**, zero local conditions or null/array/Stage/Type/Value validation, and one indirect CALL.
- **0 explicit writes to adapter fields**, including `BYTE[adapter+4]`, cache arrays, `adapter+0x1988`, `adapter+0x198C`, and dirty flag/mask `adapter+0x19D8`. The only adapter field touched is a **read of DWORD[adapter+8]**.
- **0 BeginStateBlock/EndStateBlock dispatches**, no primary adapter slot `+0xF0`, and **0 DrawPrimitive/DrawIndexedPrimitive/UP/other Draw*** imports or dispatches. Only the device `+0x10C` virtual slot is invoked.
- **0 AddRef/Release** or resource-ownership changes expressed in this function body.

Under the **external D3D9 API contract**, a successful underlying `SetTextureStageState` can change texture-stage render state inside the device. **This is not a direct adapter-cache write** and is **not proof that a specific COM call executed or succeeded**. The actual COM device implementation and device state are outside the retail PE bytes. Three input method arguments are forwarded unchanged, so this particular wrapper provides no explicit output pointer (unlike the preceding getter-style ABI). Arbitrary register/pointer alias side effects of the external implementation cannot be established by the retail wrapper code.

The absence of effects above is **strictly confined to the 16-instruction target**. It must not be generalized to downstream COM internals, other adapter slots, any frame, UI gate, live renderer or global draw reachability.

## 5. Evidence ledger

**Original PE, directly verified:** specified SHA-256; primary vtable cell `0x00B1BCB4→0x0084E900` (raw `00 E9 84 00`); all original target bytes and 16 disassembled instructions; stack arguments at `[EBP+8/+0xC/+0x10/+0x14]`; one dynamic device-vtable call through `+0x10C`; exact push sequence, `RET 0x10`, unmodified EAX; no branch, own memory write or state/Draw* forwarding.

**API-level inference, separate from bytes:** D3D9 interface slot 67 identifies `IDirect3DDevice9::SetTextureStageState(DWORD, D3DTEXTURESTAGESTATETYPE, DWORD)` with HRESULT return, supported by the proven device-origin chain, public method order and exact three-argument shape. Possible mutation of device texture-stage state is an API consequence if actually called and successful, not a demonstrated runtime event.

**Runtime evidence:** none gathered in this task. Older bounded v757 P-code observation of **zero events for separately selected Begin/EndStateBlock/Draw targets** does not instrument `0x0084E900` and cannot prove this function executed or was not invoked. No replay, game launch, frame tracing, P-code modification or guest forcing performed.

**Unresolved by scope:** actual caller/receiver at runtime, value and validity of Stage/Type/Value, concrete device COM method EIP, actual HRESULT/state change, method reachability and cross-function effects. No global search performed.

## 6. Exactly one next evidence-backed target

**`0x0084E930`**, primary adapter slot **`+0x110`**. Original PE `.rdata` at `0x00B1BCB8` contains bytes **`30 E9 84 00` → `0x0084E930`**. Its initial original machine bytes check `BYTE[adapter+4]`, and a cached branch calculates an indexed DWORD read using `((stage << 4) + type) × 4` relative to adapter offset `0xF8C`; the other path forwards to dynamic underlying device slot `+0x110`. This establishes a concrete **separate** next bounded byte/ABI target, without assuming an actual runtime call or auditing it here.

## Appendix A — entire original function 0x0084E900–0x0084E923 (16 decoded instructions)

```asm
0084e900: 55                    push   ebp
0084e901: 8b ec                 mov    ebp,esp
0084e903: 8b 55 14              mov    edx,DWORD PTR [ebp+0x14]
0084e906: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084e909: 8b 40 08              mov    eax,DWORD PTR [eax+0x8]
0084e90c: 8b 08                 mov    ecx,DWORD PTR [eax]
0084e90e: 52                    push   edx
0084e90f: 8b 55 10              mov    edx,DWORD PTR [ebp+0x10]
0084e912: 52                    push   edx
0084e913: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
0084e916: 52                    push   edx
0084e917: 50                    push   eax
0084e918: 8b 81 0c 01 00 00     mov    eax,DWORD PTR [ecx+0x10c]
0084e91e: ff d0                 call   eax
0084e920: 5d                    pop    ebp
0084e921: c2 10 00              ret    0x10
```

## Appendix B — exact original narrow constructor / device-pointer anchors (not reanalysis)

```asm
00850109: c7 06 a8 bb b1 00     mov    DWORD PTR [esi],0xb1bba8
0085010f: 89 46 08              mov    DWORD PTR [esi+0x8],eax
00850176: c6 46 04 00           mov    BYTE PTR [esi+0x4],0x0

00833095: 8b 17                 mov    edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea    ecx,[esi+0x1f7c]
0083309d: 52                    push   edx
0083309e: e8 1d b2 01 00        call   0x84e2c0
0084e2dd: 89 46 08              mov    DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea    eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov    DWORD PTR [esi+0x478],eax
```

## Appendix C — confirmed neighboring primary vtable cell / next target opening (no broader analysis)

```text
.rdata 0x00B1BCB0: D0 E8 84 00 → 0x0084E8D0  (adapter slot +0x108)
.rdata 0x00B1BCB4: 00 E9 84 00 → 0x0084E900  (adapter slot +0x10C)
.rdata 0x00B1BCB8: 30 E9 84 00 → 0x0084E930  (adapter slot +0x110)
```

```asm
0084e930: 55                    push   ebp
0084e931: 8b ec                 mov    ebp,esp
0084e933: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084e936: 80 78 04 00           cmp    BYTE PTR [eax+0x4],0x0
0084e93a: 74 1b                 je     0x84e957
0084e93c: 8b 4d 0c              mov    ecx,DWORD PTR [ebp+0xc]
0084e93f: c1 e1 04              shl    ecx,0x4
0084e942: 03 4d 10              add    ecx,DWORD PTR [ebp+0x10]
0084e945: 8b 94 88 8c 0f 00 00  mov    edx,DWORD PTR [eax+ecx*4+0xf8c]
```

**Only this Markdown report was added; no source/runtime/P-code/renderer/guest state or P2 files modified.**
