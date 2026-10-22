# Process 1b — bounded original UI setup cleanup 0x00508E40

**Date:** 2026-10-22. **Binary:** Need for Speed SHIFT PC retail 1.02, original PE32 x86, ImageBase `0x00400000`. **Verified SHA-256 of original `/mnt/data/SHIFT.exe`:** `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Complete helper instruction bytes and bounded caller callsite were independently checked by GNU `objdump -D -Mintel -w` against the SHA-matched original retail PE (see Appendices A and B).

**Strict scope:** only `0x00508E40–0x00508E65` and the caller's direct `0x00474D7F` dispatch in the previously reported `0x00508F00 → 0x00474D70` setup path. Identify the nested `0x0064F250` call boundary by instructions/ABI, **without** exploring that callee's body. No other callee deep-dives, global caller/writer/vtable sweep, new replay, source code/runtime/P-code/renderer/guest-state modification or forced state. Existing v791 observation is not a new runtime claim.

## 1. Entry ABI and exact call relationship

The immediate known callsite is `0x00474D7F` inside setup body `0x00474D70`. Its own caller arrived through five-byte tail-jump thunk `0x00508F00`, with receiver `ECX=O=original owner object S+4` and another setup argument `EDX=A`. Before this cleanup call, the setup body:
- saves `ESI=O` using `MOV ESI,ECX` at `0x00474D74`;
- reads **`DWORD[O+0x30]`** at `0x00474D76` and compares it with zero;
- pushes EDI at `0x00474D7A` to save a callee-saved register (not an outgoing method argument);
- copies incoming `EDX=A` into EDI at `0x00474D7B`; the direct helper call is reached only if the earlier `JE` is **not taken**, i.e. on a nonzero old `O+0x30`.

```asm
00474d76: 83 7e 30 00           cmp    DWORD PTR [esi+0x30],0x0
00474d7a: 57                    push   edi
00474d7b: 8b fa                 mov    edi,edx
00474d7d: 74 29                 je     0x474da8
00474d7f: e8 bc 40 09 00        call   0x508e40
00474d84: eb 22                 jmp    0x474da8
```

**Precise inbound register state at `0x00508E40`, for this callsite:**
- **`ECX=O`**, unchanged from setup body's original register receiver; this cleanup routine uses it as its sole byte-proven receiver/input.
- **`EDX=A`** is physically still the setup body's incoming second register value, but **is overwritten by `0x00508E44: MOV EDX,DWORD[O+0x30]` before being used by the cleanup**. It is therefore **not a semantic input** of this helper's observed implementation.
- **No newly pushed explicit stack arguments** are prepared for `CALL 0x00508E40`. The setup body's existing saved EDI/ESI and stack locals must not be mistaken for cleanup arguments.
- `CALL` occupies **5 bytes** and pushes **return address `0x00474D84`**. No return-address change by a thunk: this is a **direct** call to `0x00508E40`.
- The helper itself pushes EBX and ESI; ends `POP ESI; POP EBX; RET` at `0x00508E63–0x00508E65`. **Plain `RET` (`C3`), no `RET imm16` and no extra caller-argument cleanup.** On normal return, the caller executes `0x00474D84: JMP 0x00474DA8` before making replacement stores later in its own body.

This is the **register-receiver / no-explicit-stack-argument** ABI proven by bytes. It does **not** establish a typed C++ method name, COM interface, or any required additional parameter.

## 2. Complete code path, direct reads, branches and nested-call ABI

The **entire original 17-instruction function** is reproduced unchanged in Appendix A. It contains only one nested direct call and no other outgoing calls or loops.

### 2.1 First guard and zero constant

```asm
00508e40: 53                    push   ebx
00508e41: 56                    push   esi
00508e42: 8b f1                 mov    esi,ecx
00508e44: 8b 56 30              mov    edx,DWORD PTR [esi+0x30]
00508e47: 33 db                 xor    ebx,ebx
00508e49: 3b d3                 cmp    edx,ebx
00508e4b: 74 10                 je     0x508e5d
```

Here **`ESI=O`**, **`EDX=DWORD[O+0x30]`**, **`EBX=0`**. `CMP EDX,EBX` determines the **inner** zero test:
- **If `DWORD[O+0x30]==0`**: direct `JE 0x00508E5D` skips the byte test, nested call and write to `O+0x30`, but **still clears O+0x34 and O+0x38**.
- **If `DWORD[O+0x30]!=0`**: follow through to the second guard.

The **known outer callsite** itself only invokes cleanup when its prior `DWORD[O+0x30]` read was nonzero. Thus, in the ordinary uninterrupted same-thread path with no concurrent mutation between tests, the inner zero branch is not taken. Nevertheless it **exists in the complete target function** and is documented rather than omitted or declared globally unreachable. Its availability for other callers or due to intervening external mutation is not investigated.

### 2.2 Second guard and nested direct call

```asm
00508e4d: 38 5e 3c              cmp    BYTE PTR [esi+0x3c],bl
00508e50: 75 08                 jne    0x508e5a
00508e52: 8b 4e 38              mov    ecx,DWORD PTR [esi+0x38]
00508e55: e8 f6 63 14 00        call   0x64f250
```

With `EBX=0`, the inner **byte** comparison is `BYTE[O+0x3C]==0`.
- **If `BYTE[O+0x3C]!=0`**: `JNE 0x00508E5A`, **skip `0x0064F250`**, then write zero to `O+0x30`.
- **If `BYTE[O+0x3C]==0`**: **`ECX=DWORD[O+0x38]`** at `0x00508E52`, then **direct `CALL 0x0064F250`** from `0x00508E55`, return address **`0x00508E5A`**. **No stack arguments are newly pushed** by `0x00508E40` for this call. The immediate receiver/input candidate is **the previous `O+0x38` field value, not `O`**.
- At the nested callsite **EDX still contains the previous `DWORD[O+0x30]`** loaded at `0x00508E44`; whether that register is a meaningful input to `0x0064F250` is **unknown** without examining its body. EBX=0, ESI=O, EAX is not set by this cleanup before the nested call. Do not assert this is a release/free/destructor or specify its semantic return.
- Following a normal nested return, there is **no TEST/CMP of EAX**, no conditional path on its return value; execution falls through to the unconditional member-field clearing sequence.

The **exact nested-call condition** within this function is:

`(DWORD[O+0x30] != 0) && (BYTE[O+0x3C] == 0)`.

The enclosing setup call adds its own old `O+0x30 != 0` gate for cleanup to be entered at all. The nested method can mutate memory in ways not enumerated by this helper's direct stores; **nothing in these bytes proves it touches O or even that it was invoked in v791**.

### 2.3 Exact direct stores, widths, and exit

```asm
00508e5a: 89 5e 30              mov    DWORD PTR [esi+0x30],ebx
00508e5d: 89 5e 34              mov    DWORD PTR [esi+0x34],ebx
00508e60: 89 5e 38              mov    DWORD PTR [esi+0x38],ebx
00508e63: 5e                    pop    esi
00508e64: 5b                    pop    ebx
00508e65: c3                    ret
```

**EBX is exactly 0 on the stores**. Fields referenced directly in this full function:

| EIP | Operation (relative to initial O) | When |
|---|---|---|
| `0x00508E44` | **READ DWORD[O+0x30]** | Always |
| `0x00508E4D` | **READ BYTE[O+0x3C]** | Only when old `O+0x30 != 0` |
| `0x00508E52` | **READ DWORD[O+0x38]** | Only when old `O+0x30!=0` AND byte `O+0x3C==0` |
| `0x00508E5A` | **WRITE DWORD[O+0x30]=0** | Only when inner old `O+0x30!=0` |
| `0x00508E5D` | **WRITE DWORD[O+0x34]=0** | All normal paths |
| `0x00508E60` | **WRITE DWORD[O+0x38]=0** | All normal paths |

**No direct write** occurs to `BYTE[O+0x3C]`. This byte is **read** and controls whether the nested helper is invoked, but remains unchanged by direct machine instructions here. The helper has **no local store to EAX or local EAX arithmetic**: if `0x0064F250` is skipped, EAX is preserved from entry, and if it is called, its resulting EAX passes through. Thus the full EAX returned by cleanup is **not locally assigned a specific value** or type; the caller never tests it.

### 2.4 Minimal flow (strictly descriptive; not game source)

```c
// O = incoming ECX; incoming EDX unused before being overwritten
uint32_t previous = *(uint32_t *)(O+0x30);
if (previous != 0) {
    if (*(uint8_t *)(O+0x3C) == 0) {
        // ECX = *(uint32_t *)(O+0x38);
        // EDX still previous; no explicit PUSH arguments
        call_0064F250(/* ECX = old O+0x38; EDX = old O+0x30 */);
    }
    *(uint32_t *)(O+0x30) = 0;
}
*(uint32_t *)(O+0x34) = 0;
*(uint32_t *)(O+0x38) = 0;
// Return EAX is not defined by any local write; plain RET.
```

This is the direct-instruction flow only, not a claim that nested method is side-effect-free or that the memory values remain stable under concurrent execution.

## 3. No direct path to vptr, +0x14 list count, +0x2D readiness or +0x3C store

Within the complete `0x00508E40–0x00508E65`:

- **`DWORD[O]` vptr**: **not read or written**. The helper receives O from ECX but **does not itself read its vtable or install a new vptr**.
- **`DWORD[O+0x14]`**: **not read or written**. This is the later insertion-maintained list-count field observed as **9** in v791 and tested by the previously reported guard.
- **`BYTE[O+0x2D]`**: **not read or written**. The later readiness-associated zero store is in **`0x005092F0`**, not here.
- **`BYTE[O+0x3C]`**: **read for comparison only; no direct write**.
- **Direct writes only** to **DWORD[O+0x30]**, **DWORD[O+0x34]**, **DWORD[O+0x38]**, all to zero with the conditionality shown above.

This absence applies strictly to **direct addressing within the audited cleanup helper**. The nested `0x0064F250` receives **ECX=old O+0x38**, a potentially aliased pointer; without its body or independent runtime memory provenance, its possible writes, object destruction and alias effects are **unresolved**. No claim that it cannot indirectly modify O, vptr, count or readiness is justified. The supplied finite replay supplies no event proving this conditional cleanup function, let alone nested call, executed.

## 4. Relation to replacement stores in outer setup body

The already byte-verified parent setup `0x00474D70` has a **first guard `DWORD[O+0x30]!=0`** and calls cleanup only when that guard is true. After this call's normal return, parent continues at `0x00474DA8`; it optionally obtains a zero-fallback value from `0x0062E1A0` and then performs:

```asm
00474dc7: 89 46 38              mov    DWORD PTR [esi+0x38],eax
00474dca: 8b 45 08              mov    eax,DWORD PTR [ebp+0x8]
00474dcd: 89 7e 30              mov    DWORD PTR [esi+0x30],edi
00474dd0: 5f                    pop    edi
00474dd1: 89 46 34              mov    DWORD PTR [esi+0x34],eax
00474dd4: c6 46 3c 01           mov    BYTE PTR [esi+0x3c],0x1
00474dd8: 5e                    pop    esi
00474dd9: 5d                    pop    ebp
00474dda: c2 08 00              ret    0x8
```

Thus the **outer setup function's own instructions** replace old fields **+0x30/+0x34/+0x38** and set **+0x3C to 1** after cleanup has zeroed previous +0x30/+0x34/+0x38. Calling the helper "old-state cleanup" is justified **by this ordering and direct clear operations**, not by any source symbol or verified ownership/destructor contract. The cleanup's returned EAX is **not used**: parent at `0x00474DA8` unconditionally loads `EAX=[EBP+0xC]`, replacing whatever EAX the cleanup might have forwarded.

The outer routine's new values are not proof that its nested helper was run, nor that the old state was successfully released. This code alone provides **no direct causal link** to later **`O+0x14=9`**, to **`BYTE[O+0x2D]=0`**, or to a subsequent renderer/menu readiness condition.

## 5. Evidence separation and finite runtime limit

**Original retail PE facts (directly verified):** original SHA; direct callsite **`0x00474D7F → 0x00508E40`** and return address `0x00474D84`; exact 17 original decoded instructions in Appendix A; ECX=O; incoming EDX overwritten with `[O+0x30]`; no explicit stack args; branch on old +0x30, then byte +0x3C; conditional outgoing **`CALL 0x0064F250`** with ECX=old `DWORD[O+0x38]`; conditional zero store +0x30 and unconditional zero stores +0x34/+0x38; preserved EBX/ESI; plain RET; unconstrained EAX return.

**Runtime supplied in context, not reproduced here:** v791 was a bounded replay of the **original PE under Linux P-code guest execution**, with count `DWORD[O+0x14]=9`, later guard AL=0 and writer zero store `BYTE[O+0x2D]=0`. No provided trace proves **`0x00508E40` was reached**, whether its old +0x30 was nonzero, or whether `0x0064F250` ran; thus **no live cleanup occurrence** is claimed. No native Windows/Wine launch or rendered menu/race is claimed; the previous replay did not establish guest draw translation or retail rendering.

**Inference/unknown:** source C++ type/interface, resource ownership for +0x30/+0x38, byte +0x3C meaning, callee `0x0064F250` behavior and its possible indirect effects, whether this cleanup contributes to or repairs readiness. No global state-path inference follows from this local code.

## 6. Exactly one next evidence-backed target

**`0x0064F250` — the single direct conditional nested callee** of `0x00508E40`, called at **`0x00508E55`** with **`ECX=DWORD[O+0x38]`** and **no pushed arguments**, when **`DWORD[O+0x30]!=0 && BYTE[O+0x3C]==0`**. This is the only next target justified by the present bounded evidence: a separately assigned narrow analysis could determine if it actually mutates the old +0x38-associated state or has observable side effects; **its body was not examined here**. The exact role and live reachability remain unresolved.

## Appendix A — complete original retail helper 0x00508E40–0x00508E65

```asm
00508e40: 53                    push   ebx
00508e41: 56                    push   esi
00508e42: 8b f1                 mov    esi,ecx
00508e44: 8b 56 30              mov    edx,DWORD PTR [esi+0x30]
00508e47: 33 db                 xor    ebx,ebx
00508e49: 3b d3                 cmp    edx,ebx
00508e4b: 74 10                 je     0x508e5d
00508e4d: 38 5e 3c              cmp    BYTE PTR [esi+0x3c],bl
00508e50: 75 08                 jne    0x508e5a
00508e52: 8b 4e 38              mov    ecx,DWORD PTR [esi+0x38]
00508e55: e8 f6 63 14 00        call   0x64f250
00508e5a: 89 5e 30              mov    DWORD PTR [esi+0x30],ebx
00508e5d: 89 5e 34              mov    DWORD PTR [esi+0x34],ebx
00508e60: 89 5e 38              mov    DWORD PTR [esi+0x38],ebx
00508e63: 5e                    pop    esi
00508e64: 5b                    pop    ebx
00508e65: c3                    ret
```

## Appendix B — narrow PE parent caller boundary (original bytes)

```asm
00474d70: 55                    push   ebp
00474d71: 8b ec                 mov    ebp,esp
00474d73: 56                    push   esi
00474d74: 8b f1                 mov    esi,ecx
00474d76: 83 7e 30 00           cmp    DWORD PTR [esi+0x30],0x0
00474d7a: 57                    push   edi
00474d7b: 8b fa                 mov    edi,edx
00474d7d: 74 29                 je     0x474da8
00474d7f: e8 bc 40 09 00        call   0x508e40
00474d84: eb 22                 jmp    0x474da8
```

**Publication:** Markdown report only in `process-reports/`; no source/runtime/P-code/renderer/guest-state edits, replay, live-run claims or PR.
