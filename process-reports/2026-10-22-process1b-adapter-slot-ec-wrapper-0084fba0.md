# Process 1 — Retail adapter +0xEC / 0x0084FBA0: CreateStateBlock forwarder

**Scope:** bounded static analysis of the original Need for Speed SHIFT PC retail 1.02 PE32 x86, ImageBase `0x00400000`; no rendering implementation, P-code/runtime changes, guest-state forcing, game execution/replay, global caller/vtable/field-writer searches, or changes to any project source. This is separate from the preceding +0xE8 report; its analysis is not repeated.

**Retail PE SHA-256:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, **independently verified in this task** against `/mnt/data/SHIFT.exe` with SHA-256. Full target machine code independently re-disassembled using GNU `objdump -D -M intel -w` over original PE bytes. The exact primary-vtable DWORD independently confirmed by PE `.rdata` hexdump.

**Timing:** Exact user-message delivery/startedAt UTC metadata is **not exposed to tools in this turn**. No speculative delivery time or computed deadline is claimed. Report delivered during this task, not as a continuation of any canceled work.

## 1. Determination and limits

**This is a transparent x86 callee-cleanup, three-DWORD forwarding wrapper.** Its only indirect call is to `DWORD[DWORD[DWORD[adapter+8]]+0xEC]`: obtain `D=DWORD[adapter+8]`, `V=DWORD[D]`, and invoke `DWORD[V+0xEC]` with `D` as explicit COM receiver and two unmodified caller parameters.

**Identity of the underlying operation:** `IDirect3DDevice9::CreateStateBlock(D3DSTATEBLOCKTYPE Type, IDirect3DStateBlock9 **ppSB)`. This is strongly supported by (i) original retail CreateDevice-result provenance for `adapter+8`, (ii) exact push order and two-parameter shape, and (iii) the established *same device interface* adjacent slots `+0xF0` and `+0xF4` for BeginStateBlock and EndStateBlock. The D3D9 interface ordinal is 59 (`59×4=0xEC`), **a corroboration rather than the sole justification**. The concrete *runtime* COM method address is read through the underlying device vptr and **cannot be equated to a fixed PE function address** from this block. This result is API-level identification supported by PE bytes and established COM interface identity, not direct import linkage.

## 2. Exact original primary-adapter vtable value

Original PE `.rdata` bytes (this is **adapter vtable**, not the dynamic underlying device vtable):

```text
VA 0x00B1BBA8      primary adapter vptr
VA 0x00B1BC90      DWORD C0 E7 84 00 = 0x0084E7C0 (adapter slot +0xE8)
VA 0x00B1BC94      DWORD A0 FB 84 00 = 0x0084FBA0 (adapter slot +0xEC)
VA 0x00B1BC98      DWORD C0 FB 84 00 = 0x0084FBC0 (adapter slot +0xF0)
VA 0x00B1BC9C      DWORD F0 FB 84 00 = 0x0084FBF0 (adapter slot +0xF4)
```

The primary vptr `0x00B1BBA8` is written to `[adapter]` at constructor `0x00850109`. In `0x0085010F`, constructor initializes `[adapter+8]` from its provided pointer. Separately, on the established retail device-creation path, `0x0083304D–0x0083306C` calls `[IDirect3D9.vptr+0x40]` with a CreateDevice-compatible argument set and output pointer; `0x00833095–0x0083309E` retrieves the created device pointer, passes it into `0x0084E2C0`, and `0x0084E2DD` writes that pointer to `[adapter+8]`. The wrapper publishes the embedded adapter `wrapper+0x1F7C` at `[wrapper+0x478]` at `0x008330B7`. These provenance facts establish the ordinary constructed instance, **not** any dynamic run-time value, immutable pointer guarantee, or observed invocation of this +0xEC entry.

## 3. Exact ABI and stack contract

`0x0084FBA0` uses explicit stack parameters rather than entry `ECX=this`. At entry `[ESP+4]=adapter`, `[ESP+8]=arg1`, `[ESP+0xC]=arg2`. After `PUSH EBP; MOV EBP,ESP` these correspond to:

| Callee stack slot | Proven use in original machine code | Interface-level identification |
|---|---|---|
| `[EBP+0x08]` | Adapter pointer, read at `0x0084FBA6` | Wrapper receiver (`this` passed on stack) |
| `[EBP+0x0C]` | Passed unchanged to downstream as first explicit argument at `0x0084FBAF–0x0084FBB2` | `D3DSTATEBLOCKTYPE Type` |
| `[EBP+0x10]` | Passed unchanged as second explicit argument at `0x0084FBA3` and `0x0084FBAE` | `IDirect3DStateBlock9 **ppSB` (output parameter) |

* `0x0084FBA9`: `D=DWORD[adapter+8]`; `0x0084FBAC`: `V=DWORD[D]`. Both dereference the actual device pointer (no local null/type check).
* Stack preparation is precisely **`PUSH arg2`** at `0x0084FBAE`, **`PUSH arg1`** at `0x0084FBB2`, then **`PUSH D`** at `0x0084FBB3`. Thus on entry to underlying COM method its stack arguments are `[ESP+4]=D`, `[ESP+8]=arg1`, `[ESP+0xC]=arg2`.
* `0x0084FBB4`: load `F=DWORD[V+0xEC]` into EAX; `0x0084FBBA: CALL EAX` dispatches the device operation. Standard COM stdcall of this method cleans its *own* three 32-bit stack arguments.
* `0x0084FBBC: POP EBP`, `0x0084FBBD: RET 0x0C` (the RET occupies **0x0084FBBD–0x0084FBBF**) returns to caller and cleans the wrapper's **three** 32-bit original arguments. Two separate callee-cleanup boundaries do **not** imply double-cleanup.
* No EBX/ESI/EDI saves are needed: the method only operates on EAX, ECX, EDX, EBP and the stack. The frame has **zero local variable bytes**. Entry ECX and EDX are not incoming arguments and are overwritten.

There is **only one straight-line normal return path**, **no conditional branch**, no HRESULT compare, no error recovery, no normalization or conversion. EAX returned by the underlying call is **propagated unchanged** across POP EBP and RET 0x0C. Under the D3D9 interface contract this is the underlying `HRESULT`, but the wrapper performs no positive/negative/success/failure interpretation of its own. The return value need not be zero; an observed status is **not** present in the retail static evidence.

## 4. Side effects and negative findings, confined to this function

**Direct original PE-byte effects:**
- Read `DWORD[adapter+8]`; read `DWORD[device]`; read `DWORD[device.vptr+0xEC]`; read the two incoming stack DWORDs.
- Push three outgoing DWORD parameters; invoke **one** indirect COM method `0x0084FBBA`; return its raw EAX.
- **No direct instruction writes any `adapter` byte**, including `BYTE[adapter+4]`. `adapter+4` is **not even read** in this function. No cache/dirty queue/flag update is performed here.
- **No executable call to primary adapter slot +0xF0 / BeginStateBlock** and **no direct or transitive Draw* call** is established within the bounded function; the only outgoing target is the `CreateStateBlock`-compatible device vtable slot +0xEC. No direct PE import call.
- Device method **may populate the caller-provided output** `ppSB` and allocate an `IDirect3DStateBlock9` object on success by API contract, but these are **possible downstream COM effects**, not direct PE stores and not observed runtime effects.

**Bounded alias caveat:** the wrapper itself contains no `MOV [adapter+4],...`. However, since `arg2` is externally supplied and forwarded as an output pointer, an intentionally aliasing caller could point it at memory inside adapter, and COM could write through it. **No such caller or alias is established** in this assignment. Therefore the precise answer is *no proven write of BYTE[adapter+4] in this code or its evidenced normal parameter route*, not a global guarantee against all write-through aliases.

There are no standalone BeginStateBlock, EndStateBlock or Draw* calls in this method. The adjacent presence of such entries in the *adapter vtable* is not execution, and slot +0xEC is **CreateStateBlock, not BeginStateBlock**.

## 5. Evidence tiers

**Original PE-byte facts (verified):** SHA-256 original; exact complete function machine bytes, one indirect CALL, explicit incoming/outgoing stack parameters, unmodified forwarded DWORD values, raw return EAX and RET 0x0C; adapter primary vtable `+0xEC → 0x0084FBA0` at `.rdata` `0x00B1BC94`; constructor and device-pointer storage/provenance instruction addresses.

**API identification / grounded inference:** under the verified CreateDevice-derived IDirect3DDevice9 receiver, the `+0xEC` device interface call taking `Type, ppSB` is `IDirect3DDevice9::CreateStateBlock`, supported by interface ordering and the complementary adjacent Begin/EndStateBlock slots. The actual device COM method EIP, failure/success result and API implementation are not known from these original PE bytes.

**Runtime:** No replay or game launch was requested or performed. Earlier bounded v757 P-code traces reported zero events for a *different selected* Begin/EndStateBlock/Draw* target set; **they do not measure the invocation count or runtime values of 0x0084FBA0**. No execution/draw claims, no guest-state forcing and no runtime changes.

**Unresolved:** whether any runtime caller reaches this adapter entry; dynamic vptr substitutions; `Type` and output pointer values for an actual call; downstream object or allocation effects; nonstandard aliases or after-call processing. Excluded by scope: global caller/vtable/field writer searches.

## 6. Exactly one next evidence-backed target

**`0x0084FC20`** — **the immediately following primary adapter vtable slot `+0xF8`**, verified by PE `DWORD[0x00B1BCA0]=0x0084FC20`. Its visible standalone function uses explicit `[EBP+8]=adapter`, `[EBP+0xC]` as a forwarded parameter and dispatches via **`underlyingDevice.vptr+0xF8`**. A new bounded byte/ABI analysis can determine that underlying method's identity without extending this task into unrelated callsites or setters.

## Appendix A — entire original retail PE machine-code block 0x0084FBA0–0x0084FBBF

```asm
84fba0: 55                    push   ebp
84fba1: 8b ec                 mov    ebp,esp
84fba3: 8b 55 10              mov    edx,DWORD PTR [ebp+0x10]
84fba6: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
84fba9: 8b 40 08              mov    eax,DWORD PTR [eax+0x8]
84fbac: 8b 08                 mov    ecx,DWORD PTR [eax]
84fbae: 52                    push   edx
84fbaf: 8b 55 0c              mov    edx,DWORD PTR [ebp+0xc]
84fbb2: 52                    push   edx
84fbb3: 50                    push   eax
84fbb4: 8b 81 ec 00 00 00     mov    eax,DWORD PTR [ecx+0xec]
84fbba: ff d0                 call   eax
84fbbc: 5d                    pop    ebp
84fbbd: c2 0c 00              ret    0xc
```

## Appendix B — minimal original constructor/device-pointer anchors (retail bytes)

```asm
850109: c7 06 a8 bb b1 00     mov DWORD PTR [esi],0xb1bba8
85010f: 89 46 08              mov DWORD PTR [esi+0x8],eax
850176: c6 46 04 00           mov BYTE PTR [esi+0x4],0x0

83304d: 8b 46 08              mov eax,DWORD PTR [esi+0x8]
833050: 8b 10                 mov edx,DWORD PTR [eax]
833052: 8b 52 40              mov edx,DWORD PTR [edx+0x40]
83306b: 50                    push eax
83306c: ff d2                 call edx
833095: 8b 17                 mov edx,DWORD PTR [edi]
833097: 8d 8e 7c 1f 00 00     lea ecx,[esi+0x1f7c]
83309d: 52                    push edx
83309e: e8 1d b2 01 00        call 0x84e2c0
84e2dd: 89 46 08              mov DWORD PTR [esi+0x8],eax
8330b1: 8d 86 7c 1f 00 00     lea eax,[esi+0x1f7c]
8330b7: 89 86 78 04 00 00     mov DWORD PTR [esi+0x478],eax
```

## Appendix C — bounded next-slot bytes, identity only; no next-task semantics claimed

```asm
84fc20: 55                    push ebp
84fc21: 8b ec                 mov ebp,esp
84fc23: 8b 45 08              mov eax,DWORD PTR [ebp+0x8]
84fc26: 8b 40 08              mov eax,DWORD PTR [eax+0x8]
84fc29: 8b 55 0c              mov edx,DWORD PTR [ebp+0xc]
84fc2c: 8b 08                 mov ecx,DWORD PTR [eax]
84fc2e: 52                    push edx
84fc2f: 50                    push eax
84fc30: 8b 81 f8 00 00 00     mov eax,DWORD PTR [ecx+0xf8]
84fc36: ff d0                 call eax
84fc38: 5d                    pop ebp
84fc39: c2 08 00              ret 0x8
```
