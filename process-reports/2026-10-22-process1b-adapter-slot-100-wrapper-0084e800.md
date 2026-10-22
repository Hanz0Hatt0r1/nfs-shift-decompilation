# Process 1 — original retail adapter +0x100 wrapper 0x0084E800

**Date:** 2026-10-22. **Scope:** bounded machine-byte / ABI / constructor-device pointer provenance for **one** original retail adapter method, not a global vtable/caller or setter search. No runtime/source/P-code/renderer/guest-state modifications, no guest-state forcing, no replay, no claimed game execution, no P2 changes.

**PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase `0x00400000`. **SHA-256 verified anew against `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Original PE disassembled with `objdump -D -Mintel -w --start-address=0x84e800 --stop-address=0x84e870`. Vtable DWORDs read directly from original PE `.rdata`. Earlier accepted constructor/device provenance is reused; no previous `+0xFC` analysis is repeated.

## Answer: exact bounded conclusion

The **primary adapter vptr `0x00B1BBA8`**, set by constructor `0x00850100`, has **`DWORD[0x00B1BCA8]=DWORD[vptr+0x100]=0x0084E800`**; PE bytes **`00 E8 84 00`**. This method accepts `(adapter, stage, outputPointer)` as **three explicit stack DWORDs** and has two branches:

* **`BYTE[adapter+4]!=0`:** read a pointer `P=DWORD[adapter+0x1908+4*stage]`. If nonnull, invoke **`DWORD[DWORD[P]+4]` with one pushed receiver P**, consistent with COM `IUnknown::AddRef`. Then **re-read** `P` from the same array slot, store `DWORD[outputPointer]=P`, return **EAX=0**. If P is null, skip the COM call and still write the null P and return EAX=0.
* **`BYTE[adapter+4]==0`:** obtain the pre-proven **`IDirect3DDevice9*` D=DWORD[adapter+8]**; forward `(D, stage, outputPointer)` to **`DWORD[DWORD[D]+0x100]`**; propagate its EAX exactly.
* Both paths use **`RET 0x0C`**. The cached branch has no index/output validation, no bounds check and no HRESULT check. The forwarding branch has no local input check or HRESULT check.

**API-level interpretation, conditional on established COM device identity:** `IDirect3DDevice9::GetTexture(DWORD Stage, IDirect3DBaseTexture9 **ppTexture)` (D3D9 vtable index **64**, offset `0x100`). The official interface specifies `Stage` as input, `ppTexture` as output, an HRESULT result, and reference-count increment for a retrieved texture: https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-gettexture . The *PE itself* only proves two unchanged DWORD arguments, pointer write, virtual call, and vtable offsets; C++ types, AddRef identity and semantic input/output direction use the external COM contract plus the previously proven device pointer source. Neither the address of actual device GetTexture implementation nor that of the cached object's COM method is resolved in retail PE.

No instruction in the complete target directly writes adapter fields, modifies `BYTE[adapter+4]`, cache, dirty bits or queues; it **reads** +4 and the indexed cache slot. No BeginStateBlock, EndStateBlock, or Draw* call is present in either branch. Cached path **can mutate the returned COM object's reference count via external AddRef** and always **writes `DWORD[*output]`**; external COM/dynamic aliases cannot be globally excluded.

## 1. Exact three-argument stack ABI and cleanup

Prologue `0x0084E800: PUSH EBP; 0x0084E801: MOV EBP,ESP; 0x0084E803: PUSH ESI`. The receiver is **not passed via entry ECX**. Register roles:

| Entry location | Retail evidence | API-level meaning |
|---|---|---|
| `[EBP+0x08]` | `ESI=DWORD[EBP+8]`; reads +4, +8, and indexed slot | adapter pointer, explicit stack receiver |
| `[EBP+0x0C]` | `EDI=DWORD[EBP+0xC]` in cache branch or `ECX=DWORD[EBP+0xC]` in device branch | `DWORD Stage` / cache index |
| `[EBP+0x10]` | cached: `ECX=DWORD[EBP+0x10]`, then `MOV [ECX],EAX`; forwarded: `EAX=DWORD[EBP+0x10]` and `PUSH EAX` | pointer to output DWORD, by API `IDirect3DBaseTexture9** ppTexture` |

**Callee cleanup:** cached path `0x0084E83B: RET 0xC` (bytes occupy `0x0084E83B–0x0084E83D`); device path `0x0084E856: RET 0xC` (through `0x0084E858`). Neither path normalizes/cleans a separate caller frame. Both preserve EBP and ESI; cache branch also pushes and restores EDI. The method uses volatile EAX/ECX/EDX and has no local stack allocation.

**Status return:** cache path explicitly `XOR EAX,EAX` at `0x0084E837` so **full 32-bit EAX=0**, independently of AddRef's return. Device forwarding path returns **COM EAX unchanged**: after `CALL EDX` at `0x0084E852` only `POP ESI; POP EBP; RET 0xC` occur, with no HRESULT branch, sign test or conversion. Under the API contract EAX is an HRESULT, but its runtime value is not observed.

## 2. Cache-enabled branch `BYTE[adapter+4]!=0`

At `0x0084E807` the byte `[ESI+4]` is compared with 0. `0x0084E80B: JE 0x0084E83E` branches *only when zero*. Otherwise:

1. `0x0084E80D: PUSH EDI`; `0x0084E80E: EDI=stage=[EBP+0xC]`.
2. `0x0084E811: CMP DWORD[ESI+EDI*4+0x1908],0`. **Exact cache address `adapter+0x1908+4*stage`**; stage is unmasked/unrestricted 32-bit index.
3. **Nonzero slot:** `0x0084E81B: EAX=P=DWORD[adapter+0x1908+4*stage]`; `0x0084E822: ECX=DWORD[P]` (object vptr); `0x0084E824: EDX=DWORD[ECX+4]`; `0x0084E827: PUSH P`; `0x0084E828: CALL EDX`. Under normal COM identity, vptr index 1 is `IUnknown::AddRef`; no other method arguments. **No direct pointer output and no adapter-memory write yet.**
4. **Zero slot:** branch `0x0084E819: JE 0x0084E82A`, skipping AddRef entirely.
5. **Join:** `0x0084E82A: EAX=DWORD[adapter+0x1908+4*stage]` is a **fresh second load**, not guaranteed by bytes to equal the P passed to AddRef if arbitrary concurrent/external mutation occurs. `0x0084E831: ECX=DWORD[EBP+0x10]`; `0x0084E834: POP EDI`; **`0x0084E835: MOV DWORD[ECX],EAX`**, writing one DWORD to caller-supplied output pointer. `0x0084E837: XOR EAX,EAX`; restore ESI, EBP; `RET 0xC`.
6. **No cache bounds check, no stage normalization, no null check of output pointer, no validation of cached pointer's COM interface identity, no callback-error handling.** The only local conditional pointer check is cache slot `P!=0` before calling through P.vptr.

**Classification limits:** the location is a cached DWORD pointer array by instruction shape. With the device `GetTexture` counterpart and the observed `IUnknown`-shaped AddRef dispatch, the value is consistent with `IDirect3DBaseTexture9*`. The machine block alone does **not** prove that every nonnull cached pointer has a valid vptr or originates from a correctly typed D3D9 texture. The exact upstream producer/ownership of every slot is **not** resolved here. No capacity or allowed stage range for this adapter array is encoded in this function; Microsoft D3D9 API constraints must not be substituted for a missing PE bounds check.

## 3. Uncached branch `BYTE[adapter+4]==0`: full forwarding

`0x0084E83E: EAX=outputPointer`; `0x0084E841: ESI=DWORD[adapter+8]=D`; `0x0084E844: ECX=stage`; `0x0084E847: EDX=DWORD[D]`; `0x0084E849: EDX=DWORD[EDX+0x100]`. Exact push order:
- `0x0084E84F: PUSH outputPointer`;
- `0x0084E850: PUSH stage`;
- `0x0084E851: PUSH D`;
- `0x0084E852: CALL EDX`.

The called COM function's entry frame therefore has `[ESP+4]=D`, `[ESP+8]=stage`, `[ESP+0xC]=outputPointer`. Three DWORDs belong to the *device COM* call, and standard stdcall cleans these; the outer wrapper separately cleans its *original* three DWORDs via `RET 0xC`. The device method may write to the output and change reference count under D3D9 API semantics, **not by any instruction local to this wrapper**. The exact runtime COM implementation address is loaded from dynamic `DWORD[device]`, never a fixed retail `.rdata` method address.

**Proven receiver origin:** constructor `0x00850100` at `0x00850109` writes `DWORD[adapter]=0x00B1BBA8` and `0x0085010F` writes supplied device to `[adapter+8]`. In the previously verified local initializer path, retail `IDirect3D9::CreateDevice` result from `[EDI]` is forwarded at `0x00833095–0x0083309E` into `0x0084E2C0`, whose instruction `0x0084E2DD` stores the device pointer to adapter+8. `0x008330B7` publishes the embedded adapter pointer as `[wrapper+0x478]`. This establishes interface-pointer provenance for the ordinarily initialized adapter, **not** the actual runtime value on any unobserved invocation.

## 4. Byte-bound effects and answer to forbidden broad inferences

In the **complete `0x0084E800–0x0084E858`** machine block:

* It **reads** `BYTE[adapter+4]`, never directly writes it; there are **no stores to any adapter cache field** or dirty flag and **no setters/queue mutations**.
* There is exactly **one COM-like indirect call** on either branch: cached `object.vptr+4` at `0x0084E828` if nonnull, or dynamic `device.vptr+0x100` at `0x0084E852` when flag is zero. Neither is a Draw* call or a BeginStateBlock/EndStateBlock call under the established interfaces.
* **One direct memory store** via caller-controlled `DWORD[outputPointer]` at `0x0084E835` in the cached branch. A malicious/aliased caller could pass outputPointer inside adapter, including `adapter+4`, but **no alias to such an address is established** in this bounded task. Hence **no proven write to adapter+4**, not universal memory noninterference. The external COM call can also modify a returned object's reference count.
* No other function bodies, all-stage producers, caller graph, renderer Draw* reachability, or global +4 writers are examined.

## 5. Evidence tiers: PE vs external API vs runtime

**Original PE facts, independently verified:** SHA-256, exact vtable value `0x00B1BCA8 → 0x0084E800`; code instruction bytes and two branches; explicit stack ABI and both `RET 0xC` exits; address calculation `adapter+0x1908+4*stage`; conditional cached-object vptr slot +4 call; subsequent output DWORD write and EAX=0; device `[adapter+8]` and vptr +0x100 forwarding and raw EAX return; no direct writes to adapter fields, state-block operations or Draw*.

**API inference / external specification:** `IDirect3DDevice9::GetTexture(DWORD, IDirect3DBaseTexture9**)` at interface slot 64 with HRESULT and output pointer; COM AddRef semantics and texture reference-counting from documented D3D9 contract. The typed API and exact runtime method addresses cannot be read from this function's bytes alone.

**Runtime:** previous user-reported bounded v757 P-code replay was **not** targeted at `0x0084E800`; zero BeginStateBlock/Draw* events in its targeted frame window do **not** establish whether GetTexture was entered or how many times. **No replay/game execution was performed or claimed in this task.** No runtime code/state changes.

**Unresolved:** cache index validity/capacity, full producer or destruction chain of `adapter+0x1908` array, live COM object identity, output-pointer aliases, dynamic vptr EIPs, actual HRESULT/refcount in a runtime frame. None is promoted from offset coincidence to proof.

## 6. Exactly one next evidence-backed target

**`0x0084E860` — primary adapter vtable slot `+0x104`**. The same original `.rdata` contains `DWORD[0x00B1BCAC]=0x0084E860` (bytes `60 E8 84 00`). The opening instruction bytes of this adjacent function check `BYTE[adapter+4]` and, on one branch, **write `DWORD[adapter+0x1908+4*stage]`**, the *exact array slot read here*. Its alternative branch forwards to **`device.vptr+0x104`**. A new, separate bounded audit of this precise producer/ownership link would be evidence-backed without a global setter sweep. **No other next target proposed.** This is an address/relationship anchor only, not a complete analysis of `0x0084E860`.

## Appendix A — complete original retail machine block `0x0084E800–0x0084E858`

```asm
0084e800: 55                    push   ebp
0084e801: 8b ec                 mov    ebp,esp
0084e803: 56                    push   esi
0084e804: 8b 75 08              mov    esi,DWORD PTR [ebp+0x8]
0084e807: 80 7e 04 00           cmp    BYTE PTR [esi+0x4],0x0
0084e80b: 74 31                 je     0x84e83e
0084e80d: 57                    push   edi
0084e80e: 8b 7d 0c              mov    edi,DWORD PTR [ebp+0xc]
0084e811: 83 bc be 08 19 00 00 00 cmp DWORD PTR [esi+edi*4+0x1908],0x0
0084e819: 74 0f                 je     0x84e82a
0084e81b: 8b 84 be 08 19 00 00 mov eax,DWORD PTR [esi+edi*4+0x1908]
0084e822: 8b 08                 mov ecx,DWORD PTR [eax]
0084e824: 8b 51 04              mov edx,DWORD PTR [ecx+0x4]
0084e827: 50                   push   eax
0084e828: ff d2                call   edx
0084e82a: 8b 84 be 08 19 00 00 mov eax,DWORD PTR [esi+edi*4+0x1908]
0084e831: 8b 4d 10             mov    ecx,DWORD PTR [ebp+0x10]
0084e834: 5f                   pop    edi
0084e835: 89 01                mov    DWORD PTR [ecx],eax
0084e837: 33 c0                xor    eax,eax
0084e839: 5e                   pop    esi
0084e83a: 5d                   pop    ebp
0084e83b: c2 0c 00             ret    0xc
0084e83e: 8b 45 10             mov    eax,DWORD PTR [ebp+0x10]
0084e841: 8b 76 08             mov    esi,DWORD PTR [esi+0x8]
0084e844: 8b 4d 0c             mov    ecx,DWORD PTR [ebp+0xc]
0084e847: 8b 16                mov    edx,DWORD PTR [esi]
0084e849: 8b 92 00 01 00 00    mov    edx,DWORD PTR [edx+0x100]
0084e84f: 50                   push   eax
0084e850: 51                   push   ecx
0084e851: 56                   push   esi
0084e852: ff d2                call   edx
0084e854: 5e                   pop    esi
0084e855: 5d                   pop    ebp
0084e856: c2 0c 00             ret    0xc
```

## Appendix B — constructor and publication evidence (only relevant original byte anchors)

```asm
00850109: c7 06 a8 bb b1 00     mov DWORD PTR [esi],0xb1bba8
0085010f: 89 46 08              mov DWORD PTR [esi+0x8],eax
00850176: c6 46 04 00           mov BYTE PTR [esi+0x4],0x0
00833095: 8b 17                 mov edx,DWORD PTR [edi]
00833097: 8d 8e 7c 1f 00 00     lea ecx,[esi+0x1f7c]
0083309d: 52                    push edx
0083309e: e8 1d b2 01 00        call 0x84e2c0
0084e2dd: 89 46 08              mov DWORD PTR [esi+0x8],eax
008330b1: 8d 86 7c 1f 00 00     lea eax,[esi+0x1f7c]
008330b7: 89 86 78 04 00 00     mov DWORD PTR [esi+0x478],eax
```

## Appendix C — original PE vtable cells and next-target initial bytes

```text
.rdata VA 0x00B1BCA8: 00 e8 84 00 → 0x0084E800  (primary adapter +0x100)
.rdata VA 0x00B1BCAC: 60 e8 84 00 → 0x0084E860  (primary adapter +0x104)
```

```asm
0084e860: 55                    push   ebp
0084e861: 8b ec                 mov    ebp,esp
0084e863: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
0084e866: 80 78 04 00           cmp    BYTE PTR [eax+0x4],0x0
0084e86a: 8b 55 10              mov    edx,DWORD PTR [ebp+0x10]
0084e86d: 74 3e                 je     0x84e8ad
0084e86f: 8b 4d 0c              mov    ecx,DWORD PTR [ebp+0xc]
0084e872: 89 94 88 08 19 00 00 mov    DWORD PTR [eax+ecx*4+0x1908],edx
```

**No code changes, runtime changes, replay, PR, or source edits.** Only the Markdown report is added to `work/process-reports`.
