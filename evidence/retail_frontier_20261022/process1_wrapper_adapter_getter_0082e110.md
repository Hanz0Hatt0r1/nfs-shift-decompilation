# Process 1 — retail wrapper→adapter getter 0x0082E110: bounded immediate-consumer provenance

**Date:** 2026-10-22. **PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86; ImageBase `0x00400000`; verified SHA-256 of original `/mnt/data/SHIFT.exe`: `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

**Scope:** immediate consumers of the exact target `0x0082E110` in the full original PE GNU objdump. The earlier BeginStateBlock caller audit [commit `89c82f5146244d3cc3528ace85d1449611b508ae`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process1b-beginstateblock-callsite-0084fbc0.md) is the closed predecessor, not repeated here. No runtime replay, P-code/code/renderer modifications, forcing of guest fields, or global byte+4 setter sweep.

## Conclusion

**The getter has 187 exact direct `CALL rel32` consumers in linear retail objdump, and zero of their immediate post-call windows loads a `+0xF0` slot.** The returned pointer has positive adapter provenance on the enabled branch, but **no examined immediate consumer proves an invocation of primary adapter virtual slot `+0xF0`**, nor a direct write of nonzero `BYTE[adapter+4]` before such a call. This is **bounded negative evidence for *immediate* consumption**, not an assertion that BeginStateBlock is globally unreachable. A pointer can leave the local window via a stack local, register or argument; absence of a nearby opcode is not whole-program alias analysis.

## Exact getter contract and pointer identity

The full 10-instruction original byte block is in Appendix A.

- `ECX=wrapper`; no stack arguments, plain `RET`. Ghidra's `__fastcall` descriptor for the one ECX argument is compatible with bytes, but *not* proof of a C++ source declaration.
- `0x0082E110`: `CMP BYTE [ECX+0x5E8],0`. **Nonzero** → `0x0082E119: EAX=DWORD[wrapper+0x478]`; return EAX through `0x0082E11F`. This is an **unconditional raw pointer load** on that branch; the helper does not validate null or read the adapter's vptr itself.
- **Zero** → `0x0082E120–0x0082E12D`: read `wrapper.vptr+0x2E8`, load **EDX=0xA**, invoke virtual error/report callback with **ECX still the wrapper in the ordinary entry path**, then `0x0082E12F: XOR EAX,EAX` and `RET`. Return is **0 regardless of callback EAX**, although callback side effects are not bounded here. Treat no-hit/null branch separately from successful pointer provenance.
- The previously verified constructor/device-initialization chain writes **`[wrapper+0x478]=wrapper+0x1F7C`** at `0x008330B7` and **`BYTE[wrapper+0x5E8]=1`** at `0x008330D0` on the appropriate initialization path. The embedded adapter initializer `0x00850100` sets primary vptr `0x00B1BBA8` at `0x00850109`; original PE `.rdata` `DWORD[0x00B1BC98]=0x0084FBC0` at primary slot **+0xF0**. Thus for that specific initialized wrapper **getter EAX=wrapper+0x1F7C** and **`DWORD[EAX]` is the adapter vptr at initialization**. No dynamic vptr-invariance is assumed across unknown writes.

To establish an actual Begin-wrapper call in a consumer, **all** of the following are needed: `A=return(getter)`, `DWORD[A]=0x00B1BBA8` at the call, `F=DWORD[DWORD[A]+0xF0]=0x0084FBC0`, **`PUSH A; CALL F`**, since the wrapper's receiver is a **stack argument** (`[EBP+8]`, `RET 4`) rather than a `__thiscall` ECX receiver. None of the immediate windows shows this chain.

## Bounded search coverage and reproducible exact result

Original binary SHA verified, full `SHIFT_objdump_full.txt` (165 MB). Searched executable GNU linear opcode lines, not merely named symbols or one .text range; `0x0082E110` entry verified byte-for-byte. Direct xrefs matched **only** the exact mnemonic target `CALL 0x82E110`: **187 matches**, first **0x0082E4B9**, last **0x00863854**. Full-PE literal DWORD needle `10 E1 82 00` occurs **0 times**, so there is no directly encoded static pointer to this function in the raw file; this cannot exclude computed call targets, thunks or code overlays. Direct `JMP rel32` to the getter in linear objdump: **0**.

For **each of the 187 direct CALL sites**, starting at the next decoded instruction: inspect the next **12 decoded rows**; additionally scan *all linear decoded instructions whose starts fall within 160 bytes after the callsite*. **Zero windows** contain a positive `[register+0xF0]` virtual slot access. This stricter negative is about the **literal +0xF0 expression**; it does not exclude a computed offset or a virtual pointer propagated to a more distant function. The scan intentionally includes calls that then return, branch, invoke other functions, or consume the pointer via other vtable slots; it does **not** prove each window follows one executable CFG path, nor track alias through callee calls.

An exact inventory of all 187 direct callsite guest EIPs is in Appendix F; counts and range can be reproduced by:

```sh
grep -E '^[[:space:]]*[0-9a-f]+:[[:space:]]+[0-9a-f ]+[[:space:]]+call[[:space:]]+0x82e110[[:space:]]*$' SHIFT_objdump_full.txt
```

For each match, inspect subsequent 12 opcode rows and/or addresses `site<VA<=site+160`, checking `+0xF0` and corresponding pointer source; this is a *bounded literal-operand scan*. It is not a global setter survey.

### Full-byte representative immediate consumers

**A. `0x0082E4A0–0x0082E508`** (Appendix B): two mutually exclusive getter calls **0x0082E4B9 and 0x0082E4DF**. After each, `ECX=[EAX]` obtains adapter vptr; `F=[ECX+0xE4]`, two other DWORDs are pushed followed by `PUSH EAX`, then `CALL F` at **0x0082E4D5 / 0x0082E4FB**. This is **positive immediate adapter-vptr use with the correct explicit stack receiver**, but for **slot +0xE4**, not +0xF0. Do not reinterpret this as BeginStateBlock due to superficial similarity.

**B. `0x0082FAB0–0x0082FAE0`** (Appendix C): `0x0082FAB6` gets adapter. After a byte comparison/optional write to **wrapper `+0x711`**, it fetches adapter vptr **+0xE4** and invokes with `PUSH EAX`, `PUSH 0x8`, `PUSH EBX`. The byte writer `[ESI+0x711]` is **wrapper state**, not `BYTE[adapter+4]`; it cannot be promoted to the nonzero adapter flag source.

**C. `0x0084D7F0–0x0084D92E`** (Appendix D): `0x0084D7FB: ECX=[0x00C26058]`; `0x0084D801: CALL 0x0082E110`; **`0x0084D806: [EBP-4]=EAX`**. At `0x0084D836–0x0084D84D` the same stack-local pointer is moved into **ECX** and passed to the *direct helper* **0x0084D1A0** at `0x0084D84D`. Further branches repeat this with varied stack arguments. The only proven local receiver identity is **the getter-returned adapter**, not any different object, and this block contains no `+0xF0` call.

**D. Downstream `0x0084D1A0–0x0084D245`** (Appendix E): the helper called from C starts **`0x0084D1A6: EAX=[ECX]`; `0x0084D1A9: EAX=[vptr+0x5C]`** then at **0x0084D1D0** calls it with ECX as the explicit stack receiver and eight additional DWORD pushes; it consumes the returned resource pointer via further virtual slots **+0x4C, +0x50, +0x08**. This proves **one bounded transitive path beyond the immediate getter consumer uses +0x5C rather than +0xF0**; it is not a universal exclusion of other transitive callers.

## Confidence ledger

**PE-byte proven:** target instruction bytes and conditional return behavior; prior constructor/vptr identity for ordinarily initialized wrapper/adapter; 187 exact direct rel32 sites in the full original objdump; no literal target DWORD; no immediately decoded +0xF0 operand within specified two windows for any of 187; full original bytes for four inspected consumer/function bodies showing +0xE4 and +0x5C uses and one concrete `EAX→[EBP-4]→ECX` transfer.

**Source-derived runtime only:** previously supplied v757 P-code replay selected 0x0084FBC0 and related Draw targets with `events=[]` during 360 host frames, nontruncated. No new replay was made. It does not prove that getter was called or that BeginStateBlock could never execute in other UI/device states.

**Unknown:** indirect and computed callers of getter; cross-function alias propagation outside inspected examples; any +0xF0 dynamic dispatch beyond 160 bytes/12 decoded rows; whether adapter pointer is stored in longer-lived tables or modified after constructor; all dynamic nonzero BYTE[adapter+4] writers (excluded by scope). **Result does not close any P1 global reachability gate**.

## Exactly one next bounded target

**`0x0084D1A0`** — the concrete first callee to which caller **0x0084D7F0** forwards the getter-returned adapter in ECX. A subsequent receiver-proven audit could trace any alias it emits to caller outputs or resource objects; its *immediate* slot +0x5C has been identified here, with no assertion that downstream resources have adapter identity. This maintains a precise pointer join rather than performing another global +0xF0 offset sweep.

## Appendix — full original retail opcode blocks, instruction bytes included

### A. Getter `0x0082E110–0x0082E131`

```asm
82e110:	80 b9 e8 05 00 00 00 	cmp    BYTE PTR [ecx+0x5e8],0x0
  82e117:	74 07                	je     0x82e120
  82e119:	8b 81 78 04 00 00    	mov    eax,DWORD PTR [ecx+0x478]
  82e11f:	c3                   	ret
  82e120:	8b 01                	mov    eax,DWORD PTR [ecx]
  82e122:	8b 80 e8 02 00 00    	mov    eax,DWORD PTR [eax+0x2e8]
  82e128:	ba 0a 00 00 00       	mov    edx,0xa
  82e12d:	ff d0                	call   eax
  82e12f:	33 c0                	xor    eax,eax
  82e131:	c3                   	ret
```

### B. Full consumer `0x0082E4A0–0x0082E508`

```asm
82e4a0:	56                   	push   esi
  82e4a1:	8b f1                	mov    esi,ecx
  82e4a3:	80 be 50 13 00 00 00 	cmp    BYTE PTR [esi+0x1350],0x0
  82e4aa:	74 59                	je     0x82e505
  82e4ac:	80 3d 00 e2 b8 00 00 	cmp    BYTE PTR ds:0xb8e200,0x0
  82e4b3:	74 50                	je     0x82e505
  82e4b5:	84 d2                	test   dl,dl
  82e4b7:	74 26                	je     0x82e4df
  82e4b9:	e8 52 fc ff ff       	call   0x82e110
  82e4be:	8b 96 5c 13 00 00    	mov    edx,DWORD PTR [esi+0x135c]
  82e4c4:	8b 08                	mov    ecx,DWORD PTR [eax]
  82e4c6:	52                   	push   edx
  82e4c7:	8b 96 54 13 00 00    	mov    edx,DWORD PTR [esi+0x1354]
  82e4cd:	52                   	push   edx
  82e4ce:	50                   	push   eax
  82e4cf:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  82e4d5:	ff d0                	call   eax
  82e4d7:	85 c0                	test   eax,eax
  82e4d9:	74 2a                	je     0x82e505
  82e4db:	32 c0                	xor    al,al
  82e4dd:	5e                   	pop    esi
  82e4de:	c3                   	ret
  82e4df:	e8 2c fc ff ff       	call   0x82e110
  82e4e4:	8b 96 60 13 00 00    	mov    edx,DWORD PTR [esi+0x1360]
  82e4ea:	8b 08                	mov    ecx,DWORD PTR [eax]
  82e4ec:	52                   	push   edx
  82e4ed:	8b 96 58 13 00 00    	mov    edx,DWORD PTR [esi+0x1358]
  82e4f3:	52                   	push   edx
  82e4f4:	50                   	push   eax
  82e4f5:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  82e4fb:	ff d0                	call   eax
  82e4fd:	85 c0                	test   eax,eax
  82e4ff:	74 04                	je     0x82e505
  82e501:	32 c0                	xor    al,al
  82e503:	5e                   	pop    esi
  82e504:	c3                   	ret
  82e505:	b0 01                	mov    al,0x1
  82e507:	5e                   	pop    esi
  82e508:	c3                   	ret
```

### C. Full consumer `0x0082FAB0–0x0082FAE0`

```asm
82fab0:	53                   	push   ebx
  82fab1:	56                   	push   esi
  82fab2:	8a da                	mov    bl,dl
  82fab4:	8b f1                	mov    esi,ecx
  82fab6:	e8 55 e6 ff ff       	call   0x82e110
  82fabb:	38 9e 11 07 00 00    	cmp    BYTE PTR [esi+0x711],bl
  82fac1:	74 1b                	je     0x82fade
  82fac3:	88 9e 11 07 00 00    	mov    BYTE PTR [esi+0x711],bl
  82fac9:	8b 08                	mov    ecx,DWORD PTR [eax]
  82facb:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  82fad1:	f6 db                	neg    bl
  82fad3:	1b db                	sbb    ebx,ebx
  82fad5:	83 c3 03             	add    ebx,0x3
  82fad8:	53                   	push   ebx
  82fad9:	6a 08                	push   0x8
  82fadb:	50                   	push   eax
  82fadc:	ff d2                	call   edx
  82fade:	5e                   	pop    esi
  82fadf:	5b                   	pop    ebx
  82fae0:	c3                   	ret
```

### D. Full consumer `0x0084D7F0–0x0084D92E`

```asm
84d7f0:	55                   	push   ebp
  84d7f1:	8b ec                	mov    ebp,esp
  84d7f3:	83 ec 08             	sub    esp,0x8
  84d7f6:	53                   	push   ebx
  84d7f7:	56                   	push   esi
  84d7f8:	57                   	push   edi
  84d7f9:	8b f9                	mov    edi,ecx
  84d7fb:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  84d801:	e8 0a 09 fe ff       	call   0x82e110
  84d806:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84d809:	33 c0                	xor    eax,eax
  84d80b:	39 47 4c             	cmp    DWORD PTR [edi+0x4c],eax
  84d80e:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84d811:	0f 8e f2 00 00 00    	jle    0x84d909
  84d817:	8d 77 6c             	lea    esi,[edi+0x6c]
  84d81a:	8d 5f 1c             	lea    ebx,[edi+0x1c]
  84d81d:	eb 03                	jmp    0x84d822
  84d81f:	90                   	nop
  84d820:	33 c0                	xor    eax,eax
  84d822:	89 03                	mov    DWORD PTR [ebx],eax
  84d824:	89 43 08             	mov    DWORD PTR [ebx+0x8],eax
  84d827:	89 43 04             	mov    DWORD PTR [ebx+0x4],eax
  84d82a:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
  84d82d:	39 46 f8             	cmp    DWORD PTR [esi-0x8],eax
  84d830:	74 28                	je     0x84d85a
  84d832:	8d 4b f0             	lea    ecx,[ebx-0x10]
  84d835:	51                   	push   ecx
  84d836:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84d839:	56                   	push   esi
  84d83a:	8d 56 fc             	lea    edx,[esi-0x4]
  84d83d:	52                   	push   edx
  84d83e:	8b 57 50             	mov    edx,DWORD PTR [edi+0x50]
  84d841:	53                   	push   ebx
  84d842:	6a 01                	push   0x1
  84d844:	6a 02                	push   0x2
  84d846:	6a 1c                	push   0x1c
  84d848:	50                   	push   eax
  84d849:	8b 47 54             	mov    eax,DWORD PTR [edi+0x54]
  84d84c:	50                   	push   eax
  84d84d:	e8 4e f9 ff ff       	call   0x84d1a0
  84d852:	85 c0                	test   eax,eax
  84d854:	0f 84 c5 00 00 00    	je     0x84d91f
  84d85a:	83 7e 04 00          	cmp    DWORD PTR [esi+0x4],0x0
  84d85e:	74 2f                	je     0x84d88f
  84d860:	8d 4b f4             	lea    ecx,[ebx-0xc]
  84d863:	51                   	push   ecx
  84d864:	8b 4f 5c             	mov    ecx,DWORD PTR [edi+0x5c]
  84d867:	8d 56 0c             	lea    edx,[esi+0xc]
  84d86a:	52                   	push   edx
  84d86b:	8b 57 58             	mov    edx,DWORD PTR [edi+0x58]
  84d86e:	8d 46 08             	lea    eax,[esi+0x8]
  84d871:	50                   	push   eax
  84d872:	8d 43 04             	lea    eax,[ebx+0x4]
  84d875:	50                   	push   eax
  84d876:	6a 01                	push   0x1
  84d878:	6a 02                	push   0x2
  84d87a:	6a 1c                	push   0x1c
  84d87c:	6a 00                	push   0x0
  84d87e:	51                   	push   ecx
  84d87f:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84d882:	e8 19 f9 ff ff       	call   0x84d1a0
  84d887:	85 c0                	test   eax,eax
  84d889:	0f 84 90 00 00 00    	je     0x84d91f
  84d88f:	83 7e 10 00          	cmp    DWORD PTR [esi+0x10],0x0
  84d893:	74 2b                	je     0x84d8c0
  84d895:	8d 53 f8             	lea    edx,[ebx-0x8]
  84d898:	52                   	push   edx
  84d899:	8b 57 5c             	mov    edx,DWORD PTR [edi+0x5c]
  84d89c:	8d 46 18             	lea    eax,[esi+0x18]
  84d89f:	50                   	push   eax
  84d8a0:	8d 4e 14             	lea    ecx,[esi+0x14]
  84d8a3:	51                   	push   ecx
  84d8a4:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84d8a7:	8d 43 08             	lea    eax,[ebx+0x8]
  84d8aa:	50                   	push   eax
  84d8ab:	6a 01                	push   0x1
  84d8ad:	6a 02                	push   0x2
  84d8af:	6a 1c                	push   0x1c
  84d8b1:	6a 00                	push   0x0
  84d8b3:	52                   	push   edx
  84d8b4:	8b 57 58             	mov    edx,DWORD PTR [edi+0x58]
  84d8b7:	e8 e4 f8 ff ff       	call   0x84d1a0
  84d8bc:	85 c0                	test   eax,eax
  84d8be:	74 5f                	je     0x84d91f
  84d8c0:	83 7e 1c 00          	cmp    DWORD PTR [esi+0x1c],0x0
  84d8c4:	74 2b                	je     0x84d8f1
  84d8c6:	8d 43 fc             	lea    eax,[ebx-0x4]
  84d8c9:	50                   	push   eax
  84d8ca:	8d 4e 24             	lea    ecx,[esi+0x24]
  84d8cd:	51                   	push   ecx
  84d8ce:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84d8d1:	8d 56 20             	lea    edx,[esi+0x20]
  84d8d4:	52                   	push   edx
  84d8d5:	8b 57 50             	mov    edx,DWORD PTR [edi+0x50]
  84d8d8:	8d 43 0c             	lea    eax,[ebx+0xc]
  84d8db:	50                   	push   eax
  84d8dc:	8b 47 54             	mov    eax,DWORD PTR [edi+0x54]
  84d8df:	6a 01                	push   0x1
  84d8e1:	6a 02                	push   0x2
  84d8e3:	6a 1c                	push   0x1c
  84d8e5:	6a 00                	push   0x0
  84d8e7:	50                   	push   eax
  84d8e8:	e8 b3 f8 ff ff       	call   0x84d1a0
  84d8ed:	85 c0                	test   eax,eax
  84d8ef:	74 2e                	je     0x84d91f
  84d8f1:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84d8f4:	83 c0 01             	add    eax,0x1
  84d8f7:	83 c3 20             	add    ebx,0x20
  84d8fa:	83 c6 30             	add    esi,0x30
  84d8fd:	3b 47 4c             	cmp    eax,DWORD PTR [edi+0x4c]
  84d900:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  84d903:	0f 8c 17 ff ff ff    	jl     0x84d820
  84d909:	8b 17                	mov    edx,DWORD PTR [edi]
  84d90b:	8b 42 18             	mov    eax,DWORD PTR [edx+0x18]
  84d90e:	8b cf                	mov    ecx,edi
  84d910:	ff d0                	call   eax
  84d912:	f6 d8                	neg    al
  84d914:	5f                   	pop    edi
  84d915:	5e                   	pop    esi
  84d916:	5b                   	pop    ebx
  84d917:	1b c0                	sbb    eax,eax
  84d919:	f7 d8                	neg    eax
  84d91b:	8b e5                	mov    esp,ebp
  84d91d:	5d                   	pop    ebp
  84d91e:	c3                   	ret
  84d91f:	8b cf                	mov    ecx,edi
  84d921:	e8 2a f9 ff ff       	call   0x84d250
  84d926:	5f                   	pop    edi
  84d927:	5e                   	pop    esi
  84d928:	33 c0                	xor    eax,eax
  84d92a:	5b                   	pop    ebx
  84d92b:	8b e5                	mov    esp,ebp
  84d92d:	5d                   	pop    ebp
  84d92e:	c3                   	ret
```

### E. Full direct pointer-consumer helper `0x0084D1A0–0x0084D245`

```asm
84d1a0:	55                   	push   ebp
  84d1a1:	8b ec                	mov    ebp,esp
  84d1a3:	83 ec 0c             	sub    esp,0xc
  84d1a6:	8b 01                	mov    eax,DWORD PTR [ecx]
  84d1a8:	56                   	push   esi
  84d1a9:	8b 40 5c             	mov    eax,DWORD PTR [eax+0x5c]
  84d1ac:	57                   	push   edi
  84d1ad:	8b 7d 08             	mov    edi,DWORD PTR [ebp+0x8]
  84d1b0:	6a 00                	push   0x0
  84d1b2:	8b f2                	mov    esi,edx
  84d1b4:	8d 55 fc             	lea    edx,[ebp-0x4]
  84d1b7:	52                   	push   edx
  84d1b8:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84d1bb:	52                   	push   edx
  84d1bc:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84d1bf:	52                   	push   edx
  84d1c0:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84d1c3:	52                   	push   edx
  84d1c4:	6a 01                	push   0x1
  84d1c6:	57                   	push   edi
  84d1c7:	56                   	push   esi
  84d1c8:	51                   	push   ecx
  84d1c9:	c7 45 fc 00 00 00 00 	mov    DWORD PTR [ebp-0x4],0x0
  84d1d0:	ff d0                	call   eax
  84d1d2:	85 c0                	test   eax,eax
  84d1d4:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84d1d7:	7c 59                	jl     0x84d232
  84d1d9:	8b 4d 1c             	mov    ecx,DWORD PTR [ebp+0x1c]
  84d1dc:	0f af f7             	imul   esi,edi
  84d1df:	0f af 75 18          	imul   esi,DWORD PTR [ebp+0x18]
  84d1e3:	8b 55 28             	mov    edx,DWORD PTR [ebp+0x28]
  84d1e6:	89 01                	mov    DWORD PTR [ecx],eax
  84d1e8:	89 32                	mov    DWORD PTR [edx],esi
  84d1ea:	8b 75 20             	mov    esi,DWORD PTR [ebp+0x20]
  84d1ed:	85 f6                	test   esi,esi
  84d1ef:	74 34                	je     0x84d225
  84d1f1:	8b 7d 24             	mov    edi,DWORD PTR [ebp+0x24]
  84d1f4:	85 ff                	test   edi,edi
  84d1f6:	74 2d                	je     0x84d225
  84d1f8:	8b 08                	mov    ecx,DWORD PTR [eax]
  84d1fa:	6a 00                	push   0x0
  84d1fc:	6a 00                	push   0x0
  84d1fe:	8d 55 f4             	lea    edx,[ebp-0xc]
  84d201:	52                   	push   edx
  84d202:	6a 00                	push   0x0
  84d204:	50                   	push   eax
  84d205:	8b 41 4c             	mov    eax,DWORD PTR [ecx+0x4c]
  84d208:	ff d0                	call   eax
  84d20a:	85 c0                	test   eax,eax
  84d20c:	7c 30                	jl     0x84d23e
  84d20e:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  84d211:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  84d214:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84d217:	89 0f                	mov    DWORD PTR [edi],ecx
  84d219:	89 16                	mov    DWORD PTR [esi],edx
  84d21b:	8b 08                	mov    ecx,DWORD PTR [eax]
  84d21d:	8b 51 50             	mov    edx,DWORD PTR [ecx+0x50]
  84d220:	6a 00                	push   0x0
  84d222:	50                   	push   eax
  84d223:	ff d2                	call   edx
  84d225:	5f                   	pop    edi
  84d226:	b8 01 00 00 00       	mov    eax,0x1
  84d22b:	5e                   	pop    esi
  84d22c:	8b e5                	mov    esp,ebp
  84d22e:	5d                   	pop    ebp
  84d22f:	c2 24 00             	ret    0x24
  84d232:	85 c0                	test   eax,eax
  84d234:	74 08                	je     0x84d23e
  84d236:	8b 08                	mov    ecx,DWORD PTR [eax]
  84d238:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  84d23b:	50                   	push   eax
  84d23c:	ff d2                	call   edx
  84d23e:	5f                   	pop    edi
  84d23f:	33 c0                	xor    eax,eax
  84d241:	5e                   	pop    esi
  84d242:	8b e5                	mov    esp,ebp
  84d244:	5d                   	pop    ebp
  84d245:	c2 24 00             	ret    0x24
```

### F. Exact list of all 187 direct getter CALL addresses in full executable objdump

This list is address-only census; **not every listed function's complete disassembly** is included, because those sites are used only to establish the bounded 160-byte/12-instruction *syntactic negative* above, not to assert the original program's transitive behavior.

```text
0082E4B9 0082E4DF 0082EAC1 0082EAE3 0082EAFB 0082EB13 0082EB38 0082EB50 0082EB75 0082EB9A 0082EBBF 0082EBE5 0082EC0D 0082EC35
0082EC5D 0082EC97 0082FAB6 00831008 00838CF5 00838E59 0083946D 008394B3 0083950B 0083961D 0083965F 008396F8 00839895 00839976
00839A42 00839AAA 00839B48 00839B74 0083AE2B 0083AFDB 0083B792 0083B806 0083B824 0083B83E 0083B858 0083B985 0083BAA8 0083BBAC
0083BC6C 0083CE79 0083D0EE 0083D17F 0083DCA1 0083DE9B 0083DEC1 0083E3F3 0083E44F 0083E471 0083E51E 0083E572 0083E594 0083FDFB
0083FFDE 008400F5 0084046B 00840575 008409EB 00841EC5 00842D19 00843064 008434DE 00846323 00846FB6 00847C1E 00848367 00848395
00849760 008497EA 00849946 00849DF9 00849E8A 0084A347 0084AA4F 0084B100 0084B26D 0084B9CD 0084CF73 0084D079 0084D6BF 0084D801
0084D941 0084DADF 0084DC9D 008506D3 0085071D 00850743 00850775 008507D3 00850AEE 00850BC2 00850F33 00851752 0085220F 008525E9
008527C6 0085287B 008528BD 0085294B 00852AD2 00853230 008532F7 00853328 0085336C 008533DE 008535FA 00853639 00853739 00853996
00854DC3 00854E2B 00854E9E 0085610C 0085629F 008567E1 00856848 00856999 00856B79 00856FB9 00857037 00857591 008578B7 00857928
00857B6D 00857EF3 008582D3 008587F6 0085981D 0085AE8A 0085BF53 0085C40A 0085C425 0085C47D 0085CAFB 0085D895 0085D91B 0085DA78
0085DD7E 0085DE42 0085E0AF 0085E178 0085E726 0085F703 0085F9F0 0085FA09 0085FA6E 0085FB59 00860EA5 00860F04 00861CD4 008620C9
008632B4 008632D9 00863429 00863449 00863479 008634A9 008634C4 008634E0 00863509 0086352A 00863546 00863589 008635AE 008635CA
008635E6 00863605 0086362B 0086364A 00863669 008636B1 008636D6 008636F2 0086370E 0086372A 00863746 00863762 0086377E 0086379A
008637C0 008637DF 008637FE 0086381D 00863854
```
