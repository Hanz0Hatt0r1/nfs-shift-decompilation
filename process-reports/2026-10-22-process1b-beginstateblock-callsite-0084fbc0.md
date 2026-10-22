# Process 1 — retail adapter BeginStateBlock caller boundary 0x0084FBC0

**Date:** 2026-10-22. **PE:** Need for Speed SHIFT PC retail 1.02, PE32 x86, ImageBase 0x00400000. **Verified SHA-256:** eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1.

**Scope:** original PE, uploaded full GNU objdump, incoming virtual calls; no code/P-code/runtime/renderer changes and no replay. Prior 0x0084FBF0 report accepted without repeating its analysis.

## Finding and confidence

**Proven:** primary adapter constructor 0x00850100 writes vptr 0x00B1BBA8 and BYTE[adapter+4]=0. PE DWORD at 0x00B1BC98 (vptr+0xF0; file offset 0x71A698) is 0x0084FBC0, bytes C0 FB 84 00. This is a data reference, not an external executable callsite. The preceding ABI is stack passed: [EBP+8]=adapter, no ECX=this requirement; 0x0084FBC6 reads BYTE[adapter+4], 0x0084FBC9 saves it into BYTE[adapter+5], 0x0084FBCC clears +4; 0x0084FBDC invokes underlying CreateDevice-proven D3D9 BeginStateBlock through [device.vptr+0xF0]. EAX propagates unmodified, RET 4 cleans one DWORD.

**Bounded negative result:** no external callsite could be safely attributed to adapter primary vptr 0x00B1BBA8. No inspected same-call path proves a nonzero write to BYTE[adapter+4] before Begin. This is not a claim that such a caller, alias, or writer never exists.

## Exact complete executable scan

Full SHIFT_objdump_full.txt sections .text (VA 0x401000 through 0xAA5488) and .secu (VA starting 0xD31000, length 0x63070): 2,845,669 linearly decoded code-section address lines. Regex search for a positive register-base [eax|ebx|ecx|edx|esi|edi+0xF0] produced **471** references; exact MOV 32-bit register, DWORD PTR [register+0xF0] yielded **127**. Requiring a CALL of the loaded register among the following 12 decoded instruction rows and within 48 code bytes yielded **29 permissive candidate windows**, not a points-to result (clobbers and jumps allowed). Direct CALL rel32 to 0x0084FBC0: **0**; direct memory-form CALL [reg+0xF0]: **0**. The literal target DWORD C0 FB 84 00 occurs once in the original PE (offset 0x71A698). Search covers both executable sections, not merely rel32 references.

Strongest fully inspected counterexamples, with *complete* raw function blocks below:

* **0x004B2544**, inside 0x004B24D0–0x004B2548: ECX=[0xBE47E8]; pointer F=[[ECX]+0xF0]. No PUSH adapter before CALL EDX, so does not meet ordinary one-stack-DWORD Begin-wrapper ABI. Global-object-to-adapter identity not proved; no preceding +4 nonzero writer for adapter.
* **0x006F24B0**, inside 0x006F2440–0x006F24F6: ECX=[0xC0F808]; F=[[ECX]+0xF0]; CALL EDX with no explicit PUSH adapter. No identity proof or nonzero adapter+4 writer.
* **0x008B4FAC**, inside 0x008B4F90–0x008B5096: ECX=[0xC2B364], F=[[ECX]+0xF0], but pushed argument is separately sourced EDX=[ESI+0xC]. This is one correctly shaped stack argument, **not** a proved matching adapter receiver. Nor is there a local write to [EDX+4] before call.

Additional shape false positives include 0x0084FBD6 (outgoing D3D9 *device* vtable+0xF0, not incoming adapter), 0x00927E60 (function pointer stored at struct+0xF0, no vptr load), and 0x004CD4BB (data member+0xF0, not vtable). 0x004B3049 is overwritten before the apparent CALL EDX. Other candidates through linked-list objects use ECX=this and no pushed adapter, or have multiple pushed arguments. No syntactic pattern without receiver-origin proof was promoted to a positive caller.

**Blind spots:** linear disassembly of code sections may include embedded data or miss overlapping alternate entries; this scan misses calculated slot offsets, register/stack spills, longer-distance dispatches, callbacks, heap aliases, copied vtables, indirect memory calls and runtime-initialized memory. It does not establish whole-program non-reachability, dynamic vptr identity or absence of external writes. No global search for byte+4 writers was attempted.

## Runtime separation

User-reported v757 P-code replay: 360 frames, nontruncated trace of 0x0084FBC0/0x0084FBF0/0x0084FD60 and selected D3D9 targets, zero events; validation_errors=0. These are bounded external observations, not a new replay and not a proof of static non-reachability.

## Exactly one next target

**0x0082E110** — trace the existing adapter getter returning wrapper+0x478 through its immediate consumers, retaining pointer identity until any vptr+0xF0 one-argument dispatch. This is a new bounded provenance check, not a repeat of the byte+4 writer search.

## Original PE full byte blocks

### 0x004B24D0–0x004B2548, candidate A

```asm
  4b24d0:	55                   	push   ebp
  4b24d1:	8b ec                	mov    ebp,esp
  4b24d3:	80 7d 08 00          	cmp    BYTE PTR [ebp+0x8],0x0
  4b24d7:	56                   	push   esi
  4b24d8:	8b f1                	mov    esi,ecx
  4b24da:	c6 86 e1 04 00 00 00 	mov    BYTE PTR [esi+0x4e1],0x0
  4b24e1:	74 63                	je     0x4b2546
  4b24e3:	e8 08 38 00 00       	call   0x4b5cf0
  4b24e8:	8b ce                	mov    ecx,esi
  4b24ea:	e8 01 19 44 00       	call   0x8f3df0
  4b24ef:	8b 0d e8 47 be 00    	mov    ecx,DWORD PTR ds:0xbe47e8
  4b24f5:	8b 01                	mov    eax,DWORD PTR [ecx]
  4b24f7:	8b 90 b4 00 00 00    	mov    edx,DWORD PTR [eax+0xb4]
  4b24fd:	ff d2                	call   edx
  4b24ff:	84 c0                	test   al,al
  4b2501:	74 43                	je     0x4b2546
  4b2503:	b8 01 00 00 00       	mov    eax,0x1
  4b2508:	84 05 30 d0 bb 00    	test   BYTE PTR ds:0xbbd030,al
  4b250e:	75 1d                	jne    0x4b252d
  4b2510:	09 05 30 d0 bb 00    	or     DWORD PTR ds:0xbbd030,eax
  4b2516:	b9 00 c6 bb 00       	mov    ecx,0xbbc600
  4b251b:	e8 70 df f5 ff       	call   0x410490
  4b2520:	68 60 ae a9 00       	push   0xa9ae60
  4b2525:	e8 89 ea 44 00       	call   0x900fb3
  4b252a:	83 c4 04             	add    esp,0x4
  4b252d:	80 3d 14 c6 bb 00 00 	cmp    BYTE PTR ds:0xbbc614,0x0
  4b2534:	75 10                	jne    0x4b2546
  4b2536:	8b 0d e8 47 be 00    	mov    ecx,DWORD PTR ds:0xbe47e8
  4b253c:	8b 01                	mov    eax,DWORD PTR [ecx]
  4b253e:	8b 90 f0 00 00 00    	mov    edx,DWORD PTR [eax+0xf0]
  4b2544:	ff d2                	call   edx
  4b2546:	5e                   	pop    esi
  4b2547:	5d                   	pop    ebp
  4b2548:	c2 04 00             	ret    0x4
```

### 0x006F2440–0x006F24F6, candidate B

```asm
  6f2440:	55                   	push   ebp
  6f2441:	8b ec                	mov    ebp,esp
  6f2443:	83 ec 08             	sub    esp,0x8
  6f2446:	53                   	push   ebx
  6f2447:	56                   	push   esi
  6f2448:	57                   	push   edi
  6f2449:	8b f1                	mov    esi,ecx
  6f244b:	c6 45 ff 01          	mov    BYTE PTR [ebp-0x1],0x1
  6f244f:	e8 4c 69 ff ff       	call   0x6e8da0
  6f2454:	51                   	push   ecx
  6f2455:	8d 7e 24             	lea    edi,[esi+0x24]
  6f2458:	8b cc                	mov    ecx,esp
  6f245a:	57                   	push   edi
  6f245b:	8b d8                	mov    ebx,eax
  6f245d:	e8 7e eb f3 ff       	call   0x630fe0
  6f2462:	8d 8b 80 02 00 00    	lea    ecx,[ebx+0x280]
  6f2468:	e8 f3 8a ff ff       	call   0x6eaf60
  6f246d:	8b 5e 18             	mov    ebx,DWORD PTR [esi+0x18]
  6f2470:	53                   	push   ebx
  6f2471:	8d 55 ff             	lea    edx,[ebp-0x1]
  6f2474:	8d 4d fe             	lea    ecx,[ebp-0x2]
  6f2477:	88 45 fe             	mov    BYTE PTR [ebp-0x2],al
  6f247a:	e8 81 fe ff ff       	call   0x6f2300
  6f247f:	85 c0                	test   eax,eax
  6f2481:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  6f2484:	74 6a                	je     0x6f24f0
  6f2486:	85 db                	test   ebx,ebx
  6f2488:	75 35                	jne    0x6f24bf
  6f248a:	8b 0f                	mov    ecx,DWORD PTR [edi]
  6f248c:	85 c9                	test   ecx,ecx
  6f248e:	74 2f                	je     0x6f24bf
  6f2490:	68 54 05 b0 00       	push   0xb00554
  6f2495:	51                   	push   ecx
  6f2496:	e8 de ec 20 00       	call   0x901179
  6f249b:	83 c4 08             	add    esp,0x8
  6f249e:	85 c0                	test   eax,eax
  6f24a0:	75 1a                	jne    0x6f24bc
  6f24a2:	8b 0d 08 f8 c0 00    	mov    ecx,DWORD PTR ds:0xc0f808
  6f24a8:	8b 01                	mov    eax,DWORD PTR [ecx]
  6f24aa:	8b 90 f0 00 00 00    	mov    edx,DWORD PTR [eax+0xf0]
  6f24b0:	ff d2                	call   edx
  6f24b2:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  6f24b5:	5f                   	pop    edi
  6f24b6:	5e                   	pop    esi
  6f24b7:	5b                   	pop    ebx
  6f24b8:	8b e5                	mov    esp,ebp
  6f24ba:	5d                   	pop    ebp
  6f24bb:	c3                   	ret
  6f24bc:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  6f24bf:	83 7e 18 00          	cmp    DWORD PTR [esi+0x18],0x0
  6f24c3:	75 2b                	jne    0x6f24f0
  6f24c5:	8b 3f                	mov    edi,DWORD PTR [edi]
  6f24c7:	85 ff                	test   edi,edi
  6f24c9:	74 25                	je     0x6f24f0
  6f24cb:	68 40 05 b0 00       	push   0xb00540
  6f24d0:	57                   	push   edi
  6f24d1:	e8 a3 ec 20 00       	call   0x901179
  6f24d6:	83 c4 08             	add    esp,0x8
  6f24d9:	85 c0                	test   eax,eax
  6f24db:	75 10                	jne    0x6f24ed
  6f24dd:	8b 0d 08 f8 c0 00    	mov    ecx,DWORD PTR ds:0xc0f808
  6f24e3:	8b 01                	mov    eax,DWORD PTR [ecx]
  6f24e5:	8b 90 f8 00 00 00    	mov    edx,DWORD PTR [eax+0xf8]
  6f24eb:	ff d2                	call   edx
  6f24ed:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  6f24f0:	5f                   	pop    edi
  6f24f1:	5e                   	pop    esi
  6f24f2:	5b                   	pop    ebx
  6f24f3:	8b e5                	mov    esp,ebp
  6f24f5:	5d                   	pop    ebp
  6f24f6:	c3                   	ret
```

### 0x008B4F90–0x008B5096, candidate C

```asm
  8b4f90:	55                   	push   ebp
  8b4f91:	8b ec                	mov    ebp,esp
  8b4f93:	56                   	push   esi
  8b4f94:	8b f1                	mov    esi,ecx
  8b4f96:	8b 0d 64 b3 c2 00    	mov    ecx,DWORD PTR ds:0xc2b364
  8b4f9c:	85 c9                	test   ecx,ecx
  8b4f9e:	74 0e                	je     0x8b4fae
  8b4fa0:	8b 01                	mov    eax,DWORD PTR [ecx]
  8b4fa2:	8b 56 0c             	mov    edx,DWORD PTR [esi+0xc]
  8b4fa5:	8b 80 f0 00 00 00    	mov    eax,DWORD PTR [eax+0xf0]
  8b4fab:	52                   	push   edx
  8b4fac:	ff d0                	call   eax
  8b4fae:	8b 76 0c             	mov    esi,DWORD PTR [esi+0xc]
  8b4fb1:	83 fe 0d             	cmp    esi,0xd
  8b4fb4:	0f 87 da 00 00 00    	ja     0x8b5094
  8b4fba:	ff 24 b5 9c 50 8b 00 	jmp    DWORD PTR [esi*4+0x8b509c]
  8b4fc1:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b4fc4:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b4fc6:	8b 42 54             	mov    eax,DWORD PTR [edx+0x54]
  8b4fc9:	ff d0                	call   eax
  8b4fcb:	5e                   	pop    esi
  8b4fcc:	5d                   	pop    ebp
  8b4fcd:	c2 04 00             	ret    0x4
  8b4fd0:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b4fd3:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b4fd5:	8b 42 58             	mov    eax,DWORD PTR [edx+0x58]
  8b4fd8:	ff d0                	call   eax
  8b4fda:	5e                   	pop    esi
  8b4fdb:	5d                   	pop    ebp
  8b4fdc:	c2 04 00             	ret    0x4
  8b4fdf:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b4fe2:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b4fe4:	8b 42 5c             	mov    eax,DWORD PTR [edx+0x5c]
  8b4fe7:	ff d0                	call   eax
  8b4fe9:	5e                   	pop    esi
  8b4fea:	5d                   	pop    ebp
  8b4feb:	c2 04 00             	ret    0x4
  8b4fee:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b4ff1:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b4ff3:	8b 42 60             	mov    eax,DWORD PTR [edx+0x60]
  8b4ff6:	ff d0                	call   eax
  8b4ff8:	5e                   	pop    esi
  8b4ff9:	5d                   	pop    ebp
  8b4ffa:	c2 04 00             	ret    0x4
  8b4ffd:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b5000:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b5002:	8b 42 64             	mov    eax,DWORD PTR [edx+0x64]
  8b5005:	ff d0                	call   eax
  8b5007:	5e                   	pop    esi
  8b5008:	5d                   	pop    ebp
  8b5009:	c2 04 00             	ret    0x4
  8b500c:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b500f:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b5011:	8b 42 68             	mov    eax,DWORD PTR [edx+0x68]
  8b5014:	ff d0                	call   eax
  8b5016:	5e                   	pop    esi
  8b5017:	5d                   	pop    ebp
  8b5018:	c2 04 00             	ret    0x4
  8b501b:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b501e:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b5020:	8b 42 6c             	mov    eax,DWORD PTR [edx+0x6c]
  8b5023:	ff d0                	call   eax
  8b5025:	5e                   	pop    esi
  8b5026:	5d                   	pop    ebp
  8b5027:	c2 04 00             	ret    0x4
  8b502a:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b502d:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b502f:	8b 42 70             	mov    eax,DWORD PTR [edx+0x70]
  8b5032:	ff d0                	call   eax
  8b5034:	5e                   	pop    esi
  8b5035:	5d                   	pop    ebp
  8b5036:	c2 04 00             	ret    0x4
  8b5039:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b503c:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b503e:	8b 42 74             	mov    eax,DWORD PTR [edx+0x74]
  8b5041:	ff d0                	call   eax
  8b5043:	5e                   	pop    esi
  8b5044:	5d                   	pop    ebp
  8b5045:	c2 04 00             	ret    0x4
  8b5048:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b504b:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b504d:	8b 42 78             	mov    eax,DWORD PTR [edx+0x78]
  8b5050:	ff d0                	call   eax
  8b5052:	5e                   	pop    esi
  8b5053:	5d                   	pop    ebp
  8b5054:	c2 04 00             	ret    0x4
  8b5057:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b505a:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b505c:	8b 42 7c             	mov    eax,DWORD PTR [edx+0x7c]
  8b505f:	ff d0                	call   eax
  8b5061:	5e                   	pop    esi
  8b5062:	5d                   	pop    ebp
  8b5063:	c2 04 00             	ret    0x4
  8b5066:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b5069:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b506b:	8b 82 80 00 00 00    	mov    eax,DWORD PTR [edx+0x80]
  8b5071:	ff d0                	call   eax
  8b5073:	5e                   	pop    esi
  8b5074:	5d                   	pop    ebp
  8b5075:	c2 04 00             	ret    0x4
  8b5078:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b507b:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b507d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8b5080:	ff d0                	call   eax
  8b5082:	5e                   	pop    esi
  8b5083:	5d                   	pop    ebp
  8b5084:	c2 04 00             	ret    0x4
  8b5087:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  8b508a:	8b 11                	mov    edx,DWORD PTR [ecx]
  8b508c:	8b 82 cc 00 00 00    	mov    eax,DWORD PTR [edx+0xcc]
  8b5092:	ff d0                	call   eax
  8b5094:	5e                   	pop    esi
  8b5095:	5d                   	pop    ebp
  8b5096:	c2 04 00             	ret    0x4
```

### 0x0084FBC0–0x0084FBDF, target

```asm
  84fbc0:	55                   	push   ebp
  84fbc1:	8b ec                	mov    ebp,esp
  84fbc3:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  84fbc6:	8a 48 04             	mov    cl,BYTE PTR [eax+0x4]
  84fbc9:	88 48 05             	mov    BYTE PTR [eax+0x5],cl
  84fbcc:	c6 40 04 00          	mov    BYTE PTR [eax+0x4],0x0
  84fbd0:	8b 40 08             	mov    eax,DWORD PTR [eax+0x8]
  84fbd3:	8b 10                	mov    edx,DWORD PTR [eax]
  84fbd5:	50                   	push   eax
  84fbd6:	8b 82 f0 00 00 00    	mov    eax,DWORD PTR [edx+0xf0]
  84fbdc:	ff d0                	call   eax
  84fbde:	5d                   	pop    ebp
  84fbdf:	c2 04 00             	ret    0x4
```

### 0x00850100–0x0085017E, constructor

```asm
  850100:	55                   	push   ebp
  850101:	8b ec                	mov    ebp,esp
  850103:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  850106:	56                   	push   esi
  850107:	8b f1                	mov    esi,ecx
  850109:	c7 06 a8 bb b1 00    	mov    DWORD PTR [esi],0xb1bba8
  85010f:	89 46 08             	mov    DWORD PTR [esi+0x8],eax
  850112:	e8 d9 9f bb ff       	call   0x40a0f0
  850117:	33 c9                	xor    ecx,ecx
  850119:	89 86 e0 19 00 00    	mov    DWORD PTR [esi+0x19e0],eax
  85011f:	ba 08 00 00 00       	mov    edx,0x8
  850124:	f7 e2                	mul    edx
  850126:	0f 90 c1             	seto   cl
  850129:	f7 d9                	neg    ecx
  85012b:	0b c8                	or     ecx,eax
  85012d:	51                   	push   ecx
  85012e:	e8 8d 67 03 00       	call   0x8868c0
  850133:	89 86 dc 19 00 00    	mov    DWORD PTR [esi+0x19dc],eax
  850139:	c7 00 20 00 00 00    	mov    DWORD PTR [eax],0x20
  85013f:	8b 86 dc 19 00 00    	mov    eax,DWORD PTR [esi+0x19dc]
  850145:	c7 40 08 10 00 00 00 	mov    DWORD PTR [eax+0x8],0x10
  85014c:	8b 8e dc 19 00 00    	mov    ecx,DWORD PTR [esi+0x19dc]
  850152:	c7 41 10 30 00 00 00 	mov    DWORD PTR [ecx+0x10],0x30
  850159:	8b 96 dc 19 00 00    	mov    edx,DWORD PTR [esi+0x19dc]
  85015f:	c7 42 18 08 00 00 00 	mov    DWORD PTR [edx+0x18],0x8
  850166:	8b 86 dc 19 00 00    	mov    eax,DWORD PTR [esi+0x19dc]
  85016c:	c7 40 20 38 00 00 00 	mov    DWORD PTR [eax+0x20],0x38
  850173:	83 c4 04             	add    esp,0x4
  850176:	c6 46 04 00          	mov    BYTE PTR [esi+0x4],0x0
  85017a:	8b c6                	mov    eax,esi
  85017c:	5e                   	pop    esi
  85017d:	5d                   	pop    ebp
  85017e:	c2 04 00             	ret    0x4
```

