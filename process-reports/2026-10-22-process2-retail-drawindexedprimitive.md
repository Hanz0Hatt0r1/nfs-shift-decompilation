# Process 2 — retail `IDirect3DDevice9::DrawIndexedPrimitive` (SHIFT.exe)

2026-10-22 — static analysis only. No runtime guest Draw* proof. Original executable SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`; full objdump SHA-256 `cdae1cc92d07a4dffb9abdf2d242ca21fa2bb7b794b7285d5d1dd687bfef6475`.

## Slot verification

`IDirect3DDevice9` COM vtable zero-based slot **82**, 32-bit offset **0x148 = 82*4**. Neighboring indices: `SetNPatchMode=79/0x13c`, `GetNPatchMode=80/0x140`, `DrawPrimitive=81/0x144`, **`DrawIndexedPrimitive=82/0x148`**, `DrawPrimitiveUP=83/0x14c`, `DrawIndexedPrimitiveUP=84/0x150`. (API interface order; these are slots of *IDirect3DDevice9*, not generic C++ vtables.) Calling convention uses 7 32-bit pushes (this + 6 arguments, reverse order). Microsoft signature `DrawIndexedPrimitive(Type, BaseVertexIndex, MinVertexIndex, NumVertices, startIndex, primCount)`.

Method order references: https://directx-d.dpldocs.info/~master/directx.d3d9.IDirect3DDevice9.html ; https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-drawindexedprimitive

## Scope and classification

Scanned `.text` (VMA 0x00401000...) of the uploaded objdump, then checked raw PE32 instruction bytes: **no direct `call [reg+0x148]`**; there are `mov r,[vtable+0x148]` then `call r` sequences. 518 occurrences of `+0x148]` in `.text` (includes data member offsets), 180 `mov reg,DWORD PTR [...+0x148]` loads (includes non-vtable), 47 load-to-indirect `call/jmp` matches within 20 instructions, and **32** candidates with exactly six pushed parameters and an object argument. They are all listed below. Not every `+0x148` data member or vtable access is a D3D9 call. Range extraction below uses adjacent INT3 padding as linear-code boundaries, not recovered PDB function symbols. Every block is verbatim disassembly from the provided objdump, including instruction addresses and bytes.

**Parameter order in table:** `Type, BaseVertexIndex, MinVertexIndex, NumVertices, startIndex, primCount`. `4=TRIANGLELIST`, `5=TRIANGLESTRIP`, `6=TRIANGLEFAN`. Calls use `this` as final pushed DWORD. Static arguments must not be confused with runtime invocation.

## Indirect callsites

| Call VA | Method load VA | 32-bit function pointer access | Parameters | Containing linear function | 
| --- | --- | --- | --- | --- |
| `0x0083bbc6` | `0x0083bbb3` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x6, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0083bb40..0x0083bbff` |
| `0x0083bc95` | `0x0083bc8f` | `mov    eax,DWORD PTR [ecx+0x148]` → `call   eax` | `[0xb8ee70], 0, 0, [0xb8ee78], 0, [0xb8ee74]` | `0x0083bc00..0x0083bd16` |
| `0x008408df` | `0x008408d4` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x00840a5b` | `0x00840a48` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x00840cd6` | `0x00840cc3` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x00840f12` | `0x00840f01` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x00841196` | `0x00841183` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x0084152e` | `0x0084151b` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x0084189e` | `0x0084188f` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00840530..0x0084190b` |
| `0x00842140` | `0x0084212d` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00841ae0..0x00842ad9` |
| `0x0084252b` | `0x00842518` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00841ae0..0x00842ad9` |
| `0x00842896` | `0x00842883` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00841ae0..0x00842ad9` |
| `0x00842aab` | `0x00842a98` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00841ae0..0x00842ad9` |
| `0x00842ffd` | `0x00842fea` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00842cf0..0x0084302d` |
| `0x0084fd98` | `0x0084fd92` | `mov    eax,DWORD PTR [ecx+0x148]` → `call   eax` | `[ebp+0x0c], [ebp+0x10], [ebp+0x14], [ebp+0x18], [ebp+0x1c], [ebp+0x20]` | `0x0084fd60..0x0084fd9f` |
| `0x0085129a` | `0x00851287` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00850dc0..0x0085172e` |
| `0x008514d9` | `0x008514c6` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00850dc0..0x0085172e` |
| `0x008516f4` | `0x008516e1` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00850dc0..0x0085172e` |
| `0x00851b5f` | `0x00851b4c` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00851730..0x008521e9` |
| `0x00851d9e` | `0x00851d8b` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00851730..0x008521e9` |
| `0x00851f9f` | `0x00851f8c` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00851730..0x008521e9` |
| `0x008521af` | `0x0085219c` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00851730..0x008521e9` |
| `0x00852554` | `0x0085254e` | `mov    eax,DWORD PTR [edx+0x148]` → `call   eax` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x008521f0..0x0085257a` |
| `0x0085c8b1` | `0x0085c89e` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085c370..0x0085cacf` |
| `0x0085ca3b` | `0x0085ca28` | `mov    edx,DWORD PTR [ecx+0x148]` → `call   edx` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085c370..0x0085cacf` |
| `0x0085e49f` | `0x0085e494` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085e040..0x0085e6d3` |
| `0x0085e5bd` | `0x0085e5aa` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x4, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085e040..0x0085e6d3` |
| `0x0085f920` | `0x0085f90d` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085f6e0..0x0085f996` |
| `0x0085fc9c` | `0x0085fc89` | `mov    eax,DWORD PTR [edx+0x148]` → `call   eax` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085fb00..0x00860bed` |
| `0x0085fd3c` | `0x0085fd29` | `mov    ecx,DWORD PTR [eax+0x148]` → `call   ecx` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085fb00..0x00860bed` |
| `0x00860baf` | `0x00860ba9` | `mov    eax,DWORD PTR [edx+0x148]` → `call   eax` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x0085fb00..0x00860bed` |
| `0x00861372` | `0x0086135f` | `mov    eax,DWORD PTR [edx+0x148]` → `call   eax` | `0x5, 0x0, 0x0, 0x4, 0x0, 0x2` | `0x00860e60..0x008614b3` |

### Dynamic parameter cases

- `0x0083bc95`: `call 0x0082e110` returns device interface in EAX; `ECX=[EAX]`; method EAX=`[ECX+0x148]`. `D3DPRIMITIVETYPE=[0xb8ee70]`, `BaseVertexIndex=0`, `MinVertexIndex=0`, `NumVertices=[0xb8ee78]`, `startIndex=0`, `primCount=[0xb8ee74]`. None of three globals is statically constant.
- `0x0084fd98`: forwarded six arguments from caller's `[EBP+0x0c..0x20]` through `device=[([EBP+8])+8]`; `ECX=[EAX]` and pointer=`[ECX+0x148]`; conditional `call 0x0084f000` if byte `[ESI+4]` nonzero. Caller argument values unknown at this point.
- `0x0083bbc6` uses `Type=6` triangle fan; 22 sites use `Type=4` triangle list, seven use `Type=5` triangle strip. Fixed geometry has `BaseVertexIndex=0, MinVertexIndex=0, NumVertices=4, startIndex=0, primCount=2`. All 30 fixed calls draw 2 triangles; the `TRIANGLEFAN` example also renders a quad.

### Setup/state evidence, not overinterpreted

- `0x0083bbc6`, `0x0083bc95`: on another object `[ESI+0x0c]`, virtual `+0x100`, `+0x104` surround setup; `call 0x0083af10` immediately before `call 0x0082e110` device retrieval; afterward another-object `+0x108` and, in first loop, `+0x10c`. These offsets on *other vtables* are not automatically D3D9 functions.
- In `0x00840530..0x0084302d` and `0x00850dc0..0x008614b3` regions, D3D9 device vtable `+0x190` and `+0x1a0` appear in setup; on a verified D3D9 device these correspond to `SetStreamSource` and `SetIndices`. Device vtable `+0xe4` is `SetRenderState`. Inspect the full blocks to check *which object* each slot is loaded from: several nearby `+0xfc/+0x100/+0x104/+0x108/+0x10c` accesses operate on a separate wrapper/resource object. Do not relabel them as Direct3D9 state methods by offset alone.
- Most fixed sites are wrapped by calls through a separate object's `+0x100`, `+0x104`, `+0x108`, `+0x10c`; e.g. before `0x008408df` these are at `0x008408b1/0x008408c1`, and after at `0x008408e7/0x008408f4`. At `0x008408ff` device `+0xe4` (`SetRenderState`) follows.
- `0x0085c8b1` and `0x0085ca3b` additionally have adjacent `+0x13c` (GetNPatchMode, D3D9 vtable only) and lower-level wrapper activity; `0x00860baf` bracketed by secondary object's `+0x100/+0x104` and `+0x108/+0x10c`. The listed linear blocks preserve all upstream setup states verbatim.

## P1 observed chain and confidence

`0x00835590 -> 0x00831380` is a **verified direct call edge**: first call at `0x008355b5`, plus repeated calls e.g. `0x00835608/0x00835655`; `0x00831380` checks queue state `[ECX+0x24]`, obtains `[ECX+0x1c]`, reads a pointer into `[EDX]`, calls `0x0049c6f0`, then returns success. `0x00835590` tests item state `call 0x005e1d50`, invokes `0x008352f0` for one path, and uses virtual callbacks such as `[vtable+0x88]` on dequeued objects; no direct call to any of the 32 Draw sites was observed within these two functions. The static link from the observed queue to a D3D9 draw site is **not established**; dynamic callbacks might bridge it, but must be proven using a guest RIP/return-address, target-device identity and executed call event. v668 observed no guest Draw*; v719 stopped at CreateTexture; v722 showed DXT3 CreateTexture request blocked by `DXT3=0` in capture adapter. Dispatch and frame counts are not reachability proof.

## Preferred next trace

First remove capture-only DXT3 capability blocker via existing PR #2143 (no new PR or ABI redesign). Then instrument dynamic branch from `0x00835590` dequeued object's vtable callback and `0x008352f0` target, recording guest EIP/stack, and independently trap the simple canonical retail DIP at `0x0083bbc6` (or `0x0084fd98` for generic forwarding), logging seven pushed DWORDs plus device identity. Correlate actual guest execution, not aggregate dispatch/frame counts. If no match, widen to `0x008408df` onward.

## Complete linear instruction blocks from original objdump

The following 14 INT3-delimited spans encompass all 32 sites and give byte-for-byte objdump output. Some spans may contain several inlined or contiguous logical routines; without symbols, label them conservative linear ranges, not proven semantic function boundaries. `0x0084fd60` is an unambiguous parameter-forwarding thunk. Negative claim: no 0x148 direct-memory CALL was found in `.text`; other vtable `+0x148` uses with fewer parameters must not be included as D3D9 draws.

### `0x0083bb40..0x0083bbff` — sites `0x0083bbc6`

```asm
  83bb40:	55                   	push   ebp
  83bb41:	8b ec                	mov    ebp,esp
  83bb43:	51                   	push   ecx
  83bb44:	53                   	push   ebx
  83bb45:	56                   	push   esi
  83bb46:	8b f1                	mov    esi,ecx
  83bb48:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bb4b:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bb4d:	57                   	push   edi
  83bb4e:	8b 7e 3c             	mov    edi,DWORD PTR [esi+0x3c]
  83bb51:	8b da                	mov    ebx,edx
  83bb53:	8d 14 db             	lea    edx,[ebx+ebx*8]
  83bb56:	8b 14 97             	mov    edx,DWORD PTR [edi+edx*4]
  83bb59:	52                   	push   edx
  83bb5a:	50                   	push   eax
  83bb5b:	8b 81 e8 00 00 00    	mov    eax,DWORD PTR [ecx+0xe8]
  83bb61:	ff d0                	call   eax
  83bb63:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bb66:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bb68:	6a 03                	push   0x3
  83bb6a:	8d 55 fc             	lea    edx,[ebp-0x4]
  83bb6d:	52                   	push   edx
  83bb6e:	50                   	push   eax
  83bb6f:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  83bb75:	ff d0                	call   eax
  83bb77:	33 ff                	xor    edi,edi
  83bb79:	39 7d fc             	cmp    DWORD PTR [ebp-0x4],edi
  83bb7c:	76 60                	jbe    0x83bbde
  83bb7e:	8b ff                	mov    edi,edi
  83bb80:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bb83:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bb85:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  83bb8b:	57                   	push   edi
  83bb8c:	50                   	push   eax
  83bb8d:	ff d2                	call   edx
  83bb8f:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bb92:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bb94:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  83bb9a:	50                   	push   eax
  83bb9b:	ff d2                	call   edx
  83bb9d:	8b d3                	mov    edx,ebx
  83bb9f:	8b ce                	mov    ecx,esi
  83bba1:	e8 6a f3 ff ff       	call   0x83af10
  83bba6:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  83bbac:	e8 5f 25 ff ff       	call   0x82e110
  83bbb1:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bbb3:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  83bbb9:	6a 02                	push   0x2
  83bbbb:	6a 00                	push   0x0
  83bbbd:	6a 04                	push   0x4
  83bbbf:	6a 00                	push   0x0
  83bbc1:	6a 00                	push   0x0
  83bbc3:	6a 06                	push   0x6
  83bbc5:	50                   	push   eax
  83bbc6:	ff d2                	call   edx
  83bbc8:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bbcb:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bbcd:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  83bbd3:	50                   	push   eax
  83bbd4:	ff d2                	call   edx
  83bbd6:	83 c7 01             	add    edi,0x1
  83bbd9:	3b 7d fc             	cmp    edi,DWORD PTR [ebp-0x4]
  83bbdc:	72 a2                	jb     0x83bb80
  83bbde:	8b 76 0c             	mov    esi,DWORD PTR [esi+0xc]
  83bbe1:	8b 06                	mov    eax,DWORD PTR [esi]
  83bbe3:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  83bbe9:	56                   	push   esi
  83bbea:	ff d1                	call   ecx
  83bbec:	5f                   	pop    edi
  83bbed:	5e                   	pop    esi
  83bbee:	c7 05 18 e4 b8 00 01 00 00 00 	mov    DWORD PTR ds:0xb8e418,0x1
  83bbf8:	b0 01                	mov    al,0x1
  83bbfa:	5b                   	pop    ebx
  83bbfb:	8b e5                	mov    esp,ebp
  83bbfd:	5d                   	pop    ebp
  83bbfe:	c3                   	ret
```

### `0x0083bc00..0x0083bd16` — sites `0x0083bc95`

```asm
  83bc00:	55                   	push   ebp
  83bc01:	8b ec                	mov    ebp,esp
  83bc03:	53                   	push   ebx
  83bc04:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  83bc07:	56                   	push   esi
  83bc08:	8b f1                	mov    esi,ecx
  83bc0a:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bc0d:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc0f:	57                   	push   edi
  83bc10:	8b 7e 3c             	mov    edi,DWORD PTR [esi+0x3c]
  83bc13:	8d 14 db             	lea    edx,[ebx+ebx*8]
  83bc16:	8b 14 97             	mov    edx,DWORD PTR [edi+edx*4]
  83bc19:	52                   	push   edx
  83bc1a:	50                   	push   eax
  83bc1b:	8b 81 e8 00 00 00    	mov    eax,DWORD PTR [ecx+0xe8]
  83bc21:	ff d0                	call   eax
  83bc23:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bc26:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc28:	6a 03                	push   0x3
  83bc2a:	8d 55 08             	lea    edx,[ebp+0x8]
  83bc2d:	52                   	push   edx
  83bc2e:	50                   	push   eax
  83bc2f:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  83bc35:	ff d0                	call   eax
  83bc37:	33 ff                	xor    edi,edi
  83bc39:	39 7d 08             	cmp    DWORD PTR [ebp+0x8],edi
  83bc3c:	76 6f                	jbe    0x83bcad
  83bc3e:	8b ff                	mov    edi,edi
  83bc40:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bc43:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc45:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  83bc4b:	57                   	push   edi
  83bc4c:	50                   	push   eax
  83bc4d:	ff d2                	call   edx
  83bc4f:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bc52:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc54:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  83bc5a:	50                   	push   eax
  83bc5b:	ff d2                	call   edx
  83bc5d:	8b d3                	mov    edx,ebx
  83bc5f:	8b ce                	mov    ecx,esi
  83bc61:	e8 aa f2 ff ff       	call   0x83af10
  83bc66:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  83bc6c:	e8 9f 24 ff ff       	call   0x82e110
  83bc71:	8b 15 74 ee b8 00    	mov    edx,DWORD PTR ds:0xb8ee74
  83bc77:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc79:	52                   	push   edx
  83bc7a:	8b 15 78 ee b8 00    	mov    edx,DWORD PTR ds:0xb8ee78
  83bc80:	6a 00                	push   0x0
  83bc82:	52                   	push   edx
  83bc83:	8b 15 70 ee b8 00    	mov    edx,DWORD PTR ds:0xb8ee70
  83bc89:	6a 00                	push   0x0
  83bc8b:	6a 00                	push   0x0
  83bc8d:	52                   	push   edx
  83bc8e:	50                   	push   eax
  83bc8f:	8b 81 48 01 00 00    	mov    eax,DWORD PTR [ecx+0x148]
  83bc95:	ff d0                	call   eax
  83bc97:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  83bc9a:	8b 08                	mov    ecx,DWORD PTR [eax]
  83bc9c:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  83bca2:	50                   	push   eax
  83bca3:	ff d2                	call   edx
  83bca5:	83 c7 01             	add    edi,0x1
  83bca8:	3b 7d 08             	cmp    edi,DWORD PTR [ebp+0x8]
  83bcab:	72 93                	jb     0x83bc40
  83bcad:	5f                   	pop    edi
  83bcae:	5e                   	pop    esi
  83bcaf:	b0 01                	mov    al,0x1
  83bcb1:	c7 05 18 e4 b8 00 01 00 00 00 	mov    DWORD PTR ds:0xb8e418,0x1
  83bcbb:	5b                   	pop    ebx
  83bcbc:	5d                   	pop    ebp
  83bcbd:	c2 04 00             	ret    0x4
  83bcc0:	55                   	push   ebp
  83bcc1:	8b ec                	mov    ebp,esp
  83bcc3:	81 ec 04 01 00 00    	sub    esp,0x104
  83bcc9:	53                   	push   ebx
  83bcca:	50                   	push   eax
  83bccb:	51                   	push   ecx
  83bccc:	68 f0 7b ab 00       	push   0xab7bf0
  83bcd1:	8d 95 fc fe ff ff    	lea    edx,[ebp-0x104]
  83bcd7:	68 00 01 00 00       	push   0x100
  83bcdc:	52                   	push   edx
  83bcdd:	e8 9e 64 c0 ff       	call   0x442180
  83bce2:	83 c4 14             	add    esp,0x14
  83bce5:	8d 85 fc fe ff ff    	lea    eax,[ebp-0x104]
  83bceb:	50                   	push   eax
  83bcec:	8d 4d fc             	lea    ecx,[ebp-0x4]
  83bcef:	e8 4c 5a df ff       	call   0x631740
  83bcf4:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  83bcf7:	51                   	push   ecx
  83bcf8:	8b 4d 08             	mov    ecx,DWORD PTR [ebp+0x8]
  83bcfb:	8d 55 fc             	lea    edx,[ebp-0x4]
  83bcfe:	e8 1d eb ff ff       	call   0x83a820
  83bd03:	8d 4d fc             	lea    ecx,[ebp-0x4]
  83bd06:	8a d8                	mov    bl,al
  83bd08:	e8 b3 53 df ff       	call   0x6310c0
  83bd0d:	8a c3                	mov    al,bl
  83bd0f:	5b                   	pop    ebx
  83bd10:	8b e5                	mov    esp,ebp
  83bd12:	5d                   	pop    ebp
  83bd13:	c2 08 00             	ret    0x8
```

### `0x00840530..0x0084190b` — sites `0x008408df`, `0x00840a5b`, `0x00840cd6`, `0x00840f12`, `0x00841196`, `0x0084152e`, `0x0084189e`

```asm
  840530:	53                   	push   ebx
  840531:	8b dc                	mov    ebx,esp
  840533:	83 ec 08             	sub    esp,0x8
  840536:	83 e4 f0             	and    esp,0xfffffff0
  840539:	83 c4 04             	add    esp,0x4
  84053c:	55                   	push   ebp
  84053d:	8b 6b 04             	mov    ebp,DWORD PTR [ebx+0x4]
  840540:	89 6c 24 04          	mov    DWORD PTR [esp+0x4],ebp
  840544:	8b ec                	mov    ebp,esp
  840546:	81 ec c8 02 00 00    	sub    esp,0x2c8
  84054c:	56                   	push   esi
  84054d:	8b f1                	mov    esi,ecx
  84054f:	80 7e 26 00          	cmp    BYTE PTR [esi+0x26],0x0
  840553:	57                   	push   edi
  840554:	74 6e                	je     0x8405c4
  840556:	83 7e 28 00          	cmp    DWORD PTR [esi+0x28],0x0
  84055a:	0f 84 a0 13 00 00    	je     0x841900
  840560:	68 68 a6 b1 00       	push   0xb1a668
  840565:	68 00 00 ff ff       	push   0xffff0000
  84056a:	e8 b9 30 0e 00       	call   0x923628
  84056f:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  840575:	e8 96 db fe ff       	call   0x82e110
  84057a:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  840580:	8b f8                	mov    edi,eax
  840582:	8d 45 b8             	lea    eax,[ebp-0x48]
  840585:	50                   	push   eax
  840586:	8b 01                	mov    eax,DWORD PTR [ecx]
  840588:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  84058e:	33 d2                	xor    edx,edx
  840590:	89 7d e8             	mov    DWORD PTR [ebp-0x18],edi
  840593:	ff d0                	call   eax
  840595:	33 d2                	xor    edx,edx
  840597:	8b c8                	mov    ecx,eax
  840599:	e8 32 2a 01 00       	call   0x852fd0
  84059e:	8b 56 14             	mov    edx,DWORD PTR [esi+0x14]
  8405a1:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8405a7:	e8 64 df fe ff       	call   0x82e510
  8405ac:	8b 56 18             	mov    edx,DWORD PTR [esi+0x18]
  8405af:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8405b1:	8b 81 a0 01 00 00    	mov    eax,DWORD PTR [ecx+0x1a0]
  8405b7:	52                   	push   edx
  8405b8:	57                   	push   edi
  8405b9:	ff d0                	call   eax
  8405bb:	85 c0                	test   eax,eax
  8405bd:	7d 10                	jge    0x8405cf
  8405bf:	e8 5e 30 0e 00       	call   0x923622
  8405c4:	32 c0                	xor    al,al
  8405c6:	5f                   	pop    edi
  8405c7:	5e                   	pop    esi
  8405c8:	8b e5                	mov    esp,ebp
  8405ca:	5d                   	pop    ebp
  8405cb:	8b e3                	mov    esp,ebx
  8405cd:	5b                   	pop    ebx
  8405ce:	c3                   	ret
  8405cf:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8405d1:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  8405d7:	6a 00                	push   0x0
  8405d9:	68 c2 00 00 00       	push   0xc2
  8405de:	57                   	push   edi
  8405df:	ff d2                	call   edx
  8405e1:	8b 4e 68             	mov    ecx,DWORD PTR [esi+0x68]
  8405e4:	85 c9                	test   ecx,ecx
  8405e6:	74 0c                	je     0x8405f4
  8405e8:	e8 03 88 ff ff       	call   0x838df0
  8405ed:	85 c0                	test   eax,eax
  8405ef:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
  8405f2:	75 16                	jne    0x84060a
  8405f4:	8b 4e 64             	mov    ecx,DWORD PTR [esi+0x64]
  8405f7:	8b 01                	mov    eax,DWORD PTR [ecx]
  8405f9:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  8405fc:	33 d2                	xor    edx,edx
  8405fe:	ff d0                	call   eax
  840600:	8b c8                	mov    ecx,eax
  840602:	e8 e9 87 ff ff       	call   0x838df0
  840607:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
  84060a:	d9 46 2c             	fld    DWORD PTR [esi+0x2c]
  84060d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840610:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  840613:	8b c8                	mov    ecx,eax
  840615:	d9 46 30             	fld    DWORD PTR [esi+0x30]
  840618:	c7 45 bc 00 00 00 00 	mov    DWORD PTR [ebp-0x44],0x0
  84061f:	d9 46 2c             	fld    DWORD PTR [esi+0x2c]
  840622:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840625:	d8 e9                	fsubr  st,st(1)
  840627:	de f9                	fdivp  st(1),st
  840629:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  84062c:	8b 39                	mov    edi,DWORD PTR [ecx]
  84062e:	8b 10                	mov    edx,DWORD PTR [eax]
  840630:	8d 4d c0             	lea    ecx,[ebp-0x40]
  840633:	51                   	push   ecx
  840634:	68 54 a6 b1 00       	push   0xb1a654
  840639:	6a 00                	push   0x0
  84063b:	50                   	push   eax
  84063c:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84063f:	ff d0                	call   eax
  840641:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  840644:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  84064a:	50                   	push   eax
  84064b:	51                   	push   ecx
  84064c:	ff d2                	call   edx
  84064e:	d9 46 40             	fld    DWORD PTR [esi+0x40]
  840651:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840654:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  840657:	d9 46 44             	fld    DWORD PTR [esi+0x44]
  84065a:	8b c8                	mov    ecx,eax
  84065c:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  84065f:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840662:	d9 46 48             	fld    DWORD PTR [esi+0x48]
  840665:	d9 5d c8             	fstp   DWORD PTR [ebp-0x38]
  840668:	d9 46 4c             	fld    DWORD PTR [esi+0x4c]
  84066b:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  84066e:	8b 39                	mov    edi,DWORD PTR [ecx]
  840670:	8b 10                	mov    edx,DWORD PTR [eax]
  840672:	8d 4d c0             	lea    ecx,[ebp-0x40]
  840675:	51                   	push   ecx
  840676:	68 44 a6 b1 00       	push   0xb1a644
  84067b:	6a 00                	push   0x0
  84067d:	50                   	push   eax
  84067e:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840681:	ff d0                	call   eax
  840683:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  840686:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  84068c:	50                   	push   eax
  84068d:	51                   	push   ecx
  84068e:	ff d2                	call   edx
  840690:	d9 46 44             	fld    DWORD PTR [esi+0x44]
  840693:	d8 66 40             	fsub   DWORD PTR [esi+0x40]
  840696:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840699:	8b c8                	mov    ecx,eax
  84069b:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  84069e:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  8406a1:	d9 46 4c             	fld    DWORD PTR [esi+0x4c]
  8406a4:	d8 66 48             	fsub   DWORD PTR [esi+0x48]
  8406a7:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  8406aa:	d9 ee                	fldz
  8406ac:	d9 55 c8             	fst    DWORD PTR [ebp-0x38]
  8406af:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  8406b2:	8b 39                	mov    edi,DWORD PTR [ecx]
  8406b4:	8b 10                	mov    edx,DWORD PTR [eax]
  8406b6:	8d 4d c0             	lea    ecx,[ebp-0x40]
  8406b9:	51                   	push   ecx
  8406ba:	68 24 a6 b1 00       	push   0xb1a624
  8406bf:	6a 00                	push   0x0
  8406c1:	50                   	push   eax
  8406c2:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8406c5:	ff d0                	call   eax
  8406c7:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8406ca:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  8406d0:	50                   	push   eax
  8406d1:	51                   	push   ecx
  8406d2:	ff d2                	call   edx
  8406d4:	d9 46 34             	fld    DWORD PTR [esi+0x34]
  8406d7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8406da:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  8406dd:	d9 46 38             	fld    DWORD PTR [esi+0x38]
  8406e0:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  8406e3:	8b 10                	mov    edx,DWORD PTR [eax]
  8406e5:	8b c8                	mov    ecx,eax
  8406e7:	8b 39                	mov    edi,DWORD PTR [ecx]
  8406e9:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  8406ec:	8d 4d c0             	lea    ecx,[ebp-0x40]
  8406ef:	51                   	push   ecx
  8406f0:	68 18 a6 b1 00       	push   0xb1a618
  8406f5:	6a 00                	push   0x0
  8406f7:	50                   	push   eax
  8406f8:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8406fb:	ff d0                	call   eax
  8406fd:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  840700:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  840706:	50                   	push   eax
  840707:	51                   	push   ecx
  840708:	ff d2                	call   edx
  84070a:	80 3d 18 ee b8 00 00 	cmp    BYTE PTR ds:0xb8ee18,0x0
  840711:	0f 84 db 06 00 00    	je     0x840df2
  840717:	8b 56 1c             	mov    edx,DWORD PTR [esi+0x1c]
  84071a:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  84071d:	8b 08                	mov    ecx,DWORD PTR [eax]
  84071f:	6a 14                	push   0x14
  840721:	6a 00                	push   0x0
  840723:	52                   	push   edx
  840724:	6a 00                	push   0x0
  840726:	50                   	push   eax
  840727:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  84072d:	ff d0                	call   eax
  84072f:	85 c0                	test   eax,eax
  840731:	0f 8c 88 fe ff ff    	jl     0x8405bf
  840737:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  84073a:	8b 11                	mov    edx,DWORD PTR [ecx]
  84073c:	8b 02                	mov    eax,DWORD PTR [edx]
  84073e:	ff d0                	call   eax
  840740:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  840743:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  840746:	8b 11                	mov    edx,DWORD PTR [ecx]
  840748:	8b 42 04             	mov    eax,DWORD PTR [edx+0x4]
  84074b:	ff d0                	call   eax
  84074d:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  840750:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  840753:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  840756:	d9 9d 70 ff ff ff    	fstp   DWORD PTR [ebp-0x90]
  84075c:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  84075f:	d9 9d 74 ff ff ff    	fstp   DWORD PTR [ebp-0x8c]
  840765:	d9 ee                	fldz
  840767:	d9 95 78 ff ff ff    	fst    DWORD PTR [ebp-0x88]
  84076d:	d9 9d 7c ff ff ff    	fstp   DWORD PTR [ebp-0x84]
  840773:	8b 11                	mov    edx,DWORD PTR [ecx]
  840775:	8b 42 08             	mov    eax,DWORD PTR [edx+0x8]
  840778:	ff d0                	call   eax
  84077a:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  84077d:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  840780:	8b 11                	mov    edx,DWORD PTR [ecx]
  840782:	8b 42 0c             	mov    eax,DWORD PTR [edx+0xc]
  840785:	ff d0                	call   eax
  840787:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  84078a:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  84078d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840790:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  840793:	8b c8                	mov    ecx,eax
  840795:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  840798:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  84079b:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  84079e:	d9 ee                	fldz
  8407a0:	d9 55 a8             	fst    DWORD PTR [ebp-0x58]
  8407a3:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  8407a6:	8b 39                	mov    edi,DWORD PTR [ecx]
  8407a8:	8b 10                	mov    edx,DWORD PTR [eax]
  8407aa:	8d 8d 70 ff ff ff    	lea    ecx,[ebp-0x90]
  8407b0:	51                   	push   ecx
  8407b1:	68 08 a6 b1 00       	push   0xb1a608
  8407b6:	6a 00                	push   0x0
  8407b8:	50                   	push   eax
  8407b9:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8407bc:	ff d0                	call   eax
  8407be:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8407c1:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  8407c7:	50                   	push   eax
  8407c8:	51                   	push   ecx
  8407c9:	ff d2                	call   edx
  8407cb:	85 c0                	test   eax,eax
  8407cd:	0f 8c ec fd ff ff    	jl     0x8405bf
  8407d3:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8407d6:	8b 10                	mov    edx,DWORD PTR [eax]
  8407d8:	8b c8                	mov    ecx,eax
  8407da:	8b 39                	mov    edi,DWORD PTR [ecx]
  8407dc:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  8407df:	8d 4d a0             	lea    ecx,[ebp-0x60]
  8407e2:	51                   	push   ecx
  8407e3:	68 f8 a5 b1 00       	push   0xb1a5f8
  8407e8:	6a 00                	push   0x0
  8407ea:	50                   	push   eax
  8407eb:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8407ee:	ff d0                	call   eax
  8407f0:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8407f3:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  8407f9:	50                   	push   eax
  8407fa:	51                   	push   ecx
  8407fb:	ff d2                	call   edx
  8407fd:	85 c0                	test   eax,eax
  8407ff:	0f 8c ba fd ff ff    	jl     0x8405bf
  840805:	8b 46 5c             	mov    eax,DWORD PTR [esi+0x5c]
  840808:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  84080b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84080e:	8b c8                	mov    ecx,eax
  840810:	8b 39                	mov    edi,DWORD PTR [ecx]
  840812:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840815:	8b 08                	mov    ecx,DWORD PTR [eax]
  840817:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  84081a:	68 e8 a5 b1 00       	push   0xb1a5e8
  84081f:	50                   	push   eax
  840820:	ff d2                	call   edx
  840822:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  840828:	50                   	push   eax
  840829:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84082c:	50                   	push   eax
  84082d:	ff d1                	call   ecx
  84082f:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840832:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  840835:	52                   	push   edx
  840836:	8b c8                	mov    ecx,eax
  840838:	8b 39                	mov    edi,DWORD PTR [ecx]
  84083a:	68 dc a5 b1 00       	push   0xb1a5dc
  84083f:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840842:	8b 08                	mov    ecx,DWORD PTR [eax]
  840844:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  840847:	6a 00                	push   0x0
  840849:	50                   	push   eax
  84084a:	ff d2                	call   edx
  84084c:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  840852:	50                   	push   eax
  840853:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  840856:	50                   	push   eax
  840857:	ff d1                	call   ecx
  840859:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84085c:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  84085f:	52                   	push   edx
  840860:	8b c8                	mov    ecx,eax
  840862:	8b 39                	mov    edi,DWORD PTR [ecx]
  840864:	68 d0 a5 b1 00       	push   0xb1a5d0
  840869:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  84086c:	8b 08                	mov    ecx,DWORD PTR [eax]
  84086e:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  840871:	6a 00                	push   0x0
  840873:	50                   	push   eax
  840874:	ff d2                	call   edx
  840876:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  84087c:	50                   	push   eax
  84087d:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  840880:	50                   	push   eax
  840881:	ff d1                	call   ecx
  840883:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  840886:	8b 17                	mov    edx,DWORD PTR [edi]
  840888:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  84088e:	6a 08                	push   0x8
  840890:	68 a8 00 00 00       	push   0xa8
  840895:	57                   	push   edi
  840896:	ff d0                	call   eax
  840898:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84089b:	8b 08                	mov    ecx,DWORD PTR [eax]
  84089d:	6a 01                	push   0x1
  84089f:	8d 55 e4             	lea    edx,[ebp-0x1c]
  8408a2:	52                   	push   edx
  8408a3:	50                   	push   eax
  8408a4:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  8408aa:	ff d0                	call   eax
  8408ac:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8408af:	8b 08                	mov    ecx,DWORD PTR [eax]
  8408b1:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  8408b7:	6a 00                	push   0x0
  8408b9:	50                   	push   eax
  8408ba:	ff d2                	call   edx
  8408bc:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8408bf:	8b 08                	mov    ecx,DWORD PTR [eax]
  8408c1:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  8408c7:	50                   	push   eax
  8408c8:	ff d2                	call   edx
  8408ca:	8b 07                	mov    eax,DWORD PTR [edi]
  8408cc:	6a 02                	push   0x2
  8408ce:	6a 00                	push   0x0
  8408d0:	6a 04                	push   0x4
  8408d2:	6a 00                	push   0x0
  8408d4:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  8408da:	6a 00                	push   0x0
  8408dc:	6a 04                	push   0x4
  8408de:	57                   	push   edi
  8408df:	ff d1                	call   ecx
  8408e1:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8408e4:	8b 10                	mov    edx,DWORD PTR [eax]
  8408e6:	50                   	push   eax
  8408e7:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8408ed:	ff d0                	call   eax
  8408ef:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8408f2:	8b 08                	mov    ecx,DWORD PTR [eax]
  8408f4:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8408fa:	50                   	push   eax
  8408fb:	ff d2                	call   edx
  8408fd:	8b 07                	mov    eax,DWORD PTR [edi]
  8408ff:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  840905:	6a 0f                	push   0xf
  840907:	68 a8 00 00 00       	push   0xa8
  84090c:	57                   	push   edi
  84090d:	ff d1                	call   ecx
  84090f:	8b 46 54             	mov    eax,DWORD PTR [esi+0x54]
  840912:	8b 4d b8             	mov    ecx,DWORD PTR [ebp-0x48]
  840915:	8b 17                	mov    edx,DWORD PTR [edi]
  840917:	8b 92 88 00 00 00    	mov    edx,DWORD PTR [edx+0x88]
  84091d:	6a 02                	push   0x2
  84091f:	6a 00                	push   0x0
  840921:	50                   	push   eax
  840922:	6a 00                	push   0x0
  840924:	51                   	push   ecx
  840925:	57                   	push   edi
  840926:	ff d2                	call   edx
  840928:	85 c0                	test   eax,eax
  84092a:	0f 8c 8f fc ff ff    	jl     0x8405bf
  840930:	8b 4e 50             	mov    ecx,DWORD PTR [esi+0x50]
  840933:	8b 07                	mov    eax,DWORD PTR [edi]
  840935:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  84093b:	6a 14                	push   0x14
  84093d:	6a 00                	push   0x0
  84093f:	51                   	push   ecx
  840940:	6a 00                	push   0x0
  840942:	57                   	push   edi
  840943:	ff d2                	call   edx
  840945:	85 c0                	test   eax,eax
  840947:	0f 8c 72 fc ff ff    	jl     0x8405bf
  84094d:	8b 46 5c             	mov    eax,DWORD PTR [esi+0x5c]
  840950:	8b 4e 70             	mov    ecx,DWORD PTR [esi+0x70]
  840953:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  840956:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840959:	8b 10                	mov    edx,DWORD PTR [eax]
  84095b:	68 bc a5 b1 00       	push   0xb1a5bc
  840960:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840963:	8b c8                	mov    ecx,eax
  840965:	8b 39                	mov    edi,DWORD PTR [ecx]
  840967:	50                   	push   eax
  840968:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  84096b:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  84096e:	ff d0                	call   eax
  840970:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840973:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  840979:	50                   	push   eax
  84097a:	51                   	push   ecx
  84097b:	ff d2                	call   edx
  84097d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840980:	8b 10                	mov    edx,DWORD PTR [eax]
  840982:	8b c8                	mov    ecx,eax
  840984:	8b 39                	mov    edi,DWORD PTR [ecx]
  840986:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840989:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  84098c:	51                   	push   ecx
  84098d:	68 dc a5 b1 00       	push   0xb1a5dc
  840992:	6a 00                	push   0x0
  840994:	50                   	push   eax
  840995:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840998:	ff d0                	call   eax
  84099a:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  84099d:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  8409a3:	50                   	push   eax
  8409a4:	51                   	push   ecx
  8409a5:	ff d2                	call   edx
  8409a7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8409aa:	8b 10                	mov    edx,DWORD PTR [eax]
  8409ac:	8b c8                	mov    ecx,eax
  8409ae:	8b 39                	mov    edi,DWORD PTR [ecx]
  8409b0:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  8409b3:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  8409b6:	51                   	push   ecx
  8409b7:	68 d0 a5 b1 00       	push   0xb1a5d0
  8409bc:	6a 00                	push   0x0
  8409be:	50                   	push   eax
  8409bf:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8409c2:	ff d0                	call   eax
  8409c4:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  8409c7:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  8409cd:	50                   	push   eax
  8409ce:	51                   	push   ecx
  8409cf:	ff d2                	call   edx
  8409d1:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8409d4:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  8409d7:	8b 07                	mov    eax,DWORD PTR [edi]
  8409d9:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  8409df:	51                   	push   ecx
  8409e0:	6a 00                	push   0x0
  8409e2:	57                   	push   edi
  8409e3:	ff d2                	call   edx
  8409e5:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8409eb:	e8 20 d7 fe ff       	call   0x82e110
  8409f0:	8b 08                	mov    ecx,DWORD PTR [eax]
  8409f2:	8d 55 bc             	lea    edx,[ebp-0x44]
  8409f5:	52                   	push   edx
  8409f6:	50                   	push   eax
  8409f7:	8b 81 a0 00 00 00    	mov    eax,DWORD PTR [ecx+0xa0]
  8409fd:	ff d0                	call   eax
  8409ff:	85 c0                	test   eax,eax
  840a01:	0f 8c b8 fb ff ff    	jl     0x8405bf
  840a07:	8b 0f                	mov    ecx,DWORD PTR [edi]
  840a09:	8b 91 9c 00 00 00    	mov    edx,DWORD PTR [ecx+0x9c]
  840a0f:	6a 00                	push   0x0
  840a11:	57                   	push   edi
  840a12:	ff d2                	call   edx
  840a14:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840a17:	8b 08                	mov    ecx,DWORD PTR [eax]
  840a19:	6a 01                	push   0x1
  840a1b:	8d 55 e4             	lea    edx,[ebp-0x1c]
  840a1e:	52                   	push   edx
  840a1f:	50                   	push   eax
  840a20:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  840a26:	ff d0                	call   eax
  840a28:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840a2b:	8b 08                	mov    ecx,DWORD PTR [eax]
  840a2d:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  840a33:	6a 00                	push   0x0
  840a35:	50                   	push   eax
  840a36:	ff d2                	call   edx
  840a38:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840a3b:	8b 08                	mov    ecx,DWORD PTR [eax]
  840a3d:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  840a43:	50                   	push   eax
  840a44:	ff d2                	call   edx
  840a46:	8b 07                	mov    eax,DWORD PTR [edi]
  840a48:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  840a4e:	6a 02                	push   0x2
  840a50:	6a 00                	push   0x0
  840a52:	6a 04                	push   0x4
  840a54:	6a 00                	push   0x0
  840a56:	6a 00                	push   0x0
  840a58:	6a 04                	push   0x4
  840a5a:	57                   	push   edi
  840a5b:	ff d1                	call   ecx
  840a5d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840a60:	8b 10                	mov    edx,DWORD PTR [eax]
  840a62:	50                   	push   eax
  840a63:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  840a69:	ff d0                	call   eax
  840a6b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840a6e:	8b 08                	mov    ecx,DWORD PTR [eax]
  840a70:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  840a76:	50                   	push   eax
  840a77:	ff d2                	call   edx
  840a79:	8b 4e 50             	mov    ecx,DWORD PTR [esi+0x50]
  840a7c:	8b 07                	mov    eax,DWORD PTR [edi]
  840a7e:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  840a84:	6a 14                	push   0x14
  840a86:	6a 00                	push   0x0
  840a88:	51                   	push   ecx
  840a89:	6a 00                	push   0x0
  840a8b:	57                   	push   edi
  840a8c:	ff d2                	call   edx
  840a8e:	85 c0                	test   eax,eax
  840a90:	0f 8c 29 fb ff ff    	jl     0x8405bf
  840a96:	8b 46 74             	mov    eax,DWORD PTR [esi+0x74]
  840a99:	8b 08                	mov    ecx,DWORD PTR [eax]
  840a9b:	8d 95 40 fe ff ff    	lea    edx,[ebp-0x1c0]
  840aa1:	52                   	push   edx
  840aa2:	50                   	push   eax
  840aa3:	8b 41 30             	mov    eax,DWORD PTR [ecx+0x30]
  840aa6:	ff d0                	call   eax
  840aa8:	d9 e8                	fld1
  840aaa:	51                   	push   ecx
  840aab:	d9 1c 24             	fstp   DWORD PTR [esp]
  840aae:	8d 8d 60 fe ff ff    	lea    ecx,[ebp-0x1a0]
  840ab4:	51                   	push   ecx
  840ab5:	8b 8d 58 fe ff ff    	mov    ecx,DWORD PTR [ebp-0x1a8]
  840abb:	8d 95 40 fd ff ff    	lea    edx,[ebp-0x2c0]
  840ac1:	52                   	push   edx
  840ac2:	8b 95 5c fe ff ff    	mov    edx,DWORD PTR [ebp-0x1a4]
  840ac8:	e8 73 f6 ff ff       	call   0x840140
  840acd:	8b 85 a0 fd ff ff    	mov    eax,DWORD PTR [ebp-0x260]
  840ad3:	8b 8d a4 fd ff ff    	mov    ecx,DWORD PTR [ebp-0x25c]
  840ad9:	8b 95 a8 fd ff ff    	mov    edx,DWORD PTR [ebp-0x258]
  840adf:	89 45 d0             	mov    DWORD PTR [ebp-0x30],eax
  840ae2:	8b 85 ac fd ff ff    	mov    eax,DWORD PTR [ebp-0x254]
  840ae8:	89 4d d4             	mov    DWORD PTR [ebp-0x2c],ecx
  840aeb:	8b 8d c0 fe ff ff    	mov    ecx,DWORD PTR [ebp-0x140]
  840af1:	89 55 d8             	mov    DWORD PTR [ebp-0x28],edx
  840af4:	8b 95 c4 fe ff ff    	mov    edx,DWORD PTR [ebp-0x13c]
  840afa:	89 45 dc             	mov    DWORD PTR [ebp-0x24],eax
  840afd:	8b 85 c8 fe ff ff    	mov    eax,DWORD PTR [ebp-0x138]
  840b03:	89 4d 90             	mov    DWORD PTR [ebp-0x70],ecx
  840b06:	8b 8d cc fe ff ff    	mov    ecx,DWORD PTR [ebp-0x134]
  840b0c:	89 55 94             	mov    DWORD PTR [ebp-0x6c],edx
  840b0f:	89 45 98             	mov    DWORD PTR [ebp-0x68],eax
  840b12:	89 4d 9c             	mov    DWORD PTR [ebp-0x64],ecx
  840b15:	33 ff                	xor    edi,edi
  840b17:	c7 45 fc 06 00 00 00 	mov    DWORD PTR [ebp-0x4],0x6
  840b1e:	8b ff                	mov    edi,edi
  840b20:	8d 94 3d 90 fd ff ff 	lea    edx,[ebp+edi*1-0x270]
  840b27:	52                   	push   edx
  840b28:	8d 8c 3d a0 fd ff ff 	lea    ecx,[ebp+edi*1-0x260]
  840b2f:	e8 fc 05 bc ff       	call   0x401130
  840b34:	8d 84 3d b0 fe ff ff 	lea    eax,[ebp+edi*1-0x150]
  840b3b:	50                   	push   eax
  840b3c:	8d 8c 3d c0 fe ff ff 	lea    ecx,[ebp+edi*1-0x140]
  840b43:	e8 e8 05 bc ff       	call   0x401130
  840b48:	83 ef 10             	sub    edi,0x10
  840b4b:	83 6d fc 01          	sub    DWORD PTR [ebp-0x4],0x1
  840b4f:	75 cf                	jne    0x840b20
  840b51:	d9 45 d0             	fld    DWORD PTR [ebp-0x30]
  840b54:	8d bd 40 fd ff ff    	lea    edi,[ebp-0x2c0]
  840b5a:	d9 9d 40 fd ff ff    	fstp   DWORD PTR [ebp-0x2c0]
  840b60:	c7 45 fc 10 00 00 00 	mov    DWORD PTR [ebp-0x4],0x10
  840b67:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  840b6a:	d9 9d 44 fd ff ff    	fstp   DWORD PTR [ebp-0x2bc]
  840b70:	d9 45 d8             	fld    DWORD PTR [ebp-0x28]
  840b73:	d9 9d 48 fd ff ff    	fstp   DWORD PTR [ebp-0x2b8]
  840b79:	d9 45 dc             	fld    DWORD PTR [ebp-0x24]
  840b7c:	d9 9d 4c fd ff ff    	fstp   DWORD PTR [ebp-0x2b4]
  840b82:	d9 45 90             	fld    DWORD PTR [ebp-0x70]
  840b85:	d9 9d 60 fe ff ff    	fstp   DWORD PTR [ebp-0x1a0]
  840b8b:	d9 45 94             	fld    DWORD PTR [ebp-0x6c]
  840b8e:	d9 9d 64 fe ff ff    	fstp   DWORD PTR [ebp-0x19c]
  840b94:	d9 45 98             	fld    DWORD PTR [ebp-0x68]
  840b97:	d9 9d 68 fe ff ff    	fstp   DWORD PTR [ebp-0x198]
  840b9d:	d9 45 9c             	fld    DWORD PTR [ebp-0x64]
  840ba0:	d9 9d 6c fe ff ff    	fstp   DWORD PTR [ebp-0x194]
  840ba6:	d9 46 3c             	fld    DWORD PTR [esi+0x3c]
  840ba9:	51                   	push   ecx
  840baa:	8b cf                	mov    ecx,edi
  840bac:	d9 1c 24             	fstp   DWORD PTR [esp]
  840baf:	e8 7c 53 ca ff       	call   0x4e5f30
  840bb4:	83 c7 10             	add    edi,0x10
  840bb7:	83 6d fc 01          	sub    DWORD PTR [ebp-0x4],0x1
  840bbb:	75 e9                	jne    0x840ba6
  840bbd:	8b 8e 80 00 00 00    	mov    ecx,DWORD PTR [esi+0x80]
  840bc3:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840bc6:	8b 56 74             	mov    edx,DWORD PTR [esi+0x74]
  840bc9:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  840bcc:	8b c8                	mov    ecx,eax
  840bce:	8b 39                	mov    edi,DWORD PTR [ecx]
  840bd0:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840bd3:	8b 08                	mov    ecx,DWORD PTR [eax]
  840bd5:	68 a4 a5 b1 00       	push   0xb1a5a4
  840bda:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  840bdd:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  840be0:	50                   	push   eax
  840be1:	ff d2                	call   edx
  840be3:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  840be9:	50                   	push   eax
  840bea:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  840bed:	50                   	push   eax
  840bee:	ff d1                	call   ecx
  840bf0:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840bf3:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  840bf6:	52                   	push   edx
  840bf7:	8b c8                	mov    ecx,eax
  840bf9:	8b 39                	mov    edi,DWORD PTR [ecx]
  840bfb:	68 98 a5 b1 00       	push   0xb1a598
  840c00:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840c03:	8b 08                	mov    ecx,DWORD PTR [eax]
  840c05:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  840c08:	6a 00                	push   0x0
  840c0a:	50                   	push   eax
  840c0b:	ff d2                	call   edx
  840c0d:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  840c13:	50                   	push   eax
  840c14:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  840c17:	50                   	push   eax
  840c18:	ff d1                	call   ecx
  840c1a:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  840c1d:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  840c20:	8b 10                	mov    edx,DWORD PTR [eax]
  840c22:	8b 92 94 00 00 00    	mov    edx,DWORD PTR [edx+0x94]
  840c28:	51                   	push   ecx
  840c29:	6a 00                	push   0x0
  840c2b:	50                   	push   eax
  840c2c:	ff d2                	call   edx
  840c2e:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840c31:	8b 10                	mov    edx,DWORD PTR [eax]
  840c33:	8b c8                	mov    ecx,eax
  840c35:	8b 39                	mov    edi,DWORD PTR [ecx]
  840c37:	6a 0d                	push   0xd
  840c39:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840c3c:	8d 8d 60 fe ff ff    	lea    ecx,[ebp-0x1a0]
  840c42:	51                   	push   ecx
  840c43:	68 88 a5 b1 00       	push   0xb1a588
  840c48:	6a 00                	push   0x0
  840c4a:	50                   	push   eax
  840c4b:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840c4e:	ff d0                	call   eax
  840c50:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840c53:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  840c59:	50                   	push   eax
  840c5a:	51                   	push   ecx
  840c5b:	ff d2                	call   edx
  840c5d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840c60:	8b 10                	mov    edx,DWORD PTR [eax]
  840c62:	8b c8                	mov    ecx,eax
  840c64:	8b 39                	mov    edi,DWORD PTR [ecx]
  840c66:	6a 0d                	push   0xd
  840c68:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840c6b:	8d 8d 40 fd ff ff    	lea    ecx,[ebp-0x2c0]
  840c71:	51                   	push   ecx
  840c72:	68 78 a5 b1 00       	push   0xb1a578
  840c77:	6a 00                	push   0x0
  840c79:	50                   	push   eax
  840c7a:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840c7d:	ff d0                	call   eax
  840c7f:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840c82:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  840c88:	50                   	push   eax
  840c89:	51                   	push   ecx
  840c8a:	ff d2                	call   edx
  840c8c:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840c8f:	8b 08                	mov    ecx,DWORD PTR [eax]
  840c91:	6a 01                	push   0x1
  840c93:	8d 55 e4             	lea    edx,[ebp-0x1c]
  840c96:	52                   	push   edx
  840c97:	50                   	push   eax
  840c98:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  840c9e:	ff d0                	call   eax
  840ca0:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ca3:	8b 08                	mov    ecx,DWORD PTR [eax]
  840ca5:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  840cab:	6a 00                	push   0x0
  840cad:	50                   	push   eax
  840cae:	ff d2                	call   edx
  840cb0:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840cb3:	8b 08                	mov    ecx,DWORD PTR [eax]
  840cb5:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  840cbb:	50                   	push   eax
  840cbc:	ff d2                	call   edx
  840cbe:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  840cc1:	8b 08                	mov    ecx,DWORD PTR [eax]
  840cc3:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  840cc9:	6a 02                	push   0x2
  840ccb:	6a 00                	push   0x0
  840ccd:	6a 04                	push   0x4
  840ccf:	6a 00                	push   0x0
  840cd1:	6a 00                	push   0x0
  840cd3:	6a 04                	push   0x4
  840cd5:	50                   	push   eax
  840cd6:	ff d2                	call   edx
  840cd8:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840cdb:	8b 08                	mov    ecx,DWORD PTR [eax]
  840cdd:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  840ce3:	50                   	push   eax
  840ce4:	ff d2                	call   edx
  840ce6:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ce9:	8b 08                	mov    ecx,DWORD PTR [eax]
  840ceb:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  840cf1:	50                   	push   eax
  840cf2:	ff d2                	call   edx
  840cf4:	8d bd 40 fd ff ff    	lea    edi,[ebp-0x2c0]
  840cfa:	c7 45 fc 10 00 00 00 	mov    DWORD PTR [ebp-0x4],0x10
  840d01:	d9 05 f8 9a aa 00    	fld    DWORD PTR ds:0xaa9af8
  840d07:	51                   	push   ecx
  840d08:	8b cf                	mov    ecx,edi
  840d0a:	d9 1c 24             	fstp   DWORD PTR [esp]
  840d0d:	e8 1e 52 ca ff       	call   0x4e5f30
  840d12:	83 c7 10             	add    edi,0x10
  840d15:	83 6d fc 01          	sub    DWORD PTR [ebp-0x4],0x1
  840d19:	75 e6                	jne    0x840d01
  840d1b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840d1e:	8b 10                	mov    edx,DWORD PTR [eax]
  840d20:	8b c8                	mov    ecx,eax
  840d22:	8b 39                	mov    edi,DWORD PTR [ecx]
  840d24:	6a 0d                	push   0xd
  840d26:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840d29:	8d 8d 40 fd ff ff    	lea    ecx,[ebp-0x2c0]
  840d2f:	51                   	push   ecx
  840d30:	68 78 a5 b1 00       	push   0xb1a578
  840d35:	6a 00                	push   0x0
  840d37:	50                   	push   eax
  840d38:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840d3b:	ff d0                	call   eax
  840d3d:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840d40:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  840d46:	50                   	push   eax
  840d47:	51                   	push   ecx
  840d48:	ff d2                	call   edx
  840d4a:	8b 86 84 00 00 00    	mov    eax,DWORD PTR [esi+0x84]
  840d50:	8b 4e 70             	mov    ecx,DWORD PTR [esi+0x70]
  840d53:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  840d56:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840d59:	8b 10                	mov    edx,DWORD PTR [eax]
  840d5b:	68 a4 a5 b1 00       	push   0xb1a5a4
  840d60:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840d63:	8b c8                	mov    ecx,eax
  840d65:	8b 39                	mov    edi,DWORD PTR [ecx]
  840d67:	50                   	push   eax
  840d68:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  840d6b:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840d6e:	ff d0                	call   eax
  840d70:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840d73:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  840d79:	50                   	push   eax
  840d7a:	51                   	push   ecx
  840d7b:	ff d2                	call   edx
  840d7d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840d80:	8b 10                	mov    edx,DWORD PTR [eax]
  840d82:	8b c8                	mov    ecx,eax
  840d84:	8b 39                	mov    edi,DWORD PTR [ecx]
  840d86:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840d89:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  840d8c:	51                   	push   ecx
  840d8d:	68 98 a5 b1 00       	push   0xb1a598
  840d92:	6a 00                	push   0x0
  840d94:	50                   	push   eax
  840d95:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840d98:	ff d0                	call   eax
  840d9a:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840d9d:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  840da3:	50                   	push   eax
  840da4:	51                   	push   ecx
  840da5:	ff d2                	call   edx
  840da7:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  840daa:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  840dad:	8b 07                	mov    eax,DWORD PTR [edi]
  840daf:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  840db5:	51                   	push   ecx
  840db6:	6a 00                	push   0x0
  840db8:	57                   	push   edi
  840db9:	ff d2                	call   edx
  840dbb:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840dbe:	8b 08                	mov    ecx,DWORD PTR [eax]
  840dc0:	6a 01                	push   0x1
  840dc2:	8d 55 e4             	lea    edx,[ebp-0x1c]
  840dc5:	52                   	push   edx
  840dc6:	50                   	push   eax
  840dc7:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  840dcd:	ff d0                	call   eax
  840dcf:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840dd2:	8b 08                	mov    ecx,DWORD PTR [eax]
  840dd4:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  840dda:	6a 00                	push   0x0
  840ddc:	50                   	push   eax
  840ddd:	ff d2                	call   edx
  840ddf:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840de2:	8b 08                	mov    ecx,DWORD PTR [eax]
  840de4:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  840dea:	50                   	push   eax
  840deb:	ff d2                	call   edx
  840ded:	e9 27 07 00 00       	jmp    0x841519
  840df2:	8b 4e 54             	mov    ecx,DWORD PTR [esi+0x54]
  840df5:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  840df8:	8b 55 b8             	mov    edx,DWORD PTR [ebp-0x48]
  840dfb:	8b 07                	mov    eax,DWORD PTR [edi]
  840dfd:	8b 80 88 00 00 00    	mov    eax,DWORD PTR [eax+0x88]
  840e03:	6a 02                	push   0x2
  840e05:	6a 00                	push   0x0
  840e07:	51                   	push   ecx
  840e08:	6a 00                	push   0x0
  840e0a:	52                   	push   edx
  840e0b:	57                   	push   edi
  840e0c:	ff d0                	call   eax
  840e0e:	85 c0                	test   eax,eax
  840e10:	0f 8c a9 f7 ff ff    	jl     0x8405bf
  840e16:	8b 56 50             	mov    edx,DWORD PTR [esi+0x50]
  840e19:	8b 0f                	mov    ecx,DWORD PTR [edi]
  840e1b:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  840e21:	6a 14                	push   0x14
  840e23:	6a 00                	push   0x0
  840e25:	52                   	push   edx
  840e26:	6a 00                	push   0x0
  840e28:	57                   	push   edi
  840e29:	ff d0                	call   eax
  840e2b:	85 c0                	test   eax,eax
  840e2d:	0f 8c 8c f7 ff ff    	jl     0x8405bf
  840e33:	8b 4e 5c             	mov    ecx,DWORD PTR [esi+0x5c]
  840e36:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840e39:	8b 56 70             	mov    edx,DWORD PTR [esi+0x70]
  840e3c:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  840e3f:	8b c8                	mov    ecx,eax
  840e41:	8b 39                	mov    edi,DWORD PTR [ecx]
  840e43:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840e46:	8b 08                	mov    ecx,DWORD PTR [eax]
  840e48:	68 64 a5 b1 00       	push   0xb1a564
  840e4d:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  840e50:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  840e53:	50                   	push   eax
  840e54:	ff d2                	call   edx
  840e56:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  840e5c:	50                   	push   eax
  840e5d:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  840e60:	50                   	push   eax
  840e61:	ff d1                	call   ecx
  840e63:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840e66:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  840e69:	52                   	push   edx
  840e6a:	8b c8                	mov    ecx,eax
  840e6c:	8b 39                	mov    edi,DWORD PTR [ecx]
  840e6e:	68 dc a5 b1 00       	push   0xb1a5dc
  840e73:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840e76:	8b 08                	mov    ecx,DWORD PTR [eax]
  840e78:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  840e7b:	6a 00                	push   0x0
  840e7d:	50                   	push   eax
  840e7e:	ff d2                	call   edx
  840e80:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  840e86:	50                   	push   eax
  840e87:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  840e8a:	50                   	push   eax
  840e8b:	ff d1                	call   ecx
  840e8d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840e90:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  840e93:	52                   	push   edx
  840e94:	8b c8                	mov    ecx,eax
  840e96:	8b 39                	mov    edi,DWORD PTR [ecx]
  840e98:	68 d0 a5 b1 00       	push   0xb1a5d0
  840e9d:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840ea0:	8b 08                	mov    ecx,DWORD PTR [eax]
  840ea2:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  840ea5:	6a 00                	push   0x0
  840ea7:	50                   	push   eax
  840ea8:	ff d2                	call   edx
  840eaa:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  840eb0:	50                   	push   eax
  840eb1:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  840eb4:	50                   	push   eax
  840eb5:	ff d1                	call   ecx
  840eb7:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  840eba:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  840ebd:	8b 17                	mov    edx,DWORD PTR [edi]
  840ebf:	8b 8a 94 00 00 00    	mov    ecx,DWORD PTR [edx+0x94]
  840ec5:	50                   	push   eax
  840ec6:	6a 00                	push   0x0
  840ec8:	57                   	push   edi
  840ec9:	ff d1                	call   ecx
  840ecb:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ece:	8b 10                	mov    edx,DWORD PTR [eax]
  840ed0:	8b 92 fc 00 00 00    	mov    edx,DWORD PTR [edx+0xfc]
  840ed6:	6a 01                	push   0x1
  840ed8:	8d 4d e4             	lea    ecx,[ebp-0x1c]
  840edb:	51                   	push   ecx
  840edc:	50                   	push   eax
  840edd:	ff d2                	call   edx
  840edf:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ee2:	8b 08                	mov    ecx,DWORD PTR [eax]
  840ee4:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  840eea:	6a 00                	push   0x0
  840eec:	50                   	push   eax
  840eed:	ff d2                	call   edx
  840eef:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ef2:	8b 08                	mov    ecx,DWORD PTR [eax]
  840ef4:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  840efa:	50                   	push   eax
  840efb:	ff d2                	call   edx
  840efd:	8b 07                	mov    eax,DWORD PTR [edi]
  840eff:	6a 02                	push   0x2
  840f01:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  840f07:	6a 00                	push   0x0
  840f09:	6a 04                	push   0x4
  840f0b:	6a 00                	push   0x0
  840f0d:	6a 00                	push   0x0
  840f0f:	6a 04                	push   0x4
  840f11:	57                   	push   edi
  840f12:	ff d1                	call   ecx
  840f14:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840f17:	8b 10                	mov    edx,DWORD PTR [eax]
  840f19:	50                   	push   eax
  840f1a:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  840f20:	ff d0                	call   eax
  840f22:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840f25:	8b 08                	mov    ecx,DWORD PTR [eax]
  840f27:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  840f2d:	50                   	push   eax
  840f2e:	ff d2                	call   edx
  840f30:	8b 4e 50             	mov    ecx,DWORD PTR [esi+0x50]
  840f33:	8b 07                	mov    eax,DWORD PTR [edi]
  840f35:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  840f3b:	6a 14                	push   0x14
  840f3d:	6a 00                	push   0x0
  840f3f:	51                   	push   ecx
  840f40:	6a 00                	push   0x0
  840f42:	57                   	push   edi
  840f43:	ff d2                	call   edx
  840f45:	85 c0                	test   eax,eax
  840f47:	0f 8c 72 f6 ff ff    	jl     0x8405bf
  840f4d:	8b 46 74             	mov    eax,DWORD PTR [esi+0x74]
  840f50:	8b 08                	mov    ecx,DWORD PTR [eax]
  840f52:	8d 95 40 fe ff ff    	lea    edx,[ebp-0x1c0]
  840f58:	52                   	push   edx
  840f59:	50                   	push   eax
  840f5a:	8b 41 30             	mov    eax,DWORD PTR [ecx+0x30]
  840f5d:	ff d0                	call   eax
  840f5f:	db 85 58 fe ff ff    	fild   DWORD PTR [ebp-0x1a8]
  840f65:	8b 8d 58 fe ff ff    	mov    ecx,DWORD PTR [ebp-0x1a8]
  840f6b:	85 c9                	test   ecx,ecx
  840f6d:	7d 06                	jge    0x840f75
  840f6f:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  840f75:	d9 e8                	fld1
  840f77:	8b 95 5c fe ff ff    	mov    edx,DWORD PTR [ebp-0x1a4]
  840f7d:	85 d2                	test   edx,edx
  840f7f:	d9 c0                	fld    st(0)
  840f81:	de f2                	fdivrp st(2),st
  840f83:	d9 c9                	fxch   st(1)
  840f85:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  840f88:	db 85 5c fe ff ff    	fild   DWORD PTR [ebp-0x1a4]
  840f8e:	7d 06                	jge    0x840f96
  840f90:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  840f96:	8b 86 80 00 00 00    	mov    eax,DWORD PTR [esi+0x80]
  840f9c:	de f9                	fdivp  st(1),st
  840f9e:	8b 4e 74             	mov    ecx,DWORD PTR [esi+0x74]
  840fa1:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  840fa4:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840fa7:	8b 10                	mov    edx,DWORD PTR [eax]
  840fa9:	68 54 a5 b1 00       	push   0xb1a554
  840fae:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  840fb1:	8b c8                	mov    ecx,eax
  840fb3:	8b 39                	mov    edi,DWORD PTR [ecx]
  840fb5:	50                   	push   eax
  840fb6:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  840fb9:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840fbc:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  840fbf:	ff d0                	call   eax
  840fc1:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840fc4:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  840fca:	50                   	push   eax
  840fcb:	51                   	push   ecx
  840fcc:	ff d2                	call   edx
  840fce:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840fd1:	8b 10                	mov    edx,DWORD PTR [eax]
  840fd3:	8b c8                	mov    ecx,eax
  840fd5:	8b 39                	mov    edi,DWORD PTR [ecx]
  840fd7:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  840fda:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  840fdd:	51                   	push   ecx
  840fde:	68 4c a5 b1 00       	push   0xb1a54c
  840fe3:	6a 00                	push   0x0
  840fe5:	50                   	push   eax
  840fe6:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  840fe9:	ff d0                	call   eax
  840feb:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  840fee:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  840ff4:	50                   	push   eax
  840ff5:	51                   	push   ecx
  840ff6:	ff d2                	call   edx
  840ff8:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  840ffb:	8b 10                	mov    edx,DWORD PTR [eax]
  840ffd:	8b c8                	mov    ecx,eax
  840fff:	8b 39                	mov    edi,DWORD PTR [ecx]
  841001:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  841004:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  841007:	51                   	push   ecx
  841008:	68 d0 a5 b1 00       	push   0xb1a5d0
  84100d:	6a 00                	push   0x0
  84100f:	50                   	push   eax
  841010:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841013:	ff d0                	call   eax
  841015:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  841018:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  84101e:	50                   	push   eax
  84101f:	51                   	push   ecx
  841020:	ff d2                	call   edx
  841022:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  841025:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  841028:	8b 08                	mov    ecx,DWORD PTR [eax]
  84102a:	52                   	push   edx
  84102b:	6a 00                	push   0x0
  84102d:	50                   	push   eax
  84102e:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  841034:	ff d0                	call   eax
  841036:	33 ff                	xor    edi,edi
  841038:	89 7d fc             	mov    DWORD PTR [ebp-0x4],edi
  84103b:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  84103e:	db 45 fc             	fild   DWORD PTR [ebp-0x4]
  841041:	85 d2                	test   edx,edx
  841043:	8d 8c 3d e0 fe ff ff 	lea    ecx,[ebp+edi*1-0x120]
  84104a:	7d 06                	jge    0x841052
  84104c:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  841052:	d8 4d f0             	fmul   DWORD PTR [ebp-0x10]
  841055:	8d 45 a0             	lea    eax,[ebp-0x60]
  841058:	50                   	push   eax
  841059:	d9 19                	fstp   DWORD PTR [ecx]
  84105b:	d9 ee                	fldz
  84105d:	d9 94 3d e4 fe ff ff 	fst    DWORD PTR [ebp+edi*1-0x11c]
  841064:	d9 94 3d e8 fe ff ff 	fst    DWORD PTR [ebp+edi*1-0x118]
  84106b:	d9 9c 3d ec fe ff ff 	fstp   DWORD PTR [ebp+edi*1-0x114]
  841072:	e8 19 77 c1 ff       	call   0x458790
  841077:	50                   	push   eax
  841078:	8d 8c 3d c0 fd ff ff 	lea    ecx,[ebp+edi*1-0x240]
  84107f:	e8 ac 00 bc ff       	call   0x401130
  841084:	83 45 fc 01          	add    DWORD PTR [ebp-0x4],0x1
  841088:	83 c7 10             	add    edi,0x10
  84108b:	83 ff 70             	cmp    edi,0x70
  84108e:	72 ab                	jb     0x84103b
  841090:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841093:	8b 10                	mov    edx,DWORD PTR [eax]
  841095:	8b c8                	mov    ecx,eax
  841097:	8b 39                	mov    edi,DWORD PTR [ecx]
  841099:	6a 03                	push   0x3
  84109b:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  84109e:	8d 8d f0 fe ff ff    	lea    ecx,[ebp-0x110]
  8410a4:	51                   	push   ecx
  8410a5:	68 40 a5 b1 00       	push   0xb1a540
  8410aa:	6a 00                	push   0x0
  8410ac:	50                   	push   eax
  8410ad:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8410b0:	ff d0                	call   eax
  8410b2:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  8410b5:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8410bb:	50                   	push   eax
  8410bc:	51                   	push   ecx
  8410bd:	ff d2                	call   edx
  8410bf:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8410c2:	8b 10                	mov    edx,DWORD PTR [eax]
  8410c4:	8b c8                	mov    ecx,eax
  8410c6:	8b 39                	mov    edi,DWORD PTR [ecx]
  8410c8:	6a 03                	push   0x3
  8410ca:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8410cd:	8d 8d d0 fd ff ff    	lea    ecx,[ebp-0x230]
  8410d3:	51                   	push   ecx
  8410d4:	68 30 a5 b1 00       	push   0xb1a530
  8410d9:	6a 00                	push   0x0
  8410db:	50                   	push   eax
  8410dc:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8410df:	ff d0                	call   eax
  8410e1:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  8410e4:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8410ea:	50                   	push   eax
  8410eb:	51                   	push   ecx
  8410ec:	ff d2                	call   edx
  8410ee:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8410f1:	8b 10                	mov    edx,DWORD PTR [eax]
  8410f3:	8b c8                	mov    ecx,eax
  8410f5:	8b 39                	mov    edi,DWORD PTR [ecx]
  8410f7:	6a 03                	push   0x3
  8410f9:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8410fc:	8d 8d 20 ff ff ff    	lea    ecx,[ebp-0xe0]
  841102:	51                   	push   ecx
  841103:	68 24 a5 b1 00       	push   0xb1a524
  841108:	6a 00                	push   0x0
  84110a:	50                   	push   eax
  84110b:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84110e:	ff d0                	call   eax
  841110:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  841113:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  841119:	50                   	push   eax
  84111a:	51                   	push   ecx
  84111b:	ff d2                	call   edx
  84111d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841120:	8b 10                	mov    edx,DWORD PTR [eax]
  841122:	8b c8                	mov    ecx,eax
  841124:	8b 39                	mov    edi,DWORD PTR [ecx]
  841126:	6a 03                	push   0x3
  841128:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  84112b:	8d 8d 00 fe ff ff    	lea    ecx,[ebp-0x200]
  841131:	51                   	push   ecx
  841132:	68 14 a5 b1 00       	push   0xb1a514
  841137:	6a 00                	push   0x0
  841139:	50                   	push   eax
  84113a:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84113d:	ff d0                	call   eax
  84113f:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  841142:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  841148:	50                   	push   eax
  841149:	51                   	push   ecx
  84114a:	ff d2                	call   edx
  84114c:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84114f:	8b 08                	mov    ecx,DWORD PTR [eax]
  841151:	6a 01                	push   0x1
  841153:	8d 55 e4             	lea    edx,[ebp-0x1c]
  841156:	52                   	push   edx
  841157:	50                   	push   eax
  841158:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  84115e:	ff d0                	call   eax
  841160:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841163:	8b 08                	mov    ecx,DWORD PTR [eax]
  841165:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  84116b:	6a 00                	push   0x0
  84116d:	50                   	push   eax
  84116e:	ff d2                	call   edx
  841170:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841173:	8b 08                	mov    ecx,DWORD PTR [eax]
  841175:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  84117b:	50                   	push   eax
  84117c:	ff d2                	call   edx
  84117e:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  841181:	8b 08                	mov    ecx,DWORD PTR [eax]
  841183:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  841189:	6a 02                	push   0x2
  84118b:	6a 00                	push   0x0
  84118d:	6a 04                	push   0x4
  84118f:	6a 00                	push   0x0
  841191:	6a 00                	push   0x0
  841193:	6a 04                	push   0x4
  841195:	50                   	push   eax
  841196:	ff d2                	call   edx
  841198:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84119b:	8b 08                	mov    ecx,DWORD PTR [eax]
  84119d:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  8411a3:	50                   	push   eax
  8411a4:	ff d2                	call   edx
  8411a6:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8411a9:	8b 08                	mov    ecx,DWORD PTR [eax]
  8411ab:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8411b1:	50                   	push   eax
  8411b2:	ff d2                	call   edx
  8411b4:	8b 86 84 00 00 00    	mov    eax,DWORD PTR [esi+0x84]
  8411ba:	8b 4e 70             	mov    ecx,DWORD PTR [esi+0x70]
  8411bd:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  8411c0:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8411c3:	8b 10                	mov    edx,DWORD PTR [eax]
  8411c5:	68 04 a5 b1 00       	push   0xb1a504
  8411ca:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  8411cd:	8b c8                	mov    ecx,eax
  8411cf:	8b 39                	mov    edi,DWORD PTR [ecx]
  8411d1:	50                   	push   eax
  8411d2:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  8411d5:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8411d8:	ff d0                	call   eax
  8411da:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  8411dd:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  8411e3:	50                   	push   eax
  8411e4:	51                   	push   ecx
  8411e5:	ff d2                	call   edx
  8411e7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8411ea:	8b 10                	mov    edx,DWORD PTR [eax]
  8411ec:	8b c8                	mov    ecx,eax
  8411ee:	8b 39                	mov    edi,DWORD PTR [ecx]
  8411f0:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8411f3:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  8411f6:	51                   	push   ecx
  8411f7:	68 4c a5 b1 00       	push   0xb1a54c
  8411fc:	6a 00                	push   0x0
  8411fe:	50                   	push   eax
  8411ff:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841202:	ff d0                	call   eax
  841204:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  841207:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  84120d:	50                   	push   eax
  84120e:	51                   	push   ecx
  84120f:	ff d2                	call   edx
  841211:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  841214:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  841217:	8b 08                	mov    ecx,DWORD PTR [eax]
  841219:	52                   	push   edx
  84121a:	6a 00                	push   0x0
  84121c:	50                   	push   eax
  84121d:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  841223:	ff d0                	call   eax
  841225:	d9 ee                	fldz
  841227:	d9 95 e0 fe ff ff    	fst    DWORD PTR [ebp-0x120]
  84122d:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841230:	dd 05 68 dd aa 00    	fld    QWORD PTR ds:0xaadd68
  841236:	d8 c9                	fmul   st,st(1)
  841238:	d9 9d e4 fe ff ff    	fstp   DWORD PTR [ebp-0x11c]
  84123e:	d9 c9                	fxch   st(1)
  841240:	d9 95 e8 fe ff ff    	fst    DWORD PTR [ebp-0x118]
  841246:	d9 95 ec fe ff ff    	fst    DWORD PTR [ebp-0x114]
  84124c:	d9 85 e4 fe ff ff    	fld    DWORD PTR [ebp-0x11c]
  841252:	d9 e0                	fchs
  841254:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  841257:	d9 05 8c e9 ae 00    	fld    DWORD PTR ds:0xaee98c
  84125d:	d9 95 c0 fd ff ff    	fst    DWORD PTR [ebp-0x240]
  841263:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  841266:	d9 9d c4 fd ff ff    	fstp   DWORD PTR [ebp-0x23c]
  84126c:	d9 95 c8 fd ff ff    	fst    DWORD PTR [ebp-0x238]
  841272:	d9 95 cc fd ff ff    	fst    DWORD PTR [ebp-0x234]
  841278:	d9 c9                	fxch   st(1)
  84127a:	d9 95 f0 fe ff ff    	fst    DWORD PTR [ebp-0x110]
  841280:	d9 95 f8 fe ff ff    	fst    DWORD PTR [ebp-0x108]
  841286:	d9 95 fc fe ff ff    	fst    DWORD PTR [ebp-0x104]
  84128c:	d9 ca                	fxch   st(2)
  84128e:	d9 95 f4 fe ff ff    	fst    DWORD PTR [ebp-0x10c]
  841294:	d9 85 f4 fe ff ff    	fld    DWORD PTR [ebp-0x10c]
  84129a:	d9 e0                	fchs
  84129c:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  84129f:	d9 c9                	fxch   st(1)
  8412a1:	d9 95 d0 fd ff ff    	fst    DWORD PTR [ebp-0x230]
  8412a7:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  8412aa:	d9 9d d4 fd ff ff    	fstp   DWORD PTR [ebp-0x22c]
  8412b0:	d9 95 d8 fd ff ff    	fst    DWORD PTR [ebp-0x228]
  8412b6:	d9 95 dc fd ff ff    	fst    DWORD PTR [ebp-0x224]
  8412bc:	d9 ca                	fxch   st(2)
  8412be:	d9 95 00 ff ff ff    	fst    DWORD PTR [ebp-0x100]
  8412c4:	d9 c1                	fld    st(1)
  8412c6:	dc c0                	fadd   st(0),st
  8412c8:	d9 9d 04 ff ff ff    	fstp   DWORD PTR [ebp-0xfc]
  8412ce:	d9 95 08 ff ff ff    	fst    DWORD PTR [ebp-0xf8]
  8412d4:	d9 95 0c ff ff ff    	fst    DWORD PTR [ebp-0xf4]
  8412da:	d9 85 04 ff ff ff    	fld    DWORD PTR [ebp-0xfc]
  8412e0:	d9 e0                	fchs
  8412e2:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  8412e5:	d9 ca                	fxch   st(2)
  8412e7:	d9 95 e0 fd ff ff    	fst    DWORD PTR [ebp-0x220]
  8412ed:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  8412f0:	d9 9d e4 fd ff ff    	fstp   DWORD PTR [ebp-0x21c]
  8412f6:	d9 95 e8 fd ff ff    	fst    DWORD PTR [ebp-0x218]
  8412fc:	d9 95 ec fd ff ff    	fst    DWORD PTR [ebp-0x214]
  841302:	d9 ca                	fxch   st(2)
  841304:	d9 95 10 ff ff ff    	fst    DWORD PTR [ebp-0xf0]
  84130a:	d9 c1                	fld    st(1)
  84130c:	dc 0d 88 16 ab 00    	fmul   QWORD PTR ds:0xab1688
  841312:	d9 9d 14 ff ff ff    	fstp   DWORD PTR [ebp-0xec]
  841318:	d9 95 18 ff ff ff    	fst    DWORD PTR [ebp-0xe8]
  84131e:	d9 95 1c ff ff ff    	fst    DWORD PTR [ebp-0xe4]
  841324:	d9 85 14 ff ff ff    	fld    DWORD PTR [ebp-0xec]
  84132a:	d9 e0                	fchs
  84132c:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  84132f:	d9 ca                	fxch   st(2)
  841331:	d9 95 f0 fd ff ff    	fst    DWORD PTR [ebp-0x210]
  841337:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  84133a:	d9 9d f4 fd ff ff    	fstp   DWORD PTR [ebp-0x20c]
  841340:	d9 95 f8 fd ff ff    	fst    DWORD PTR [ebp-0x208]
  841346:	d9 95 fc fd ff ff    	fst    DWORD PTR [ebp-0x204]
  84134c:	d9 ca                	fxch   st(2)
  84134e:	d9 95 20 ff ff ff    	fst    DWORD PTR [ebp-0xe0]
  841354:	d9 c1                	fld    st(1)
  841356:	dc 0d b8 44 ab 00    	fmul   QWORD PTR ds:0xab44b8
  84135c:	d9 9d 24 ff ff ff    	fstp   DWORD PTR [ebp-0xdc]
  841362:	d9 95 28 ff ff ff    	fst    DWORD PTR [ebp-0xd8]
  841368:	d9 95 2c ff ff ff    	fst    DWORD PTR [ebp-0xd4]
  84136e:	d9 85 24 ff ff ff    	fld    DWORD PTR [ebp-0xdc]
  841374:	d9 e0                	fchs
  841376:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  841379:	d9 ca                	fxch   st(2)
  84137b:	d9 95 00 fe ff ff    	fst    DWORD PTR [ebp-0x200]
  841381:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  841384:	d9 9d 04 fe ff ff    	fstp   DWORD PTR [ebp-0x1fc]
  84138a:	d9 95 08 fe ff ff    	fst    DWORD PTR [ebp-0x1f8]
  841390:	d9 95 0c fe ff ff    	fst    DWORD PTR [ebp-0x1f4]
  841396:	d9 ca                	fxch   st(2)
  841398:	d9 95 30 ff ff ff    	fst    DWORD PTR [ebp-0xd0]
  84139e:	d9 c1                	fld    st(1)
  8413a0:	dc 0d 60 7a af 00    	fmul   QWORD PTR ds:0xaf7a60
  8413a6:	d9 9d 34 ff ff ff    	fstp   DWORD PTR [ebp-0xcc]
  8413ac:	d9 95 38 ff ff ff    	fst    DWORD PTR [ebp-0xc8]
  8413b2:	d9 95 3c ff ff ff    	fst    DWORD PTR [ebp-0xc4]
  8413b8:	d9 85 34 ff ff ff    	fld    DWORD PTR [ebp-0xcc]
  8413be:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8413c1:	d9 e0                	fchs
  8413c3:	8b c8                	mov    ecx,eax
  8413c5:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  8413c8:	6a 03                	push   0x3
  8413ca:	d9 ca                	fxch   st(2)
  8413cc:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8413cf:	d9 95 10 fe ff ff    	fst    DWORD PTR [ebp-0x1f0]
  8413d5:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  8413d8:	d9 9d 14 fe ff ff    	fstp   DWORD PTR [ebp-0x1ec]
  8413de:	d9 95 18 fe ff ff    	fst    DWORD PTR [ebp-0x1e8]
  8413e4:	d9 95 1c fe ff ff    	fst    DWORD PTR [ebp-0x1e4]
  8413ea:	d9 ca                	fxch   st(2)
  8413ec:	d9 95 40 ff ff ff    	fst    DWORD PTR [ebp-0xc0]
  8413f2:	d9 c9                	fxch   st(1)
  8413f4:	dc 0d a0 4a ab 00    	fmul   QWORD PTR ds:0xab4aa0
  8413fa:	d9 9d 44 ff ff ff    	fstp   DWORD PTR [ebp-0xbc]
  841400:	d9 95 48 ff ff ff    	fst    DWORD PTR [ebp-0xb8]
  841406:	d9 9d 4c ff ff ff    	fstp   DWORD PTR [ebp-0xb4]
  84140c:	d9 85 44 ff ff ff    	fld    DWORD PTR [ebp-0xbc]
  841412:	d9 e0                	fchs
  841414:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  841417:	d9 95 20 fe ff ff    	fst    DWORD PTR [ebp-0x1e0]
  84141d:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  841420:	d9 9d 24 fe ff ff    	fstp   DWORD PTR [ebp-0x1dc]
  841426:	d9 95 28 fe ff ff    	fst    DWORD PTR [ebp-0x1d8]
  84142c:	d9 9d 2c fe ff ff    	fstp   DWORD PTR [ebp-0x1d4]
  841432:	8b 39                	mov    edi,DWORD PTR [ecx]
  841434:	8b 10                	mov    edx,DWORD PTR [eax]
  841436:	8d 8d f0 fe ff ff    	lea    ecx,[ebp-0x110]
  84143c:	51                   	push   ecx
  84143d:	68 40 a5 b1 00       	push   0xb1a540
  841442:	6a 00                	push   0x0
  841444:	50                   	push   eax
  841445:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841448:	ff d0                	call   eax
  84144a:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  84144d:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  841453:	50                   	push   eax
  841454:	51                   	push   ecx
  841455:	ff d2                	call   edx
  841457:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84145a:	8b 10                	mov    edx,DWORD PTR [eax]
  84145c:	8b c8                	mov    ecx,eax
  84145e:	8b 39                	mov    edi,DWORD PTR [ecx]
  841460:	6a 03                	push   0x3
  841462:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841465:	8d 8d d0 fd ff ff    	lea    ecx,[ebp-0x230]
  84146b:	51                   	push   ecx
  84146c:	68 30 a5 b1 00       	push   0xb1a530
  841471:	6a 00                	push   0x0
  841473:	50                   	push   eax
  841474:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841477:	ff d0                	call   eax
  841479:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  84147c:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  841482:	50                   	push   eax
  841483:	51                   	push   ecx
  841484:	ff d2                	call   edx
  841486:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841489:	8b 10                	mov    edx,DWORD PTR [eax]
  84148b:	8b c8                	mov    ecx,eax
  84148d:	8b 39                	mov    edi,DWORD PTR [ecx]
  84148f:	6a 03                	push   0x3
  841491:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841494:	8d 8d 20 ff ff ff    	lea    ecx,[ebp-0xe0]
  84149a:	51                   	push   ecx
  84149b:	68 24 a5 b1 00       	push   0xb1a524
  8414a0:	6a 00                	push   0x0
  8414a2:	50                   	push   eax
  8414a3:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8414a6:	ff d0                	call   eax
  8414a8:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  8414ab:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8414b1:	50                   	push   eax
  8414b2:	51                   	push   ecx
  8414b3:	ff d2                	call   edx
  8414b5:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8414b8:	8b c8                	mov    ecx,eax
  8414ba:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8414bd:	8b 39                	mov    edi,DWORD PTR [ecx]
  8414bf:	8b 10                	mov    edx,DWORD PTR [eax]
  8414c1:	6a 03                	push   0x3
  8414c3:	8d 8d 00 fe ff ff    	lea    ecx,[ebp-0x200]
  8414c9:	51                   	push   ecx
  8414ca:	68 14 a5 b1 00       	push   0xb1a514
  8414cf:	6a 00                	push   0x0
  8414d1:	50                   	push   eax
  8414d2:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8414d5:	ff d0                	call   eax
  8414d7:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  8414da:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8414e0:	50                   	push   eax
  8414e1:	51                   	push   ecx
  8414e2:	ff d2                	call   edx
  8414e4:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8414e7:	8b 08                	mov    ecx,DWORD PTR [eax]
  8414e9:	6a 01                	push   0x1
  8414eb:	8d 55 e4             	lea    edx,[ebp-0x1c]
  8414ee:	52                   	push   edx
  8414ef:	50                   	push   eax
  8414f0:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  8414f6:	ff d0                	call   eax
  8414f8:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8414fb:	8b 08                	mov    ecx,DWORD PTR [eax]
  8414fd:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  841503:	6a 00                	push   0x0
  841505:	50                   	push   eax
  841506:	ff d2                	call   edx
  841508:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84150b:	8b 08                	mov    ecx,DWORD PTR [eax]
  84150d:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  841513:	50                   	push   eax
  841514:	ff d2                	call   edx
  841516:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  841519:	8b 07                	mov    eax,DWORD PTR [edi]
  84151b:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  841521:	6a 02                	push   0x2
  841523:	6a 00                	push   0x0
  841525:	6a 04                	push   0x4
  841527:	6a 00                	push   0x0
  841529:	6a 00                	push   0x0
  84152b:	6a 04                	push   0x4
  84152d:	57                   	push   edi
  84152e:	ff d1                	call   ecx
  841530:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841533:	8b 10                	mov    edx,DWORD PTR [eax]
  841535:	50                   	push   eax
  841536:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  84153c:	ff d0                	call   eax
  84153e:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841541:	8b 08                	mov    ecx,DWORD PTR [eax]
  841543:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  841549:	50                   	push   eax
  84154a:	ff d2                	call   edx
  84154c:	8b 4e 1c             	mov    ecx,DWORD PTR [esi+0x1c]
  84154f:	8b 07                	mov    eax,DWORD PTR [edi]
  841551:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  841557:	6a 14                	push   0x14
  841559:	6a 00                	push   0x0
  84155b:	51                   	push   ecx
  84155c:	6a 00                	push   0x0
  84155e:	57                   	push   edi
  84155f:	ff d2                	call   edx
  841561:	85 c0                	test   eax,eax
  841563:	0f 8c 56 f0 ff ff    	jl     0x8405bf
  841569:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  84156c:	8b 01                	mov    eax,DWORD PTR [ecx]
  84156e:	8b 10                	mov    edx,DWORD PTR [eax]
  841570:	ff d2                	call   edx
  841572:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841575:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  841578:	8b 01                	mov    eax,DWORD PTR [ecx]
  84157a:	8b 50 04             	mov    edx,DWORD PTR [eax+0x4]
  84157d:	ff d2                	call   edx
  84157f:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  841582:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841585:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  841588:	d9 9d 60 ff ff ff    	fstp   DWORD PTR [ebp-0xa0]
  84158e:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  841591:	d9 9d 64 ff ff ff    	fstp   DWORD PTR [ebp-0x9c]
  841597:	d9 ee                	fldz
  841599:	d9 95 68 ff ff ff    	fst    DWORD PTR [ebp-0x98]
  84159f:	d9 9d 6c ff ff ff    	fstp   DWORD PTR [ebp-0x94]
  8415a5:	8b 01                	mov    eax,DWORD PTR [ecx]
  8415a7:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  8415aa:	ff d2                	call   edx
  8415ac:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  8415af:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  8415b2:	8b 01                	mov    eax,DWORD PTR [ecx]
  8415b4:	8b 50 0c             	mov    edx,DWORD PTR [eax+0xc]
  8415b7:	ff d2                	call   edx
  8415b9:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  8415bc:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  8415bf:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8415c2:	d9 5d 80             	fstp   DWORD PTR [ebp-0x80]
  8415c5:	8b c8                	mov    ecx,eax
  8415c7:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  8415ca:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8415cd:	d9 5d 84             	fstp   DWORD PTR [ebp-0x7c]
  8415d0:	d9 ee                	fldz
  8415d2:	d9 55 88             	fst    DWORD PTR [ebp-0x78]
  8415d5:	d9 5d 8c             	fstp   DWORD PTR [ebp-0x74]
  8415d8:	8b 39                	mov    edi,DWORD PTR [ecx]
  8415da:	8b 10                	mov    edx,DWORD PTR [eax]
  8415dc:	8d 8d 60 ff ff ff    	lea    ecx,[ebp-0xa0]
  8415e2:	51                   	push   ecx
  8415e3:	68 08 a6 b1 00       	push   0xb1a608
  8415e8:	6a 00                	push   0x0
  8415ea:	50                   	push   eax
  8415eb:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8415ee:	ff d0                	call   eax
  8415f0:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  8415f3:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  8415f9:	50                   	push   eax
  8415fa:	51                   	push   ecx
  8415fb:	ff d2                	call   edx
  8415fd:	85 c0                	test   eax,eax
  8415ff:	0f 8c ba ef ff ff    	jl     0x8405bf
  841605:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841608:	8b 10                	mov    edx,DWORD PTR [eax]
  84160a:	8b c8                	mov    ecx,eax
  84160c:	8b 39                	mov    edi,DWORD PTR [ecx]
  84160e:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841611:	8d 4d 80             	lea    ecx,[ebp-0x80]
  841614:	51                   	push   ecx
  841615:	68 f8 a5 b1 00       	push   0xb1a5f8
  84161a:	6a 00                	push   0x0
  84161c:	50                   	push   eax
  84161d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841620:	ff d0                	call   eax
  841622:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  841625:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  84162b:	50                   	push   eax
  84162c:	51                   	push   ecx
  84162d:	ff d2                	call   edx
  84162f:	85 c0                	test   eax,eax
  841631:	0f 8c 88 ef ff ff    	jl     0x8405bf
  841637:	80 3d 18 ee b8 00 00 	cmp    BYTE PTR ds:0xb8ee18,0x0
  84163e:	8b 46 5c             	mov    eax,DWORD PTR [esi+0x5c]
  841641:	8b 8e 80 00 00 00    	mov    ecx,DWORD PTR [esi+0x80]
  841647:	8b 55 b8             	mov    edx,DWORD PTR [ebp-0x48]
  84164a:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  84164d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841650:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  841653:	8b c8                	mov    ecx,eax
  841655:	8b 39                	mov    edi,DWORD PTR [ecx]
  841657:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  84165a:	74 19                	je     0x841675
  84165c:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  84165f:	8b 08                	mov    ecx,DWORD PTR [eax]
  841661:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  841664:	68 f4 a4 b1 00       	push   0xb1a4f4
  841669:	50                   	push   eax
  84166a:	ff d2                	call   edx
  84166c:	50                   	push   eax
  84166d:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  841670:	e9 47 01 00 00       	jmp    0x8417bc
  841675:	80 be 90 00 00 00 00 	cmp    BYTE PTR [esi+0x90],0x0
  84167c:	0f 84 26 01 00 00    	je     0x8417a8
  841682:	8b 15 58 60 c2 00    	mov    edx,DWORD PTR ds:0xc26058
  841688:	d9 82 08 07 00 00    	fld    DWORD PTR [edx+0x708]
  84168e:	51                   	push   ecx
  84168f:	d9 1c 24             	fstp   DWORD PTR [esp]
  841692:	68 7c 99 b1 00       	push   0xb1997c
  841697:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  84169a:	8b 08                	mov    ecx,DWORD PTR [eax]
  84169c:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  84169f:	6a 00                	push   0x0
  8416a1:	50                   	push   eax
  8416a2:	ff d2                	call   edx
  8416a4:	8b 4f 78             	mov    ecx,DWORD PTR [edi+0x78]
  8416a7:	50                   	push   eax
  8416a8:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  8416ab:	50                   	push   eax
  8416ac:	ff d1                	call   ecx
  8416ae:	8b 56 28             	mov    edx,DWORD PTR [esi+0x28]
  8416b1:	8b 8e 94 00 00 00    	mov    ecx,DWORD PTR [esi+0x94]
  8416b7:	8b c2                	mov    eax,edx
  8416b9:	8b 38                	mov    edi,DWORD PTR [eax]
  8416bb:	89 55 f8             	mov    DWORD PTR [ebp-0x8],edx
  8416be:	89 45 f0             	mov    DWORD PTR [ebp-0x10],eax
  8416c1:	e8 2a 77 ff ff       	call   0x838df0
  8416c6:	50                   	push   eax
  8416c7:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  8416ca:	8b 08                	mov    ecx,DWORD PTR [eax]
  8416cc:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8416cf:	68 e0 a4 b1 00       	push   0xb1a4e0
  8416d4:	6a 00                	push   0x0
  8416d6:	50                   	push   eax
  8416d7:	ff d2                	call   edx
  8416d9:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  8416df:	50                   	push   eax
  8416e0:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  8416e3:	50                   	push   eax
  8416e4:	ff d1                	call   ecx
  8416e6:	d9 86 98 00 00 00    	fld    DWORD PTR [esi+0x98]
  8416ec:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8416ef:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  8416f2:	d9 86 9c 00 00 00    	fld    DWORD PTR [esi+0x9c]
  8416f8:	8d 55 a0             	lea    edx,[ebp-0x60]
  8416fb:	d8 a6 98 00 00 00    	fsub   DWORD PTR [esi+0x98]
  841701:	52                   	push   edx
  841702:	8b c8                	mov    ecx,eax
  841704:	68 cc a4 b1 00       	push   0xb1a4cc
  841709:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  84170c:	8b 39                	mov    edi,DWORD PTR [ecx]
  84170e:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841711:	8b 08                	mov    ecx,DWORD PTR [eax]
  841713:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  841716:	6a 00                	push   0x0
  841718:	50                   	push   eax
  841719:	ff d2                	call   edx
  84171b:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  841721:	50                   	push   eax
  841722:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  841725:	50                   	push   eax
  841726:	ff d1                	call   ecx
  841728:	d9 86 a0 00 00 00    	fld    DWORD PTR [esi+0xa0]
  84172e:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841731:	8b 10                	mov    edx,DWORD PTR [eax]
  841733:	8b c8                	mov    ecx,eax
  841735:	8b 39                	mov    edi,DWORD PTR [ecx]
  841737:	51                   	push   ecx
  841738:	d9 1c 24             	fstp   DWORD PTR [esp]
  84173b:	68 b4 a4 b1 00       	push   0xb1a4b4
  841740:	6a 00                	push   0x0
  841742:	50                   	push   eax
  841743:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  841746:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841749:	ff d0                	call   eax
  84174b:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  84174e:	8b 57 78             	mov    edx,DWORD PTR [edi+0x78]
  841751:	50                   	push   eax
  841752:	51                   	push   ecx
  841753:	ff d2                	call   edx
  841755:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841758:	8b c8                	mov    ecx,eax
  84175a:	8b 39                	mov    edi,DWORD PTR [ecx]
  84175c:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  84175f:	51                   	push   ecx
  841760:	d9 86 a4 00 00 00    	fld    DWORD PTR [esi+0xa4]
  841766:	8b 08                	mov    ecx,DWORD PTR [eax]
  841768:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  84176b:	d9 1c 24             	fstp   DWORD PTR [esp]
  84176e:	68 a4 a4 b1 00       	push   0xb1a4a4
  841773:	6a 00                	push   0x0
  841775:	50                   	push   eax
  841776:	ff d2                	call   edx
  841778:	8b 4f 78             	mov    ecx,DWORD PTR [edi+0x78]
  84177b:	50                   	push   eax
  84177c:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  84177f:	50                   	push   eax
  841780:	ff d1                	call   ecx
  841782:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841785:	8b 10                	mov    edx,DWORD PTR [eax]
  841787:	8b c8                	mov    ecx,eax
  841789:	8b 39                	mov    edi,DWORD PTR [ecx]
  84178b:	68 88 a4 b1 00       	push   0xb1a488
  841790:	50                   	push   eax
  841791:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  841794:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841797:	ff d0                	call   eax
  841799:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  84179c:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  8417a2:	50                   	push   eax
  8417a3:	51                   	push   ecx
  8417a4:	ff d2                	call   edx
  8417a6:	eb 1d                	jmp    0x8417c5
  8417a8:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8417ab:	8b 08                	mov    ecx,DWORD PTR [eax]
  8417ad:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  8417b0:	68 78 a4 b1 00       	push   0xb1a478
  8417b5:	50                   	push   eax
  8417b6:	ff d2                	call   edx
  8417b8:	50                   	push   eax
  8417b9:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  8417bc:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  8417c2:	50                   	push   eax
  8417c3:	ff d1                	call   ecx
  8417c5:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8417c8:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  8417cb:	52                   	push   edx
  8417cc:	8b c8                	mov    ecx,eax
  8417ce:	8b 39                	mov    edi,DWORD PTR [ecx]
  8417d0:	68 dc a5 b1 00       	push   0xb1a5dc
  8417d5:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8417d8:	8b 08                	mov    ecx,DWORD PTR [eax]
  8417da:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8417dd:	6a 00                	push   0x0
  8417df:	50                   	push   eax
  8417e0:	ff d2                	call   edx
  8417e2:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  8417e8:	50                   	push   eax
  8417e9:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  8417ec:	50                   	push   eax
  8417ed:	ff d1                	call   ecx
  8417ef:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8417f2:	8b 55 f4             	mov    edx,DWORD PTR [ebp-0xc]
  8417f5:	52                   	push   edx
  8417f6:	8b c8                	mov    ecx,eax
  8417f8:	8b 39                	mov    edi,DWORD PTR [ecx]
  8417fa:	68 4c a5 b1 00       	push   0xb1a54c
  8417ff:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  841802:	8b 08                	mov    ecx,DWORD PTR [eax]
  841804:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  841807:	6a 00                	push   0x0
  841809:	50                   	push   eax
  84180a:	ff d2                	call   edx
  84180c:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  841812:	50                   	push   eax
  841813:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  841816:	50                   	push   eax
  841817:	ff d1                	call   ecx
  841819:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84181c:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  84181f:	52                   	push   edx
  841820:	8b c8                	mov    ecx,eax
  841822:	8b 39                	mov    edi,DWORD PTR [ecx]
  841824:	68 d0 a5 b1 00       	push   0xb1a5d0
  841829:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  84182c:	8b 08                	mov    ecx,DWORD PTR [eax]
  84182e:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  841831:	6a 00                	push   0x0
  841833:	50                   	push   eax
  841834:	ff d2                	call   edx
  841836:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  84183c:	50                   	push   eax
  84183d:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  841840:	50                   	push   eax
  841841:	ff d1                	call   ecx
  841843:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  841846:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  841849:	8b 17                	mov    edx,DWORD PTR [edi]
  84184b:	8b 8a 94 00 00 00    	mov    ecx,DWORD PTR [edx+0x94]
  841851:	50                   	push   eax
  841852:	6a 00                	push   0x0
  841854:	57                   	push   edi
  841855:	ff d1                	call   ecx
  841857:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84185a:	8b 10                	mov    edx,DWORD PTR [eax]
  84185c:	8b 92 fc 00 00 00    	mov    edx,DWORD PTR [edx+0xfc]
  841862:	6a 01                	push   0x1
  841864:	8d 4d e4             	lea    ecx,[ebp-0x1c]
  841867:	51                   	push   ecx
  841868:	50                   	push   eax
  841869:	ff d2                	call   edx
  84186b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84186e:	8b 08                	mov    ecx,DWORD PTR [eax]
  841870:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  841876:	6a 00                	push   0x0
  841878:	50                   	push   eax
  841879:	ff d2                	call   edx
  84187b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84187e:	8b 08                	mov    ecx,DWORD PTR [eax]
  841880:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  841886:	50                   	push   eax
  841887:	ff d2                	call   edx
  841889:	8b 07                	mov    eax,DWORD PTR [edi]
  84188b:	6a 02                	push   0x2
  84188d:	6a 00                	push   0x0
  84188f:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  841895:	6a 04                	push   0x4
  841897:	6a 00                	push   0x0
  841899:	6a 00                	push   0x0
  84189b:	6a 04                	push   0x4
  84189d:	57                   	push   edi
  84189e:	ff d1                	call   ecx
  8418a0:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8418a3:	8b 10                	mov    edx,DWORD PTR [eax]
  8418a5:	50                   	push   eax
  8418a6:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8418ac:	ff d0                	call   eax
  8418ae:	8b 76 28             	mov    esi,DWORD PTR [esi+0x28]
  8418b1:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8418b3:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8418b9:	56                   	push   esi
  8418ba:	ff d2                	call   edx
  8418bc:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8418c2:	8b 01                	mov    eax,DWORD PTR [ecx]
  8418c4:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  8418ca:	33 d2                	xor    edx,edx
  8418cc:	ff d0                	call   eax
  8418ce:	8b c8                	mov    ecx,eax
  8418d0:	e8 7b 1a 01 00       	call   0x853350
  8418d5:	8b 45 bc             	mov    eax,DWORD PTR [ebp-0x44]
  8418d8:	85 c0                	test   eax,eax
  8418da:	74 1f                	je     0x8418fb
  8418dc:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8418de:	8b 91 9c 00 00 00    	mov    edx,DWORD PTR [ecx+0x9c]
  8418e4:	50                   	push   eax
  8418e5:	57                   	push   edi
  8418e6:	ff d2                	call   edx
  8418e8:	85 c0                	test   eax,eax
  8418ea:	0f 8c cf ec ff ff    	jl     0x8405bf
  8418f0:	8b 45 bc             	mov    eax,DWORD PTR [ebp-0x44]
  8418f3:	8b 08                	mov    ecx,DWORD PTR [eax]
  8418f5:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  8418f8:	50                   	push   eax
  8418f9:	ff d2                	call   edx
  8418fb:	e8 22 1d 0e 00       	call   0x923622
  841900:	5f                   	pop    edi
  841901:	b0 01                	mov    al,0x1
  841903:	5e                   	pop    esi
  841904:	8b e5                	mov    esp,ebp
  841906:	5d                   	pop    ebp
  841907:	8b e3                	mov    esp,ebx
  841909:	5b                   	pop    ebx
  84190a:	c3                   	ret
```

### `0x00841ae0..0x00842ad9` — sites `0x00842140`, `0x0084252b`, `0x00842896`, `0x00842aab`

```asm
  841ae0:	53                   	push   ebx
  841ae1:	8b dc                	mov    ebx,esp
  841ae3:	83 ec 08             	sub    esp,0x8
  841ae6:	83 e4 f0             	and    esp,0xfffffff0
  841ae9:	83 c4 04             	add    esp,0x4
  841aec:	55                   	push   ebp
  841aed:	8b 6b 04             	mov    ebp,DWORD PTR [ebx+0x4]
  841af0:	89 6c 24 04          	mov    DWORD PTR [esp+0x4],ebp
  841af4:	8b ec                	mov    ebp,esp
  841af6:	81 ec f8 01 00 00    	sub    esp,0x1f8
  841afc:	56                   	push   esi
  841afd:	57                   	push   edi
  841afe:	8b f1                	mov    esi,ecx
  841b00:	80 7e 26 00          	cmp    BYTE PTR [esi+0x26],0x0
  841b04:	8b fa                	mov    edi,edx
  841b06:	89 7d e8             	mov    DWORD PTR [ebp-0x18],edi
  841b09:	0f 84 f6 03 00 00    	je     0x841f05
  841b0f:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  841b15:	8b 01                	mov    eax,DWORD PTR [ecx]
  841b17:	8b 90 70 02 00 00    	mov    edx,DWORD PTR [eax+0x270]
  841b1d:	ff d2                	call   edx
  841b1f:	68 88 a7 b1 00       	push   0xb1a788
  841b24:	68 00 00 ff ff       	push   0xffff0000
  841b29:	88 45 df             	mov    BYTE PTR [ebp-0x21],al
  841b2c:	e8 f7 1a 0e 00       	call   0x923628
  841b31:	d9 ee                	fldz
  841b33:	80 7d df 00          	cmp    BYTE PTR [ebp-0x21],0x0
  841b37:	d9 55 f4             	fst    DWORD PTR [ebp-0xc]
  841b3a:	a1 58 60 c2 00       	mov    eax,ds:0xc26058
  841b3f:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841b42:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  841b45:	74 3e                	je     0x841b85
  841b47:	d9 86 d4 00 00 00    	fld    DWORD PTR [esi+0xd4]
  841b4d:	8d 88 ec 06 00 00    	lea    ecx,[eax+0x6ec]
  841b53:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841b56:	d9 86 d8 00 00 00    	fld    DWORD PTR [esi+0xd8]
  841b5c:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841b5f:	e8 6c d5 bc ff       	call   0x40f0d0
  841b64:	85 c0                	test   eax,eax
  841b66:	89 45 bc             	mov    DWORD PTR [ebp-0x44],eax
  841b69:	db 45 bc             	fild   DWORD PTR [ebp-0x44]
  841b6c:	7d 06                	jge    0x841b74
  841b6e:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  841b74:	dc 0d c0 38 ab 00    	fmul   QWORD PTR ds:0xab38c0
  841b7a:	d9 9e d0 00 00 00    	fstp   DWORD PTR [esi+0xd0]
  841b80:	e9 69 01 00 00       	jmp    0x841cee
  841b85:	8b cf                	mov    ecx,edi
  841b87:	e8 34 2d 00 00       	call   0x8448c0
  841b8c:	50                   	push   eax
  841b8d:	8b cf                	mov    ecx,edi
  841b8f:	e8 8c 35 00 00       	call   0x845120
  841b94:	50                   	push   eax
  841b95:	8d 85 50 ff ff ff    	lea    eax,[ebp-0xb0]
  841b9b:	50                   	push   eax
  841b9c:	e8 dd bd d3 ff       	call   0x57d97e
  841ba1:	8d 8d 50 ff ff ff    	lea    ecx,[ebp-0xb0]
  841ba7:	51                   	push   ecx
  841ba8:	8d 96 b0 00 00 00    	lea    edx,[esi+0xb0]
  841bae:	52                   	push   edx
  841baf:	8d 45 a0             	lea    eax,[ebp-0x60]
  841bb2:	50                   	push   eax
  841bb3:	e8 7c 1a 0e 00       	call   0x923634
  841bb8:	8b 07                	mov    eax,DWORD PTR [edi]
  841bba:	8b 40 1c             	mov    eax,DWORD PTR [eax+0x1c]
  841bbd:	8d 55 c0             	lea    edx,[ebp-0x40]
  841bc0:	8b cf                	mov    ecx,edi
  841bc2:	ff d0                	call   eax
  841bc4:	d9 e8                	fld1
  841bc6:	d8 5d a8             	fcomp  DWORD PTR [ebp-0x58]
  841bc9:	df e0                	fnstsw ax
  841bcb:	f6 c4 05             	test   ah,0x5
  841bce:	0f 8a e4 00 00 00    	jp     0x841cb8
  841bd4:	d9 45 a0             	fld    DWORD PTR [ebp-0x60]
  841bd7:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  841bdd:	d9 e0                	fchs
  841bdf:	d9 45 ac             	fld    DWORD PTR [ebp-0x54]
  841be2:	d9 c0                	fld    st(0)
  841be4:	de fa                	fdivp  st(2),st
  841be6:	d9 c9                	fxch   st(1)
  841be8:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841beb:	d8 7d a4             	fdivr  DWORD PTR [ebp-0x5c]
  841bee:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841bf1:	e8 ba e1 ff ff       	call   0x83fdb0
  841bf6:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841bf9:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841bfc:	d9 c0                	fld    st(0)
  841bfe:	d8 a6 d0 00 00 00    	fsub   DWORD PTR [esi+0xd0]
  841c04:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841c07:	d9 9e d0 00 00 00    	fstp   DWORD PTR [esi+0xd0]
  841c0d:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841c10:	dc 3d 80 a7 b1 00    	fdivr  QWORD PTR ds:0xb1a780
  841c16:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  841c19:	d9 45 c0             	fld    DWORD PTR [ebp-0x40]
  841c1c:	d8 a6 c0 00 00 00    	fsub   DWORD PTR [esi+0xc0]
  841c22:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  841c25:	d9 45 c4             	fld    DWORD PTR [ebp-0x3c]
  841c28:	d8 a6 c4 00 00 00    	fsub   DWORD PTR [esi+0xc4]
  841c2e:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  841c31:	d9 45 c8             	fld    DWORD PTR [ebp-0x38]
  841c34:	d8 a6 c8 00 00 00    	fsub   DWORD PTR [esi+0xc8]
  841c3a:	d9 5d a8             	fstp   DWORD PTR [ebp-0x58]
  841c3d:	d9 45 a0             	fld    DWORD PTR [ebp-0x60]
  841c40:	d9 45 a4             	fld    DWORD PTR [ebp-0x5c]
  841c43:	d9 45 a8             	fld    DWORD PTR [ebp-0x58]
  841c46:	d9 c1                	fld    st(1)
  841c48:	de ca                	fmulp  st(2),st
  841c4a:	d9 c2                	fld    st(2)
  841c4c:	de cb                	fmulp  st(3),st
  841c4e:	d9 c9                	fxch   st(1)
  841c50:	de c2                	faddp  st(2),st
  841c52:	dc c8                	fmul   st(0),st
  841c54:	de c1                	faddp  st(1),st
  841c56:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841c59:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841c5c:	dc 1d 88 ac aa 00    	fcomp  QWORD PTR ds:0xaaac88
  841c62:	df e0                	fnstsw ax
  841c64:	f6 c4 05             	test   ah,0x5
  841c67:	7a 47                	jp     0x841cb0
  841c69:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  841c6c:	d9 c0                	fld    st(0)
  841c6e:	d8 4d f4             	fmul   DWORD PTR [ebp-0xc]
  841c71:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841c74:	d9 86 d4 00 00 00    	fld    DWORD PTR [esi+0xd4]
  841c7a:	dd 05 88 16 ab 00    	fld    QWORD PTR ds:0xab1688
  841c80:	dc c9                	fmul   st(1),st
  841c82:	d9 c9                	fxch   st(1)
  841c84:	d8 45 f8             	fadd   DWORD PTR [ebp-0x8]
  841c87:	dd 05 08 9b aa 00    	fld    QWORD PTR ds:0xaa9b08
  841c8d:	dc c9                	fmul   st(1),st
  841c8f:	d9 c9                	fxch   st(1)
  841c91:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841c94:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841c97:	de cb                	fmulp  st(3),st
  841c99:	d9 ca                	fxch   st(2)
  841c9b:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841c9e:	d9 86 d8 00 00 00    	fld    DWORD PTR [esi+0xd8]
  841ca4:	de c9                	fmulp  st(1),st
  841ca6:	d8 45 f8             	fadd   DWORD PTR [ebp-0x8]
  841ca9:	de c9                	fmulp  st(1),st
  841cab:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841cae:	eb 08                	jmp    0x841cb8
  841cb0:	d9 ee                	fldz
  841cb2:	d9 55 ec             	fst    DWORD PTR [ebp-0x14]
  841cb5:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841cb8:	d9 45 c0             	fld    DWORD PTR [ebp-0x40]
  841cbb:	d9 9e c0 00 00 00    	fstp   DWORD PTR [esi+0xc0]
  841cc1:	d9 45 c4             	fld    DWORD PTR [ebp-0x3c]
  841cc4:	d9 9e c4 00 00 00    	fstp   DWORD PTR [esi+0xc4]
  841cca:	d9 45 c8             	fld    DWORD PTR [ebp-0x38]
  841ccd:	d9 9e c8 00 00 00    	fstp   DWORD PTR [esi+0xc8]
  841cd3:	d9 45 cc             	fld    DWORD PTR [ebp-0x34]
  841cd6:	d9 9e cc 00 00 00    	fstp   DWORD PTR [esi+0xcc]
  841cdc:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  841cdf:	d9 9e d4 00 00 00    	fstp   DWORD PTR [esi+0xd4]
  841ce5:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841ce8:	d9 9e d8 00 00 00    	fstp   DWORD PTR [esi+0xd8]
  841cee:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  841cf1:	dd 05 b8 44 ab 00    	fld    QWORD PTR ds:0xab44b8
  841cf7:	dc c9                	fmul   st(1),st
  841cf9:	d9 c9                	fxch   st(1)
  841cfb:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841cfe:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841d01:	dc c0                	fadd   st(0),st
  841d03:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841d06:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  841d09:	d8 d1                	fcom   st(1)
  841d0b:	df e0                	fnstsw ax
  841d0d:	d9 05 bc c7 aa 00    	fld    DWORD PTR ds:0xaac7bc
  841d13:	f6 c4 41             	test   ah,0x41
  841d16:	75 05                	jne    0x841d1d
  841d18:	d9 55 f8             	fst    DWORD PTR [ebp-0x8]
  841d1b:	eb 07                	jmp    0x841d24
  841d1d:	d9 c9                	fxch   st(1)
  841d1f:	d9 55 f8             	fst    DWORD PTR [ebp-0x8]
  841d22:	d9 c9                	fxch   st(1)
  841d24:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841d27:	dc 1d 00 95 b0 00    	fcomp  QWORD PTR ds:0xb09500
  841d2d:	df e0                	fnstsw ax
  841d2f:	f6 c4 05             	test   ah,0x5
  841d32:	7a 14                	jp     0x841d48
  841d34:	dd da                	fstp   st(2)
  841d36:	dd d8                	fstp   st(0)
  841d38:	dd d8                	fstp   st(0)
  841d3a:	d9 05 44 42 ac 00    	fld    DWORD PTR ds:0xac4244
  841d40:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841d43:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  841d46:	eb 17                	jmp    0x841d5f
  841d48:	d9 ca                	fxch   st(2)
  841d4a:	d8 d9                	fcomp  st(1)
  841d4c:	df e0                	fnstsw ax
  841d4e:	f6 c4 05             	test   ah,0x5
  841d51:	7a 0a                	jp     0x841d5d
  841d53:	dd d8                	fstp   st(0)
  841d55:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  841d58:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  841d5b:	eb 02                	jmp    0x841d5f
  841d5d:	dd d9                	fstp   st(1)
  841d5f:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841d62:	dd 05 88 16 ab 00    	fld    QWORD PTR ds:0xab1688
  841d68:	d8 d1                	fcom   st(1)
  841d6a:	df e0                	fnstsw ax
  841d6c:	d9 05 f8 b3 aa 00    	fld    DWORD PTR ds:0xaab3f8
  841d72:	f6 c4 05             	test   ah,0x5
  841d75:	7a 05                	jp     0x841d7c
  841d77:	d9 55 f8             	fst    DWORD PTR [ebp-0x8]
  841d7a:	eb 07                	jmp    0x841d83
  841d7c:	d9 ca                	fxch   st(2)
  841d7e:	d9 55 f8             	fst    DWORD PTR [ebp-0x8]
  841d81:	d9 ca                	fxch   st(2)
  841d83:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841d86:	dc 1d b8 49 b0 00    	fcomp  QWORD PTR ds:0xb049b8
  841d8c:	df e0                	fnstsw ax
  841d8e:	f6 c4 05             	test   ah,0x5
  841d91:	7a 14                	jp     0x841da7
  841d93:	dd da                	fstp   st(2)
  841d95:	dd d9                	fstp   st(1)
  841d97:	dd d8                	fstp   st(0)
  841d99:	d9 05 48 42 ac 00    	fld    DWORD PTR ds:0xac4248
  841d9f:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841da2:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841da5:	eb 17                	jmp    0x841dbe
  841da7:	d9 c9                	fxch   st(1)
  841da9:	d8 da                	fcomp  st(2)
  841dab:	df e0                	fnstsw ax
  841dad:	f6 c4 05             	test   ah,0x5
  841db0:	7a 0a                	jp     0x841dbc
  841db2:	dd d9                	fstp   st(1)
  841db4:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  841db7:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  841dba:	eb 02                	jmp    0x841dbe
  841dbc:	dd d8                	fstp   st(0)
  841dbe:	dc c8                	fmul   st(0),st
  841dc0:	d9 c1                	fld    st(1)
  841dc2:	de ca                	fmulp  st(2),st
  841dc4:	de c1                	faddp  st(1),st
  841dc6:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841dc9:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841dcc:	e8 5f ef 0b 00       	call   0x900d30
  841dd1:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841dd4:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841dd7:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  841dda:	dd 05 78 a7 b1 00    	fld    QWORD PTR ds:0xb1a778
  841de0:	e8 4b ef 0b 00       	call   0x900d30
  841de5:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841de8:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841deb:	d8 7d f0             	fdivr  DWORD PTR [ebp-0x10]
  841dee:	d9 e8                	fld1
  841df0:	d8 d1                	fcom   st(1)
  841df2:	df e0                	fnstsw ax
  841df4:	f6 c4 05             	test   ah,0x5
  841df7:	7a 04                	jp     0x841dfd
  841df9:	dd d9                	fstp   st(1)
  841dfb:	eb 02                	jmp    0x841dff
  841dfd:	dd d8                	fstp   st(0)
  841dff:	8b 07                	mov    eax,DWORD PTR [edi]
  841e01:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  841e04:	8b 40 1c             	mov    eax,DWORD PTR [eax+0x1c]
  841e07:	8d 95 70 fe ff ff    	lea    edx,[ebp-0x190]
  841e0d:	8b cf                	mov    ecx,edi
  841e0f:	ff d0                	call   eax
  841e11:	8b 07                	mov    eax,DWORD PTR [edi]
  841e13:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  841e16:	8d 95 10 fe ff ff    	lea    edx,[ebp-0x1f0]
  841e1c:	8b cf                	mov    ecx,edi
  841e1e:	ff d0                	call   eax
  841e20:	d9 46 48             	fld    DWORD PTR [esi+0x48]
  841e23:	d8 46 44             	fadd   DWORD PTR [esi+0x44]
  841e26:	8d 4d a0             	lea    ecx,[ebp-0x60]
  841e29:	51                   	push   ecx
  841e2a:	8d 8d 70 fe ff ff    	lea    ecx,[ebp-0x190]
  841e30:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  841e33:	d9 85 30 fe ff ff    	fld    DWORD PTR [ebp-0x1d0]
  841e39:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  841e3c:	d9 c0                	fld    st(0)
  841e3e:	de ca                	fmulp  st(2),st
  841e40:	d9 c9                	fxch   st(1)
  841e42:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  841e45:	d9 85 34 fe ff ff    	fld    DWORD PTR [ebp-0x1cc]
  841e4b:	d8 c9                	fmul   st,st(1)
  841e4d:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  841e50:	d9 85 38 fe ff ff    	fld    DWORD PTR [ebp-0x1c8]
  841e56:	d8 c9                	fmul   st,st(1)
  841e58:	d9 5d c8             	fstp   DWORD PTR [ebp-0x38]
  841e5b:	dc 0d 68 dd aa 00    	fmul   QWORD PTR ds:0xaadd68
  841e61:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  841e64:	d9 45 c0             	fld    DWORD PTR [ebp-0x40]
  841e67:	dd 05 20 9a aa 00    	fld    QWORD PTR ds:0xaa9a20
  841e6d:	dc c9                	fmul   st(1),st
  841e6f:	d9 c9                	fxch   st(1)
  841e71:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  841e74:	d9 45 c4             	fld    DWORD PTR [ebp-0x3c]
  841e77:	d8 c9                	fmul   st,st(1)
  841e79:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  841e7c:	d9 45 c8             	fld    DWORD PTR [ebp-0x38]
  841e7f:	d8 c9                	fmul   st,st(1)
  841e81:	d9 5d a8             	fstp   DWORD PTR [ebp-0x58]
  841e84:	d8 4d cc             	fmul   DWORD PTR [ebp-0x34]
  841e87:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  841e8a:	e8 01 f3 bb ff       	call   0x401190
  841e8f:	d9 85 70 fe ff ff    	fld    DWORD PTR [ebp-0x190]
  841e95:	d9 9e b0 00 00 00    	fstp   DWORD PTR [esi+0xb0]
  841e9b:	d9 85 74 fe ff ff    	fld    DWORD PTR [ebp-0x18c]
  841ea1:	d9 9e b4 00 00 00    	fstp   DWORD PTR [esi+0xb4]
  841ea7:	d9 85 78 fe ff ff    	fld    DWORD PTR [ebp-0x188]
  841ead:	d9 9e b8 00 00 00    	fstp   DWORD PTR [esi+0xb8]
  841eb3:	d9 85 7c fe ff ff    	fld    DWORD PTR [ebp-0x184]
  841eb9:	d9 9e bc 00 00 00    	fstp   DWORD PTR [esi+0xbc]
  841ebf:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  841ec5:	e8 46 c2 fe ff       	call   0x82e110
  841eca:	8b 4d d8             	mov    ecx,DWORD PTR [ebp-0x28]
  841ecd:	8b 11                	mov    edx,DWORD PTR [ecx]
  841ecf:	8b f8                	mov    edi,eax
  841ed1:	8b 82 0c 01 00 00    	mov    eax,DWORD PTR [edx+0x10c]
  841ed7:	89 7d e0             	mov    DWORD PTR [ebp-0x20],edi
  841eda:	ff d0                	call   eax
  841edc:	8b c8                	mov    ecx,eax
  841ede:	e8 4d e4 00 00       	call   0x850330
  841ee3:	8b 56 58             	mov    edx,DWORD PTR [esi+0x58]
  841ee6:	8b 0f                	mov    ecx,DWORD PTR [edi]
  841ee8:	6a 00                	push   0x0
  841eea:	6a 00                	push   0x0
  841eec:	52                   	push   edx
  841eed:	6a 00                	push   0x0
  841eef:	50                   	push   eax
  841ef0:	89 45 bc             	mov    DWORD PTR [ebp-0x44],eax
  841ef3:	8b 81 88 00 00 00    	mov    eax,DWORD PTR [ecx+0x88]
  841ef9:	57                   	push   edi
  841efa:	ff d0                	call   eax
  841efc:	85 c0                	test   eax,eax
  841efe:	7d 10                	jge    0x841f10
  841f00:	e8 1d 17 0e 00       	call   0x923622
  841f05:	32 c0                	xor    al,al
  841f07:	5f                   	pop    edi
  841f08:	5e                   	pop    esi
  841f09:	8b e5                	mov    esp,ebp
  841f0b:	5d                   	pop    ebp
  841f0c:	8b e3                	mov    esp,ebx
  841f0e:	5b                   	pop    ebx
  841f0f:	c3                   	ret
  841f10:	8b 56 14             	mov    edx,DWORD PTR [esi+0x14]
  841f13:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  841f19:	e8 f2 c5 fe ff       	call   0x82e510
  841f1e:	8b 56 1c             	mov    edx,DWORD PTR [esi+0x1c]
  841f21:	8b 0f                	mov    ecx,DWORD PTR [edi]
  841f23:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  841f29:	6a 14                	push   0x14
  841f2b:	6a 00                	push   0x0
  841f2d:	52                   	push   edx
  841f2e:	6a 00                	push   0x0
  841f30:	57                   	push   edi
  841f31:	ff d0                	call   eax
  841f33:	85 c0                	test   eax,eax
  841f35:	7c c9                	jl     0x841f00
  841f37:	8b 56 18             	mov    edx,DWORD PTR [esi+0x18]
  841f3a:	8b 0f                	mov    ecx,DWORD PTR [edi]
  841f3c:	8b 81 a0 01 00 00    	mov    eax,DWORD PTR [ecx+0x1a0]
  841f42:	52                   	push   edx
  841f43:	57                   	push   edi
  841f44:	ff d0                	call   eax
  841f46:	85 c0                	test   eax,eax
  841f48:	7c b6                	jl     0x841f00
  841f4a:	8b 4e 68             	mov    ecx,DWORD PTR [esi+0x68]
  841f4d:	85 c9                	test   ecx,ecx
  841f4f:	74 0c                	je     0x841f5d
  841f51:	e8 9a 6e ff ff       	call   0x838df0
  841f56:	85 c0                	test   eax,eax
  841f58:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  841f5b:	75 16                	jne    0x841f73
  841f5d:	8b 4e 64             	mov    ecx,DWORD PTR [esi+0x64]
  841f60:	8b 01                	mov    eax,DWORD PTR [ecx]
  841f62:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  841f65:	33 d2                	xor    edx,edx
  841f67:	ff d0                	call   eax
  841f69:	8b c8                	mov    ecx,eax
  841f6b:	e8 80 6e ff ff       	call   0x838df0
  841f70:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  841f73:	d9 46 2c             	fld    DWORD PTR [esi+0x2c]
  841f76:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  841f79:	d9 9d 80 fe ff ff    	fstp   DWORD PTR [ebp-0x180]
  841f7f:	8d 95 80 fe ff ff    	lea    edx,[ebp-0x180]
  841f85:	d9 46 30             	fld    DWORD PTR [esi+0x30]
  841f88:	52                   	push   edx
  841f89:	d9 46 2c             	fld    DWORD PTR [esi+0x2c]
  841f8c:	68 54 a6 b1 00       	push   0xb1a654
  841f91:	d8 e9                	fsubr  st,st(1)
  841f93:	6a 00                	push   0x0
  841f95:	50                   	push   eax
  841f96:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  841f99:	de f9                	fdivp  st(1),st
  841f9b:	d9 9d 84 fe ff ff    	fstp   DWORD PTR [ebp-0x17c]
  841fa1:	8b 38                	mov    edi,DWORD PTR [eax]
  841fa3:	8b cf                	mov    ecx,edi
  841fa5:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  841fa8:	ff d2                	call   edx
  841faa:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  841fb0:	50                   	push   eax
  841fb1:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  841fb4:	50                   	push   eax
  841fb5:	ff d1                	call   ecx
  841fb7:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  841fba:	8b 11                	mov    edx,DWORD PTR [ecx]
  841fbc:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  841fbf:	ff d0                	call   eax
  841fc1:	dc 3d 00 9b aa 00    	fdivr  QWORD PTR ds:0xaa9b00
  841fc7:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  841fca:	d9 46 48             	fld    DWORD PTR [esi+0x48]
  841fcd:	d8 46 44             	fadd   DWORD PTR [esi+0x44]
  841fd0:	dc 0d 20 9a aa 00    	fmul   QWORD PTR ds:0xaa9a20
  841fd6:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  841fd9:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  841fdc:	dc 0d b0 70 ab 00    	fmul   QWORD PTR ds:0xab70b0
  841fe2:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  841fe5:	d9 c0                	fld    st(0)
  841fe7:	de c2                	faddp  st(2),st
  841fe9:	d9 c9                	fxch   st(1)
  841feb:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  841fee:	dc 15 68 dd aa 00    	fcom   QWORD PTR ds:0xaadd68
  841ff4:	df e0                	fnstsw ax
  841ff6:	f6 c4 05             	test   ah,0x5
  841ff9:	7a 04                	jp     0x841fff
  841ffb:	dd d8                	fstp   st(0)
  841ffd:	d9 ee                	fldz
  841fff:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842002:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  842005:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  842008:	8d 95 80 fe ff ff    	lea    edx,[ebp-0x180]
  84200e:	d9 9d 80 fe ff ff    	fstp   DWORD PTR [ebp-0x180]
  842014:	52                   	push   edx
  842015:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  842018:	68 64 a7 b1 00       	push   0xb1a764
  84201d:	d9 9d 84 fe ff ff    	fstp   DWORD PTR [ebp-0x17c]
  842023:	8b 38                	mov    edi,DWORD PTR [eax]
  842025:	8b cf                	mov    ecx,edi
  842027:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  84202a:	6a 00                	push   0x0
  84202c:	50                   	push   eax
  84202d:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842030:	ff d2                	call   edx
  842032:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  842038:	50                   	push   eax
  842039:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  84203c:	50                   	push   eax
  84203d:	ff d1                	call   ecx
  84203f:	d9 45 e4             	fld    DWORD PTR [ebp-0x1c]
  842042:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842045:	8b 38                	mov    edi,DWORD PTR [eax]
  842047:	51                   	push   ecx
  842048:	d9 1c 24             	fstp   DWORD PTR [esp]
  84204b:	68 50 a7 b1 00       	push   0xb1a750
  842050:	6a 00                	push   0x0
  842052:	8b d7                	mov    edx,edi
  842054:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842057:	50                   	push   eax
  842058:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84205b:	ff d0                	call   eax
  84205d:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842060:	8b 57 78             	mov    edx,DWORD PTR [edi+0x78]
  842063:	50                   	push   eax
  842064:	51                   	push   ecx
  842065:	ff d2                	call   edx
  842067:	8b 46 60             	mov    eax,DWORD PTR [esi+0x60]
  84206a:	8b 4e 78             	mov    ecx,DWORD PTR [esi+0x78]
  84206d:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  842070:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842073:	8b 38                	mov    edi,DWORD PTR [eax]
  842075:	68 38 a7 b1 00       	push   0xb1a738
  84207a:	8b d7                	mov    edx,edi
  84207c:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84207f:	50                   	push   eax
  842080:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  842083:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  842086:	ff d0                	call   eax
  842088:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84208b:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  842091:	50                   	push   eax
  842092:	51                   	push   ecx
  842093:	ff d2                	call   edx
  842095:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842098:	8b 4d d8             	mov    ecx,DWORD PTR [ebp-0x28]
  84209b:	8b 38                	mov    edi,DWORD PTR [eax]
  84209d:	51                   	push   ecx
  84209e:	68 dc a5 b1 00       	push   0xb1a5dc
  8420a3:	6a 00                	push   0x0
  8420a5:	8b d7                	mov    edx,edi
  8420a7:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8420aa:	50                   	push   eax
  8420ab:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8420ae:	ff d0                	call   eax
  8420b0:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8420b3:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  8420b9:	50                   	push   eax
  8420ba:	51                   	push   ecx
  8420bb:	ff d2                	call   edx
  8420bd:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8420c0:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  8420c3:	8b 38                	mov    edi,DWORD PTR [eax]
  8420c5:	51                   	push   ecx
  8420c6:	68 d0 a5 b1 00       	push   0xb1a5d0
  8420cb:	6a 00                	push   0x0
  8420cd:	8b d7                	mov    edx,edi
  8420cf:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8420d2:	50                   	push   eax
  8420d3:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8420d6:	ff d0                	call   eax
  8420d8:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8420db:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  8420e1:	50                   	push   eax
  8420e2:	51                   	push   ecx
  8420e3:	ff d2                	call   edx
  8420e5:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  8420e8:	8b 7d e0             	mov    edi,DWORD PTR [ebp-0x20]
  8420eb:	8b 07                	mov    eax,DWORD PTR [edi]
  8420ed:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  8420f3:	51                   	push   ecx
  8420f4:	6a 00                	push   0x0
  8420f6:	57                   	push   edi
  8420f7:	ff d2                	call   edx
  8420f9:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8420fc:	8b 08                	mov    ecx,DWORD PTR [eax]
  8420fe:	6a 01                	push   0x1
  842100:	8d 55 d4             	lea    edx,[ebp-0x2c]
  842103:	52                   	push   edx
  842104:	50                   	push   eax
  842105:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  84210b:	ff d0                	call   eax
  84210d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842110:	8b 08                	mov    ecx,DWORD PTR [eax]
  842112:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  842118:	6a 00                	push   0x0
  84211a:	50                   	push   eax
  84211b:	ff d2                	call   edx
  84211d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842120:	8b 08                	mov    ecx,DWORD PTR [eax]
  842122:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  842128:	50                   	push   eax
  842129:	ff d2                	call   edx
  84212b:	8b 07                	mov    eax,DWORD PTR [edi]
  84212d:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  842133:	6a 02                	push   0x2
  842135:	6a 00                	push   0x0
  842137:	6a 04                	push   0x4
  842139:	6a 00                	push   0x0
  84213b:	6a 00                	push   0x0
  84213d:	6a 04                	push   0x4
  84213f:	57                   	push   edi
  842140:	ff d1                	call   ecx
  842142:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842145:	8b 10                	mov    edx,DWORD PTR [eax]
  842147:	50                   	push   eax
  842148:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  84214e:	ff d0                	call   eax
  842150:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842153:	8b 08                	mov    ecx,DWORD PTR [eax]
  842155:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  84215b:	50                   	push   eax
  84215c:	ff d2                	call   edx
  84215e:	8b 4e 50             	mov    ecx,DWORD PTR [esi+0x50]
  842161:	8b 07                	mov    eax,DWORD PTR [edi]
  842163:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  842169:	6a 14                	push   0x14
  84216b:	6a 00                	push   0x0
  84216d:	51                   	push   ecx
  84216e:	6a 00                	push   0x0
  842170:	57                   	push   edi
  842171:	ff d2                	call   edx
  842173:	85 c0                	test   eax,eax
  842175:	0f 8c 85 fd ff ff    	jl     0x841f00
  84217b:	8b 46 7c             	mov    eax,DWORD PTR [esi+0x7c]
  84217e:	8b 08                	mov    ecx,DWORD PTR [eax]
  842180:	8d 55 90             	lea    edx,[ebp-0x70]
  842183:	52                   	push   edx
  842184:	50                   	push   eax
  842185:	8b 41 30             	mov    eax,DWORD PTR [ecx+0x30]
  842188:	ff d0                	call   eax
  84218a:	db 45 a8             	fild   DWORD PTR [ebp-0x58]
  84218d:	8b 4d a8             	mov    ecx,DWORD PTR [ebp-0x58]
  842190:	85 c9                	test   ecx,ecx
  842192:	7d 06                	jge    0x84219a
  842194:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  84219a:	d9 e8                	fld1
  84219c:	8b 55 ac             	mov    edx,DWORD PTR [ebp-0x54]
  84219f:	85 d2                	test   edx,edx
  8421a1:	d9 c0                	fld    st(0)
  8421a3:	de f2                	fdivrp st(2),st
  8421a5:	d9 c9                	fxch   st(1)
  8421a7:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  8421aa:	db 45 ac             	fild   DWORD PTR [ebp-0x54]
  8421ad:	7d 06                	jge    0x8421b5
  8421af:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8421b5:	8b 86 88 00 00 00    	mov    eax,DWORD PTR [esi+0x88]
  8421bb:	de f9                	fdivp  st(1),st
  8421bd:	8b 4e 7c             	mov    ecx,DWORD PTR [esi+0x7c]
  8421c0:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  8421c3:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8421c6:	8b 38                	mov    edi,DWORD PTR [eax]
  8421c8:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8421cb:	8b cf                	mov    ecx,edi
  8421cd:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  8421d0:	68 54 a5 b1 00       	push   0xb1a554
  8421d5:	50                   	push   eax
  8421d6:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8421d9:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  8421dc:	ff d2                	call   edx
  8421de:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  8421e4:	50                   	push   eax
  8421e5:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8421e8:	50                   	push   eax
  8421e9:	ff d1                	call   ecx
  8421eb:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8421ee:	8b 55 d8             	mov    edx,DWORD PTR [ebp-0x28]
  8421f1:	8b 38                	mov    edi,DWORD PTR [eax]
  8421f3:	52                   	push   edx
  8421f4:	68 4c a5 b1 00       	push   0xb1a54c
  8421f9:	8b cf                	mov    ecx,edi
  8421fb:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8421fe:	6a 00                	push   0x0
  842200:	50                   	push   eax
  842201:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842204:	ff d2                	call   edx
  842206:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  84220c:	50                   	push   eax
  84220d:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  842210:	50                   	push   eax
  842211:	ff d1                	call   ecx
  842213:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842216:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  842219:	8b 38                	mov    edi,DWORD PTR [eax]
  84221b:	52                   	push   edx
  84221c:	68 d0 a5 b1 00       	push   0xb1a5d0
  842221:	8b cf                	mov    ecx,edi
  842223:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  842226:	6a 00                	push   0x0
  842228:	50                   	push   eax
  842229:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84222c:	ff d2                	call   edx
  84222e:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  842234:	50                   	push   eax
  842235:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  842238:	50                   	push   eax
  842239:	ff d1                	call   ecx
  84223b:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  84223e:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  842241:	8b 10                	mov    edx,DWORD PTR [eax]
  842243:	8b 92 94 00 00 00    	mov    edx,DWORD PTR [edx+0x94]
  842249:	51                   	push   ecx
  84224a:	6a 00                	push   0x0
  84224c:	50                   	push   eax
  84224d:	ff d2                	call   edx
  84224f:	d9 45 e4             	fld    DWORD PTR [ebp-0x1c]
  842252:	dd 05 68 dd aa 00    	fld    QWORD PTR ds:0xaadd68
  842258:	d8 c9                	fmul   st,st(1)
  84225a:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  84225d:	d9 c0                	fld    st(0)
  84225f:	de ca                	fmulp  st(2),st
  842261:	d9 c9                	fxch   st(1)
  842263:	d9 9d 10 ff ff ff    	fstp   DWORD PTR [ebp-0xf0]
  842269:	d9 ee                	fldz
  84226b:	d9 95 14 ff ff ff    	fst    DWORD PTR [ebp-0xec]
  842271:	d9 95 18 ff ff ff    	fst    DWORD PTR [ebp-0xe8]
  842277:	d9 95 1c ff ff ff    	fst    DWORD PTR [ebp-0xe4]
  84227d:	d9 c2                	fld    st(2)
  84227f:	d8 ca                	fmul   st,st(2)
  842281:	d9 9d 90 fe ff ff    	fstp   DWORD PTR [ebp-0x170]
  842287:	d9 95 94 fe ff ff    	fst    DWORD PTR [ebp-0x16c]
  84228d:	d9 95 98 fe ff ff    	fst    DWORD PTR [ebp-0x168]
  842293:	d9 95 9c fe ff ff    	fst    DWORD PTR [ebp-0x164]
  842299:	d9 c2                	fld    st(2)
  84229b:	dc c0                	fadd   st(0),st
  84229d:	d8 ca                	fmul   st,st(2)
  84229f:	d9 9d 20 ff ff ff    	fstp   DWORD PTR [ebp-0xe0]
  8422a5:	d9 95 24 ff ff ff    	fst    DWORD PTR [ebp-0xdc]
  8422ab:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8422ae:	d9 95 28 ff ff ff    	fst    DWORD PTR [ebp-0xd8]
  8422b4:	d9 95 2c ff ff ff    	fst    DWORD PTR [ebp-0xd4]
  8422ba:	d9 c2                	fld    st(2)
  8422bc:	dc 0d 88 16 ab 00    	fmul   QWORD PTR ds:0xab1688
  8422c2:	d8 ca                	fmul   st,st(2)
  8422c4:	d9 9d a0 fe ff ff    	fstp   DWORD PTR [ebp-0x160]
  8422ca:	d9 95 a4 fe ff ff    	fst    DWORD PTR [ebp-0x15c]
  8422d0:	d9 95 a8 fe ff ff    	fst    DWORD PTR [ebp-0x158]
  8422d6:	d9 95 ac fe ff ff    	fst    DWORD PTR [ebp-0x154]
  8422dc:	d9 c2                	fld    st(2)
  8422de:	dc 0d b8 44 ab 00    	fmul   QWORD PTR ds:0xab44b8
  8422e4:	d8 ca                	fmul   st,st(2)
  8422e6:	d9 9d 30 ff ff ff    	fstp   DWORD PTR [ebp-0xd0]
  8422ec:	d9 95 34 ff ff ff    	fst    DWORD PTR [ebp-0xcc]
  8422f2:	d9 95 38 ff ff ff    	fst    DWORD PTR [ebp-0xc8]
  8422f8:	d9 95 3c ff ff ff    	fst    DWORD PTR [ebp-0xc4]
  8422fe:	d9 c2                	fld    st(2)
  842300:	dc 0d 60 7a af 00    	fmul   QWORD PTR ds:0xaf7a60
  842306:	d8 ca                	fmul   st,st(2)
  842308:	d9 9d b0 fe ff ff    	fstp   DWORD PTR [ebp-0x150]
  84230e:	d9 95 b4 fe ff ff    	fst    DWORD PTR [ebp-0x14c]
  842314:	d9 95 b8 fe ff ff    	fst    DWORD PTR [ebp-0x148]
  84231a:	d9 95 bc fe ff ff    	fst    DWORD PTR [ebp-0x144]
  842320:	d9 c2                	fld    st(2)
  842322:	dc 0d a0 4a ab 00    	fmul   QWORD PTR ds:0xab4aa0
  842328:	d8 ca                	fmul   st,st(2)
  84232a:	d9 9d 40 ff ff ff    	fstp   DWORD PTR [ebp-0xc0]
  842330:	d9 95 44 ff ff ff    	fst    DWORD PTR [ebp-0xbc]
  842336:	d9 95 48 ff ff ff    	fst    DWORD PTR [ebp-0xb8]
  84233c:	d9 95 4c ff ff ff    	fst    DWORD PTR [ebp-0xb4]
  842342:	d9 c2                	fld    st(2)
  842344:	dc 0d b8 70 ab 00    	fmul   QWORD PTR ds:0xab70b8
  84234a:	d8 ca                	fmul   st,st(2)
  84234c:	d9 9d c0 fe ff ff    	fstp   DWORD PTR [ebp-0x140]
  842352:	d9 95 c4 fe ff ff    	fst    DWORD PTR [ebp-0x13c]
  842358:	d9 95 c8 fe ff ff    	fst    DWORD PTR [ebp-0x138]
  84235e:	d9 95 cc fe ff ff    	fst    DWORD PTR [ebp-0x134]
  842364:	d9 c2                	fld    st(2)
  842366:	dc 0d b8 46 ac 00    	fmul   QWORD PTR ds:0xac46b8
  84236c:	d8 ca                	fmul   st,st(2)
  84236e:	d9 9d 50 ff ff ff    	fstp   DWORD PTR [ebp-0xb0]
  842374:	d9 95 54 ff ff ff    	fst    DWORD PTR [ebp-0xac]
  84237a:	d9 95 58 ff ff ff    	fst    DWORD PTR [ebp-0xa8]
  842380:	d9 95 5c ff ff ff    	fst    DWORD PTR [ebp-0xa4]
  842386:	d9 c2                	fld    st(2)
  842388:	dc 0d 00 3d ac 00    	fmul   QWORD PTR ds:0xac3d00
  84238e:	d8 ca                	fmul   st,st(2)
  842390:	d9 9d d0 fe ff ff    	fstp   DWORD PTR [ebp-0x130]
  842396:	d9 95 d4 fe ff ff    	fst    DWORD PTR [ebp-0x12c]
  84239c:	d9 95 d8 fe ff ff    	fst    DWORD PTR [ebp-0x128]
  8423a2:	d9 95 dc fe ff ff    	fst    DWORD PTR [ebp-0x124]
  8423a8:	d9 c2                	fld    st(2)
  8423aa:	dc 0d f0 1b ab 00    	fmul   QWORD PTR ds:0xab1bf0
  8423b0:	d8 ca                	fmul   st,st(2)
  8423b2:	d9 9d 60 ff ff ff    	fstp   DWORD PTR [ebp-0xa0]
  8423b8:	d9 95 64 ff ff ff    	fst    DWORD PTR [ebp-0x9c]
  8423be:	d9 95 68 ff ff ff    	fst    DWORD PTR [ebp-0x98]
  8423c4:	d9 95 6c ff ff ff    	fst    DWORD PTR [ebp-0x94]
  8423ca:	d9 c2                	fld    st(2)
  8423cc:	dc 0d 18 77 b0 00    	fmul   QWORD PTR ds:0xb07718
  8423d2:	d8 ca                	fmul   st,st(2)
  8423d4:	d9 9d e0 fe ff ff    	fstp   DWORD PTR [ebp-0x120]
  8423da:	d9 95 e4 fe ff ff    	fst    DWORD PTR [ebp-0x11c]
  8423e0:	d9 95 e8 fe ff ff    	fst    DWORD PTR [ebp-0x118]
  8423e6:	d9 95 ec fe ff ff    	fst    DWORD PTR [ebp-0x114]
  8423ec:	d9 c2                	fld    st(2)
  8423ee:	dc 0d b8 ce af 00    	fmul   QWORD PTR ds:0xafceb8
  8423f4:	d8 ca                	fmul   st,st(2)
  8423f6:	d9 9d 70 ff ff ff    	fstp   DWORD PTR [ebp-0x90]
  8423fc:	d9 95 74 ff ff ff    	fst    DWORD PTR [ebp-0x8c]
  842402:	d9 95 78 ff ff ff    	fst    DWORD PTR [ebp-0x88]
  842408:	d9 95 7c ff ff ff    	fst    DWORD PTR [ebp-0x84]
  84240e:	d9 ca                	fxch   st(2)
  842410:	dc 0d 20 4a ac 00    	fmul   QWORD PTR ds:0xac4a20
  842416:	de c9                	fmulp  st(1),st
  842418:	d9 9d f0 fe ff ff    	fstp   DWORD PTR [ebp-0x110]
  84241e:	d9 95 f4 fe ff ff    	fst    DWORD PTR [ebp-0x10c]
  842424:	d9 95 f8 fe ff ff    	fst    DWORD PTR [ebp-0x108]
  84242a:	d9 9d fc fe ff ff    	fstp   DWORD PTR [ebp-0x104]
  842430:	8b 38                	mov    edi,DWORD PTR [eax]
  842432:	6a 03                	push   0x3
  842434:	8d 8d 20 ff ff ff    	lea    ecx,[ebp-0xe0]
  84243a:	51                   	push   ecx
  84243b:	68 40 a5 b1 00       	push   0xb1a540
  842440:	6a 00                	push   0x0
  842442:	8b d7                	mov    edx,edi
  842444:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842447:	50                   	push   eax
  842448:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84244b:	ff d0                	call   eax
  84244d:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842450:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  842456:	50                   	push   eax
  842457:	51                   	push   ecx
  842458:	ff d2                	call   edx
  84245a:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84245d:	8b 38                	mov    edi,DWORD PTR [eax]
  84245f:	6a 03                	push   0x3
  842461:	8d 8d a0 fe ff ff    	lea    ecx,[ebp-0x160]
  842467:	51                   	push   ecx
  842468:	68 30 a5 b1 00       	push   0xb1a530
  84246d:	6a 00                	push   0x0
  84246f:	8b d7                	mov    edx,edi
  842471:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842474:	50                   	push   eax
  842475:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842478:	ff d0                	call   eax
  84247a:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  84247d:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  842483:	50                   	push   eax
  842484:	51                   	push   ecx
  842485:	ff d2                	call   edx
  842487:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84248a:	8b 38                	mov    edi,DWORD PTR [eax]
  84248c:	6a 03                	push   0x3
  84248e:	8d 8d 50 ff ff ff    	lea    ecx,[ebp-0xb0]
  842494:	51                   	push   ecx
  842495:	68 24 a5 b1 00       	push   0xb1a524
  84249a:	6a 00                	push   0x0
  84249c:	8b d7                	mov    edx,edi
  84249e:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8424a1:	50                   	push   eax
  8424a2:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8424a5:	ff d0                	call   eax
  8424a7:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8424aa:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8424b0:	50                   	push   eax
  8424b1:	51                   	push   ecx
  8424b2:	ff d2                	call   edx
  8424b4:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8424b7:	8b 38                	mov    edi,DWORD PTR [eax]
  8424b9:	6a 03                	push   0x3
  8424bb:	8d 8d d0 fe ff ff    	lea    ecx,[ebp-0x130]
  8424c1:	51                   	push   ecx
  8424c2:	68 14 a5 b1 00       	push   0xb1a514
  8424c7:	6a 00                	push   0x0
  8424c9:	8b d7                	mov    edx,edi
  8424cb:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8424ce:	50                   	push   eax
  8424cf:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8424d2:	ff d0                	call   eax
  8424d4:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8424d7:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8424dd:	50                   	push   eax
  8424de:	51                   	push   ecx
  8424df:	ff d2                	call   edx
  8424e1:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8424e4:	8b 08                	mov    ecx,DWORD PTR [eax]
  8424e6:	6a 01                	push   0x1
  8424e8:	8d 55 d4             	lea    edx,[ebp-0x2c]
  8424eb:	52                   	push   edx
  8424ec:	50                   	push   eax
  8424ed:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  8424f3:	ff d0                	call   eax
  8424f5:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8424f8:	8b 08                	mov    ecx,DWORD PTR [eax]
  8424fa:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  842500:	6a 00                	push   0x0
  842502:	50                   	push   eax
  842503:	ff d2                	call   edx
  842505:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842508:	8b 08                	mov    ecx,DWORD PTR [eax]
  84250a:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  842510:	50                   	push   eax
  842511:	ff d2                	call   edx
  842513:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  842516:	8b 08                	mov    ecx,DWORD PTR [eax]
  842518:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  84251e:	6a 02                	push   0x2
  842520:	6a 00                	push   0x0
  842522:	6a 04                	push   0x4
  842524:	6a 00                	push   0x0
  842526:	6a 00                	push   0x0
  842528:	6a 04                	push   0x4
  84252a:	50                   	push   eax
  84252b:	ff d2                	call   edx
  84252d:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842530:	8b 08                	mov    ecx,DWORD PTR [eax]
  842532:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  842538:	50                   	push   eax
  842539:	ff d2                	call   edx
  84253b:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84253e:	8b 08                	mov    ecx,DWORD PTR [eax]
  842540:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  842546:	50                   	push   eax
  842547:	ff d2                	call   edx
  842549:	8b 86 8c 00 00 00    	mov    eax,DWORD PTR [esi+0x8c]
  84254f:	8b 4e 78             	mov    ecx,DWORD PTR [esi+0x78]
  842552:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  842555:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842558:	8b 38                	mov    edi,DWORD PTR [eax]
  84255a:	68 04 a5 b1 00       	push   0xb1a504
  84255f:	8b d7                	mov    edx,edi
  842561:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842564:	50                   	push   eax
  842565:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  842568:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  84256b:	ff d0                	call   eax
  84256d:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842570:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  842576:	50                   	push   eax
  842577:	51                   	push   ecx
  842578:	ff d2                	call   edx
  84257a:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84257d:	8b 4d d8             	mov    ecx,DWORD PTR [ebp-0x28]
  842580:	8b 38                	mov    edi,DWORD PTR [eax]
  842582:	51                   	push   ecx
  842583:	68 4c a5 b1 00       	push   0xb1a54c
  842588:	6a 00                	push   0x0
  84258a:	8b d7                	mov    edx,edi
  84258c:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84258f:	50                   	push   eax
  842590:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842593:	ff d0                	call   eax
  842595:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842598:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  84259e:	50                   	push   eax
  84259f:	51                   	push   ecx
  8425a0:	ff d2                	call   edx
  8425a2:	8b 55 f0             	mov    edx,DWORD PTR [ebp-0x10]
  8425a5:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  8425a8:	8b 08                	mov    ecx,DWORD PTR [eax]
  8425aa:	52                   	push   edx
  8425ab:	6a 00                	push   0x0
  8425ad:	50                   	push   eax
  8425ae:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  8425b4:	ff d0                	call   eax
  8425b6:	d9 ee                	fldz
  8425b8:	d9 95 10 ff ff ff    	fst    DWORD PTR [ebp-0xf0]
  8425be:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  8425c1:	dd 05 68 dd aa 00    	fld    QWORD PTR ds:0xaadd68
  8425c7:	d8 c9                	fmul   st,st(1)
  8425c9:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  8425cc:	d9 c0                	fld    st(0)
  8425ce:	de ca                	fmulp  st(2),st
  8425d0:	d9 c9                	fxch   st(1)
  8425d2:	d9 9d 14 ff ff ff    	fstp   DWORD PTR [ebp-0xec]
  8425d8:	d9 ca                	fxch   st(2)
  8425da:	d9 95 18 ff ff ff    	fst    DWORD PTR [ebp-0xe8]
  8425e0:	d9 95 1c ff ff ff    	fst    DWORD PTR [ebp-0xe4]
  8425e6:	d9 95 90 fe ff ff    	fst    DWORD PTR [ebp-0x170]
  8425ec:	d9 c1                	fld    st(1)
  8425ee:	d8 cb                	fmul   st,st(3)
  8425f0:	d9 9d 94 fe ff ff    	fstp   DWORD PTR [ebp-0x16c]
  8425f6:	d9 95 98 fe ff ff    	fst    DWORD PTR [ebp-0x168]
  8425fc:	d9 95 9c fe ff ff    	fst    DWORD PTR [ebp-0x164]
  842602:	d9 95 20 ff ff ff    	fst    DWORD PTR [ebp-0xe0]
  842608:	d9 c1                	fld    st(1)
  84260a:	dc c0                	fadd   st(0),st
  84260c:	d8 cb                	fmul   st,st(3)
  84260e:	d9 9d 24 ff ff ff    	fstp   DWORD PTR [ebp-0xdc]
  842614:	d9 95 28 ff ff ff    	fst    DWORD PTR [ebp-0xd8]
  84261a:	d9 95 2c ff ff ff    	fst    DWORD PTR [ebp-0xd4]
  842620:	d9 95 a0 fe ff ff    	fst    DWORD PTR [ebp-0x160]
  842626:	d9 c1                	fld    st(1)
  842628:	dc 0d 88 16 ab 00    	fmul   QWORD PTR ds:0xab1688
  84262e:	d8 cb                	fmul   st,st(3)
  842630:	d9 9d a4 fe ff ff    	fstp   DWORD PTR [ebp-0x15c]
  842636:	d9 95 a8 fe ff ff    	fst    DWORD PTR [ebp-0x158]
  84263c:	d9 95 ac fe ff ff    	fst    DWORD PTR [ebp-0x154]
  842642:	d9 95 30 ff ff ff    	fst    DWORD PTR [ebp-0xd0]
  842648:	d9 c1                	fld    st(1)
  84264a:	dc 0d b8 44 ab 00    	fmul   QWORD PTR ds:0xab44b8
  842650:	d8 cb                	fmul   st,st(3)
  842652:	d9 9d 34 ff ff ff    	fstp   DWORD PTR [ebp-0xcc]
  842658:	d9 95 38 ff ff ff    	fst    DWORD PTR [ebp-0xc8]
  84265e:	d9 95 3c ff ff ff    	fst    DWORD PTR [ebp-0xc4]
  842664:	d9 95 b0 fe ff ff    	fst    DWORD PTR [ebp-0x150]
  84266a:	d9 c1                	fld    st(1)
  84266c:	dc 0d 60 7a af 00    	fmul   QWORD PTR ds:0xaf7a60
  842672:	d8 cb                	fmul   st,st(3)
  842674:	d9 9d b4 fe ff ff    	fstp   DWORD PTR [ebp-0x14c]
  84267a:	d9 95 b8 fe ff ff    	fst    DWORD PTR [ebp-0x148]
  842680:	d9 95 bc fe ff ff    	fst    DWORD PTR [ebp-0x144]
  842686:	d9 95 40 ff ff ff    	fst    DWORD PTR [ebp-0xc0]
  84268c:	d9 c1                	fld    st(1)
  84268e:	dc 0d a0 4a ab 00    	fmul   QWORD PTR ds:0xab4aa0
  842694:	d8 cb                	fmul   st,st(3)
  842696:	d9 9d 44 ff ff ff    	fstp   DWORD PTR [ebp-0xbc]
  84269c:	d9 95 48 ff ff ff    	fst    DWORD PTR [ebp-0xb8]
  8426a2:	d9 95 4c ff ff ff    	fst    DWORD PTR [ebp-0xb4]
  8426a8:	d9 95 c0 fe ff ff    	fst    DWORD PTR [ebp-0x140]
  8426ae:	d9 c1                	fld    st(1)
  8426b0:	dc 0d b8 70 ab 00    	fmul   QWORD PTR ds:0xab70b8
  8426b6:	d8 cb                	fmul   st,st(3)
  8426b8:	d9 9d c4 fe ff ff    	fstp   DWORD PTR [ebp-0x13c]
  8426be:	d9 95 c8 fe ff ff    	fst    DWORD PTR [ebp-0x138]
  8426c4:	d9 95 cc fe ff ff    	fst    DWORD PTR [ebp-0x134]
  8426ca:	d9 95 50 ff ff ff    	fst    DWORD PTR [ebp-0xb0]
  8426d0:	d9 c1                	fld    st(1)
  8426d2:	dc 0d b8 46 ac 00    	fmul   QWORD PTR ds:0xac46b8
  8426d8:	d8 cb                	fmul   st,st(3)
  8426da:	d9 9d 54 ff ff ff    	fstp   DWORD PTR [ebp-0xac]
  8426e0:	d9 95 58 ff ff ff    	fst    DWORD PTR [ebp-0xa8]
  8426e6:	d9 95 5c ff ff ff    	fst    DWORD PTR [ebp-0xa4]
  8426ec:	d9 95 d0 fe ff ff    	fst    DWORD PTR [ebp-0x130]
  8426f2:	d9 c1                	fld    st(1)
  8426f4:	dc 0d 00 3d ac 00    	fmul   QWORD PTR ds:0xac3d00
  8426fa:	d8 cb                	fmul   st,st(3)
  8426fc:	d9 9d d4 fe ff ff    	fstp   DWORD PTR [ebp-0x12c]
  842702:	d9 95 d8 fe ff ff    	fst    DWORD PTR [ebp-0x128]
  842708:	d9 95 dc fe ff ff    	fst    DWORD PTR [ebp-0x124]
  84270e:	d9 95 60 ff ff ff    	fst    DWORD PTR [ebp-0xa0]
  842714:	d9 c1                	fld    st(1)
  842716:	dc 0d f0 1b ab 00    	fmul   QWORD PTR ds:0xab1bf0
  84271c:	d8 cb                	fmul   st,st(3)
  84271e:	d9 9d 64 ff ff ff    	fstp   DWORD PTR [ebp-0x9c]
  842724:	d9 95 68 ff ff ff    	fst    DWORD PTR [ebp-0x98]
  84272a:	d9 95 6c ff ff ff    	fst    DWORD PTR [ebp-0x94]
  842730:	d9 95 e0 fe ff ff    	fst    DWORD PTR [ebp-0x120]
  842736:	d9 c1                	fld    st(1)
  842738:	dc 0d 18 77 b0 00    	fmul   QWORD PTR ds:0xb07718
  84273e:	d8 cb                	fmul   st,st(3)
  842740:	d9 9d e4 fe ff ff    	fstp   DWORD PTR [ebp-0x11c]
  842746:	d9 95 e8 fe ff ff    	fst    DWORD PTR [ebp-0x118]
  84274c:	d9 95 ec fe ff ff    	fst    DWORD PTR [ebp-0x114]
  842752:	d9 95 70 ff ff ff    	fst    DWORD PTR [ebp-0x90]
  842758:	d9 c1                	fld    st(1)
  84275a:	dc 0d b8 ce af 00    	fmul   QWORD PTR ds:0xafceb8
  842760:	d8 cb                	fmul   st,st(3)
  842762:	d9 9d 74 ff ff ff    	fstp   DWORD PTR [ebp-0x8c]
  842768:	d9 95 78 ff ff ff    	fst    DWORD PTR [ebp-0x88]
  84276e:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842771:	d9 95 7c ff ff ff    	fst    DWORD PTR [ebp-0x84]
  842777:	d9 95 f0 fe ff ff    	fst    DWORD PTR [ebp-0x110]
  84277d:	6a 03                	push   0x3
  84277f:	d9 c9                	fxch   st(1)
  842781:	8d 8d 20 ff ff ff    	lea    ecx,[ebp-0xe0]
  842787:	dc 0d 20 4a ac 00    	fmul   QWORD PTR ds:0xac4a20
  84278d:	51                   	push   ecx
  84278e:	68 40 a5 b1 00       	push   0xb1a540
  842793:	6a 00                	push   0x0
  842795:	de ca                	fmulp  st(2),st
  842797:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84279a:	d9 c9                	fxch   st(1)
  84279c:	50                   	push   eax
  84279d:	d9 9d f4 fe ff ff    	fstp   DWORD PTR [ebp-0x10c]
  8427a3:	d9 95 f8 fe ff ff    	fst    DWORD PTR [ebp-0x108]
  8427a9:	d9 9d fc fe ff ff    	fstp   DWORD PTR [ebp-0x104]
  8427af:	8b 38                	mov    edi,DWORD PTR [eax]
  8427b1:	8b d7                	mov    edx,edi
  8427b3:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8427b6:	ff d0                	call   eax
  8427b8:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8427bb:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8427c1:	50                   	push   eax
  8427c2:	51                   	push   ecx
  8427c3:	ff d2                	call   edx
  8427c5:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8427c8:	8b 38                	mov    edi,DWORD PTR [eax]
  8427ca:	6a 03                	push   0x3
  8427cc:	8d 8d a0 fe ff ff    	lea    ecx,[ebp-0x160]
  8427d2:	51                   	push   ecx
  8427d3:	68 30 a5 b1 00       	push   0xb1a530
  8427d8:	6a 00                	push   0x0
  8427da:	8b d7                	mov    edx,edi
  8427dc:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8427df:	50                   	push   eax
  8427e0:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8427e3:	ff d0                	call   eax
  8427e5:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8427e8:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  8427ee:	50                   	push   eax
  8427ef:	51                   	push   ecx
  8427f0:	ff d2                	call   edx
  8427f2:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8427f5:	8b 38                	mov    edi,DWORD PTR [eax]
  8427f7:	6a 03                	push   0x3
  8427f9:	8d 8d 50 ff ff ff    	lea    ecx,[ebp-0xb0]
  8427ff:	51                   	push   ecx
  842800:	68 24 a5 b1 00       	push   0xb1a524
  842805:	6a 00                	push   0x0
  842807:	8b d7                	mov    edx,edi
  842809:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84280c:	50                   	push   eax
  84280d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842810:	ff d0                	call   eax
  842812:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842815:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  84281b:	50                   	push   eax
  84281c:	51                   	push   ecx
  84281d:	ff d2                	call   edx
  84281f:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842822:	8b 38                	mov    edi,DWORD PTR [eax]
  842824:	6a 03                	push   0x3
  842826:	8d 8d d0 fe ff ff    	lea    ecx,[ebp-0x130]
  84282c:	51                   	push   ecx
  84282d:	68 14 a5 b1 00       	push   0xb1a514
  842832:	6a 00                	push   0x0
  842834:	8b d7                	mov    edx,edi
  842836:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842839:	50                   	push   eax
  84283a:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  84283d:	ff d0                	call   eax
  84283f:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842842:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  842848:	50                   	push   eax
  842849:	51                   	push   ecx
  84284a:	ff d2                	call   edx
  84284c:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84284f:	8b 08                	mov    ecx,DWORD PTR [eax]
  842851:	6a 01                	push   0x1
  842853:	8d 55 d4             	lea    edx,[ebp-0x2c]
  842856:	52                   	push   edx
  842857:	50                   	push   eax
  842858:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  84285e:	ff d0                	call   eax
  842860:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842863:	8b 08                	mov    ecx,DWORD PTR [eax]
  842865:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  84286b:	6a 00                	push   0x0
  84286d:	50                   	push   eax
  84286e:	ff d2                	call   edx
  842870:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842873:	8b 08                	mov    ecx,DWORD PTR [eax]
  842875:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  84287b:	50                   	push   eax
  84287c:	ff d2                	call   edx
  84287e:	8b 7d e0             	mov    edi,DWORD PTR [ebp-0x20]
  842881:	8b 07                	mov    eax,DWORD PTR [edi]
  842883:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  842889:	6a 02                	push   0x2
  84288b:	6a 00                	push   0x0
  84288d:	6a 04                	push   0x4
  84288f:	6a 00                	push   0x0
  842891:	6a 00                	push   0x0
  842893:	6a 04                	push   0x4
  842895:	57                   	push   edi
  842896:	ff d1                	call   ecx
  842898:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84289b:	8b 10                	mov    edx,DWORD PTR [eax]
  84289d:	50                   	push   eax
  84289e:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8428a4:	ff d0                	call   eax
  8428a6:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8428a9:	8b 08                	mov    ecx,DWORD PTR [eax]
  8428ab:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8428b1:	50                   	push   eax
  8428b2:	ff d2                	call   edx
  8428b4:	8b 4e 1c             	mov    ecx,DWORD PTR [esi+0x1c]
  8428b7:	8b 07                	mov    eax,DWORD PTR [edi]
  8428b9:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  8428bf:	6a 14                	push   0x14
  8428c1:	6a 00                	push   0x0
  8428c3:	51                   	push   ecx
  8428c4:	6a 00                	push   0x0
  8428c6:	57                   	push   edi
  8428c7:	ff d2                	call   edx
  8428c9:	85 c0                	test   eax,eax
  8428cb:	0f 8c 2f f6 ff ff    	jl     0x841f00
  8428d1:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  8428d4:	8b 01                	mov    eax,DWORD PTR [ecx]
  8428d6:	8b 10                	mov    edx,DWORD PTR [eax]
  8428d8:	ff d2                	call   edx
  8428da:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  8428dd:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  8428e0:	8b 01                	mov    eax,DWORD PTR [ecx]
  8428e2:	8b 50 04             	mov    edx,DWORD PTR [eax+0x4]
  8428e5:	ff d2                	call   edx
  8428e7:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  8428ea:	d9 45 e4             	fld    DWORD PTR [ebp-0x1c]
  8428ed:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  8428f0:	d9 9d 50 fe ff ff    	fstp   DWORD PTR [ebp-0x1b0]
  8428f6:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  8428f9:	d9 9d 54 fe ff ff    	fstp   DWORD PTR [ebp-0x1ac]
  8428ff:	d9 ee                	fldz
  842901:	d9 95 58 fe ff ff    	fst    DWORD PTR [ebp-0x1a8]
  842907:	d9 9d 5c fe ff ff    	fstp   DWORD PTR [ebp-0x1a4]
  84290d:	8b 01                	mov    eax,DWORD PTR [ecx]
  84290f:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  842912:	ff d2                	call   edx
  842914:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  842917:	8b 4e 20             	mov    ecx,DWORD PTR [esi+0x20]
  84291a:	8b 01                	mov    eax,DWORD PTR [ecx]
  84291c:	8b 50 0c             	mov    edx,DWORD PTR [eax+0xc]
  84291f:	ff d2                	call   edx
  842921:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  842924:	d9 45 e4             	fld    DWORD PTR [ebp-0x1c]
  842927:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84292a:	d9 9d 60 fe ff ff    	fstp   DWORD PTR [ebp-0x1a0]
  842930:	8d 8d 50 fe ff ff    	lea    ecx,[ebp-0x1b0]
  842936:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  842939:	51                   	push   ecx
  84293a:	d9 9d 64 fe ff ff    	fstp   DWORD PTR [ebp-0x19c]
  842940:	68 08 a6 b1 00       	push   0xb1a608
  842945:	d9 ee                	fldz
  842947:	6a 00                	push   0x0
  842949:	d9 95 68 fe ff ff    	fst    DWORD PTR [ebp-0x198]
  84294f:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842952:	d9 9d 6c fe ff ff    	fstp   DWORD PTR [ebp-0x194]
  842958:	50                   	push   eax
  842959:	8b 38                	mov    edi,DWORD PTR [eax]
  84295b:	8b d7                	mov    edx,edi
  84295d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842960:	ff d0                	call   eax
  842962:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842965:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  84296b:	50                   	push   eax
  84296c:	51                   	push   ecx
  84296d:	ff d2                	call   edx
  84296f:	85 c0                	test   eax,eax
  842971:	0f 8c 89 f5 ff ff    	jl     0x841f00
  842977:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  84297a:	8b 38                	mov    edi,DWORD PTR [eax]
  84297c:	8d 8d 60 fe ff ff    	lea    ecx,[ebp-0x1a0]
  842982:	51                   	push   ecx
  842983:	68 f8 a5 b1 00       	push   0xb1a5f8
  842988:	6a 00                	push   0x0
  84298a:	8b d7                	mov    edx,edi
  84298c:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  84298f:	50                   	push   eax
  842990:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842993:	ff d0                	call   eax
  842995:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842998:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  84299e:	50                   	push   eax
  84299f:	51                   	push   ecx
  8429a0:	ff d2                	call   edx
  8429a2:	85 c0                	test   eax,eax
  8429a4:	0f 8c 56 f5 ff ff    	jl     0x841f00
  8429aa:	8b 86 88 00 00 00    	mov    eax,DWORD PTR [esi+0x88]
  8429b0:	8b 4e 60             	mov    ecx,DWORD PTR [esi+0x60]
  8429b3:	51                   	push   ecx
  8429b4:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
  8429b7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8429ba:	8b 38                	mov    edi,DWORD PTR [eax]
  8429bc:	68 dc a5 b1 00       	push   0xb1a5dc
  8429c1:	8b cf                	mov    ecx,edi
  8429c3:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8429c6:	6a 00                	push   0x0
  8429c8:	50                   	push   eax
  8429c9:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8429cc:	ff d2                	call   edx
  8429ce:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  8429d4:	50                   	push   eax
  8429d5:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8429d8:	50                   	push   eax
  8429d9:	ff d1                	call   ecx
  8429db:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  8429de:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
  8429e1:	8b 38                	mov    edi,DWORD PTR [eax]
  8429e3:	52                   	push   edx
  8429e4:	68 4c a5 b1 00       	push   0xb1a54c
  8429e9:	8b cf                	mov    ecx,edi
  8429eb:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8429ee:	6a 00                	push   0x0
  8429f0:	50                   	push   eax
  8429f1:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8429f4:	ff d2                	call   edx
  8429f6:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  8429fc:	50                   	push   eax
  8429fd:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  842a00:	50                   	push   eax
  842a01:	ff d1                	call   ecx
  842a03:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842a06:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  842a09:	8b 38                	mov    edi,DWORD PTR [eax]
  842a0b:	52                   	push   edx
  842a0c:	68 d0 a5 b1 00       	push   0xb1a5d0
  842a11:	8b cf                	mov    ecx,edi
  842a13:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  842a16:	6a 00                	push   0x0
  842a18:	50                   	push   eax
  842a19:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842a1c:	ff d2                	call   edx
  842a1e:	8b 8f d0 00 00 00    	mov    ecx,DWORD PTR [edi+0xd0]
  842a24:	50                   	push   eax
  842a25:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  842a28:	50                   	push   eax
  842a29:	ff d1                	call   ecx
  842a2b:	8b 4d bc             	mov    ecx,DWORD PTR [ebp-0x44]
  842a2e:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  842a31:	8b 10                	mov    edx,DWORD PTR [eax]
  842a33:	8b 92 94 00 00 00    	mov    edx,DWORD PTR [edx+0x94]
  842a39:	51                   	push   ecx
  842a3a:	6a 00                	push   0x0
  842a3c:	50                   	push   eax
  842a3d:	ff d2                	call   edx
  842a3f:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842a42:	8b 38                	mov    edi,DWORD PTR [eax]
  842a44:	8b cf                	mov    ecx,edi
  842a46:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  842a49:	68 2c a7 b1 00       	push   0xb1a72c
  842a4e:	50                   	push   eax
  842a4f:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  842a52:	ff d2                	call   edx
  842a54:	8b 8f e8 00 00 00    	mov    ecx,DWORD PTR [edi+0xe8]
  842a5a:	50                   	push   eax
  842a5b:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  842a5e:	50                   	push   eax
  842a5f:	ff d1                	call   ecx
  842a61:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842a64:	8b 10                	mov    edx,DWORD PTR [eax]
  842a66:	8b 92 fc 00 00 00    	mov    edx,DWORD PTR [edx+0xfc]
  842a6c:	6a 01                	push   0x1
  842a6e:	8d 4d d4             	lea    ecx,[ebp-0x2c]
  842a71:	51                   	push   ecx
  842a72:	50                   	push   eax
  842a73:	ff d2                	call   edx
  842a75:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842a78:	8b 08                	mov    ecx,DWORD PTR [eax]
  842a7a:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  842a80:	6a 00                	push   0x0
  842a82:	50                   	push   eax
  842a83:	ff d2                	call   edx
  842a85:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842a88:	8b 08                	mov    ecx,DWORD PTR [eax]
  842a8a:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  842a90:	50                   	push   eax
  842a91:	ff d2                	call   edx
  842a93:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  842a96:	8b 08                	mov    ecx,DWORD PTR [eax]
  842a98:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  842a9e:	6a 02                	push   0x2
  842aa0:	6a 00                	push   0x0
  842aa2:	6a 04                	push   0x4
  842aa4:	6a 00                	push   0x0
  842aa6:	6a 00                	push   0x0
  842aa8:	6a 04                	push   0x4
  842aaa:	50                   	push   eax
  842aab:	ff d2                	call   edx
  842aad:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842ab0:	8b 08                	mov    ecx,DWORD PTR [eax]
  842ab2:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  842ab8:	50                   	push   eax
  842ab9:	ff d2                	call   edx
  842abb:	8b 76 28             	mov    esi,DWORD PTR [esi+0x28]
  842abe:	8b 06                	mov    eax,DWORD PTR [esi]
  842ac0:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  842ac6:	56                   	push   esi
  842ac7:	ff d1                	call   ecx
  842ac9:	e8 54 0b 0e 00       	call   0x923622
  842ace:	5f                   	pop    edi
  842acf:	b0 01                	mov    al,0x1
  842ad1:	5e                   	pop    esi
  842ad2:	8b e5                	mov    esp,ebp
  842ad4:	5d                   	pop    ebp
  842ad5:	8b e3                	mov    esp,ebx
  842ad7:	5b                   	pop    ebx
  842ad8:	c3                   	ret
```

### `0x00842cf0..0x0084302d` — sites `0x00842ffd`

```asm
  842cf0:	53                   	push   ebx
  842cf1:	8b dc                	mov    ebx,esp
  842cf3:	83 ec 08             	sub    esp,0x8
  842cf6:	83 e4 f0             	and    esp,0xfffffff0
  842cf9:	83 c4 04             	add    esp,0x4
  842cfc:	55                   	push   ebp
  842cfd:	8b 6b 04             	mov    ebp,DWORD PTR [ebx+0x4]
  842d00:	89 6c 24 04          	mov    DWORD PTR [esp+0x4],ebp
  842d04:	8b ec                	mov    ebp,esp
  842d06:	81 ec 58 02 00 00    	sub    esp,0x258
  842d0c:	56                   	push   esi
  842d0d:	8b f1                	mov    esi,ecx
  842d0f:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  842d15:	57                   	push   edi
  842d16:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  842d19:	e8 f2 b3 fe ff       	call   0x82e110
  842d1e:	68 08 a8 b1 00       	push   0xb1a808
  842d23:	8b f8                	mov    edi,eax
  842d25:	68 00 00 ff ff       	push   0xffff0000
  842d2a:	89 7d f4             	mov    DWORD PTR [ebp-0xc],edi
  842d2d:	e8 f6 08 0e 00       	call   0x923628
  842d32:	8b 56 14             	mov    edx,DWORD PTR [esi+0x14]
  842d35:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  842d3b:	e8 d0 b7 fe ff       	call   0x82e510
  842d40:	8b 4e 18             	mov    ecx,DWORD PTR [esi+0x18]
  842d43:	8b 07                	mov    eax,DWORD PTR [edi]
  842d45:	8b 90 a0 01 00 00    	mov    edx,DWORD PTR [eax+0x1a0]
  842d4b:	51                   	push   ecx
  842d4c:	57                   	push   edi
  842d4d:	ff d2                	call   edx
  842d4f:	85 c0                	test   eax,eax
  842d51:	7d 12                	jge    0x842d65
  842d53:	e8 ca 08 0e 00       	call   0x923622
  842d58:	32 c0                	xor    al,al
  842d5a:	5f                   	pop    edi
  842d5b:	5e                   	pop    esi
  842d5c:	8b e5                	mov    esp,ebp
  842d5e:	5d                   	pop    ebp
  842d5f:	8b e3                	mov    esp,ebx
  842d61:	5b                   	pop    ebx
  842d62:	c2 08 00             	ret    0x8
  842d65:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
  842d68:	8b 08                	mov    ecx,DWORD PTR [eax]
  842d6a:	8d 55 b0             	lea    edx,[ebp-0x50]
  842d6d:	52                   	push   edx
  842d6e:	50                   	push   eax
  842d6f:	8b 41 30             	mov    eax,DWORD PTR [ecx+0x30]
  842d72:	ff d0                	call   eax
  842d74:	8b 4d cc             	mov    ecx,DWORD PTR [ebp-0x34]
  842d77:	8b 55 c8             	mov    edx,DWORD PTR [ebp-0x38]
  842d7a:	51                   	push   ecx
  842d7b:	8b ce                	mov    ecx,esi
  842d7d:	e8 de fe ff ff       	call   0x842c60
  842d82:	8b 17                	mov    edx,DWORD PTR [edi]
  842d84:	6a 14                	push   0x14
  842d86:	6a 00                	push   0x0
  842d88:	50                   	push   eax
  842d89:	8b 82 90 01 00 00    	mov    eax,DWORD PTR [edx+0x190]
  842d8f:	6a 00                	push   0x0
  842d91:	57                   	push   edi
  842d92:	ff d0                	call   eax
  842d94:	85 c0                	test   eax,eax
  842d96:	7c bb                	jl     0x842d53
  842d98:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
  842d9b:	8b 08                	mov    ecx,DWORD PTR [eax]
  842d9d:	8d 55 d0             	lea    edx,[ebp-0x30]
  842da0:	52                   	push   edx
  842da1:	50                   	push   eax
  842da2:	8b 41 30             	mov    eax,DWORD PTR [ecx+0x30]
  842da5:	ff d0                	call   eax
  842da7:	d9 e8                	fld1
  842da9:	51                   	push   ecx
  842daa:	d9 1c 24             	fstp   DWORD PTR [esp]
  842dad:	8d 8d b0 fd ff ff    	lea    ecx,[ebp-0x250]
  842db3:	51                   	push   ecx
  842db4:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  842db7:	8d 95 b0 fe ff ff    	lea    edx,[ebp-0x150]
  842dbd:	52                   	push   edx
  842dbe:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  842dc1:	e8 7a d3 ff ff       	call   0x840140
  842dc6:	d9 43 0c             	fld    DWORD PTR [ebx+0xc]
  842dc9:	8d 85 b8 fe ff ff    	lea    eax,[ebp-0x148]
  842dcf:	b9 02 00 00 00       	mov    ecx,0x2
  842dd4:	d9 c0                	fld    st(0)
  842dd6:	d8 48 f8             	fmul   DWORD PTR [eax-0x8]
  842dd9:	d9 58 f8             	fstp   DWORD PTR [eax-0x8]
  842ddc:	d9 40 fc             	fld    DWORD PTR [eax-0x4]
  842ddf:	d8 c9                	fmul   st,st(1)
  842de1:	d9 58 fc             	fstp   DWORD PTR [eax-0x4]
  842de4:	d9 00                	fld    DWORD PTR [eax]
  842de6:	d8 c9                	fmul   st,st(1)
  842de8:	d9 18                	fstp   DWORD PTR [eax]
  842dea:	d9 40 04             	fld    DWORD PTR [eax+0x4]
  842ded:	d8 c9                	fmul   st,st(1)
  842def:	d9 58 04             	fstp   DWORD PTR [eax+0x4]
  842df2:	d9 40 08             	fld    DWORD PTR [eax+0x8]
  842df5:	d8 c9                	fmul   st,st(1)
  842df7:	d9 58 08             	fstp   DWORD PTR [eax+0x8]
  842dfa:	d9 40 0c             	fld    DWORD PTR [eax+0xc]
  842dfd:	d8 c9                	fmul   st,st(1)
  842dff:	d9 58 0c             	fstp   DWORD PTR [eax+0xc]
  842e02:	d9 c0                	fld    st(0)
  842e04:	d8 48 10             	fmul   DWORD PTR [eax+0x10]
  842e07:	d9 58 10             	fstp   DWORD PTR [eax+0x10]
  842e0a:	d9 40 14             	fld    DWORD PTR [eax+0x14]
  842e0d:	d8 c9                	fmul   st,st(1)
  842e0f:	d9 58 14             	fstp   DWORD PTR [eax+0x14]
  842e12:	d9 40 18             	fld    DWORD PTR [eax+0x18]
  842e15:	d8 c9                	fmul   st,st(1)
  842e17:	d9 58 18             	fstp   DWORD PTR [eax+0x18]
  842e1a:	d9 40 1c             	fld    DWORD PTR [eax+0x1c]
  842e1d:	d8 c9                	fmul   st,st(1)
  842e1f:	d9 58 1c             	fstp   DWORD PTR [eax+0x1c]
  842e22:	d9 40 20             	fld    DWORD PTR [eax+0x20]
  842e25:	d8 c9                	fmul   st,st(1)
  842e27:	d9 58 20             	fstp   DWORD PTR [eax+0x20]
  842e2a:	d9 c0                	fld    st(0)
  842e2c:	d8 48 24             	fmul   DWORD PTR [eax+0x24]
  842e2f:	d9 58 24             	fstp   DWORD PTR [eax+0x24]
  842e32:	d9 40 28             	fld    DWORD PTR [eax+0x28]
  842e35:	d8 c9                	fmul   st,st(1)
  842e37:	d9 58 28             	fstp   DWORD PTR [eax+0x28]
  842e3a:	d9 40 2c             	fld    DWORD PTR [eax+0x2c]
  842e3d:	d8 c9                	fmul   st,st(1)
  842e3f:	d9 58 2c             	fstp   DWORD PTR [eax+0x2c]
  842e42:	d9 40 30             	fld    DWORD PTR [eax+0x30]
  842e45:	d8 c9                	fmul   st,st(1)
  842e47:	d9 58 30             	fstp   DWORD PTR [eax+0x30]
  842e4a:	d9 40 34             	fld    DWORD PTR [eax+0x34]
  842e4d:	d8 c9                	fmul   st,st(1)
  842e4f:	d9 58 34             	fstp   DWORD PTR [eax+0x34]
  842e52:	d9 c0                	fld    st(0)
  842e54:	d8 48 38             	fmul   DWORD PTR [eax+0x38]
  842e57:	d9 58 38             	fstp   DWORD PTR [eax+0x38]
  842e5a:	d9 c0                	fld    st(0)
  842e5c:	d8 48 3c             	fmul   DWORD PTR [eax+0x3c]
  842e5f:	d9 58 3c             	fstp   DWORD PTR [eax+0x3c]
  842e62:	d9 40 40             	fld    DWORD PTR [eax+0x40]
  842e65:	d8 c9                	fmul   st,st(1)
  842e67:	d9 58 40             	fstp   DWORD PTR [eax+0x40]
  842e6a:	d9 40 44             	fld    DWORD PTR [eax+0x44]
  842e6d:	d8 c9                	fmul   st,st(1)
  842e6f:	d9 58 44             	fstp   DWORD PTR [eax+0x44]
  842e72:	d9 40 48             	fld    DWORD PTR [eax+0x48]
  842e75:	d8 c9                	fmul   st,st(1)
  842e77:	d9 58 48             	fstp   DWORD PTR [eax+0x48]
  842e7a:	d9 40 4c             	fld    DWORD PTR [eax+0x4c]
  842e7d:	d8 c9                	fmul   st,st(1)
  842e7f:	d9 58 4c             	fstp   DWORD PTR [eax+0x4c]
  842e82:	d9 c0                	fld    st(0)
  842e84:	d8 48 50             	fmul   DWORD PTR [eax+0x50]
  842e87:	d9 58 50             	fstp   DWORD PTR [eax+0x50]
  842e8a:	d9 40 54             	fld    DWORD PTR [eax+0x54]
  842e8d:	d8 c9                	fmul   st,st(1)
  842e8f:	d9 58 54             	fstp   DWORD PTR [eax+0x54]
  842e92:	d9 40 58             	fld    DWORD PTR [eax+0x58]
  842e95:	d8 c9                	fmul   st,st(1)
  842e97:	d9 58 58             	fstp   DWORD PTR [eax+0x58]
  842e9a:	d9 40 5c             	fld    DWORD PTR [eax+0x5c]
  842e9d:	d8 c9                	fmul   st,st(1)
  842e9f:	d9 58 5c             	fstp   DWORD PTR [eax+0x5c]
  842ea2:	d9 40 60             	fld    DWORD PTR [eax+0x60]
  842ea5:	d8 c9                	fmul   st,st(1)
  842ea7:	d9 58 60             	fstp   DWORD PTR [eax+0x60]
  842eaa:	d9 c0                	fld    st(0)
  842eac:	05 80 00 00 00       	add    eax,0x80
  842eb1:	83 e9 01             	sub    ecx,0x1
  842eb4:	d8 48 e4             	fmul   DWORD PTR [eax-0x1c]
  842eb7:	d9 58 e4             	fstp   DWORD PTR [eax-0x1c]
  842eba:	d9 40 e8             	fld    DWORD PTR [eax-0x18]
  842ebd:	d8 c9                	fmul   st,st(1)
  842ebf:	d9 58 e8             	fstp   DWORD PTR [eax-0x18]
  842ec2:	d9 40 ec             	fld    DWORD PTR [eax-0x14]
  842ec5:	d8 c9                	fmul   st,st(1)
  842ec7:	d9 58 ec             	fstp   DWORD PTR [eax-0x14]
  842eca:	d9 40 f0             	fld    DWORD PTR [eax-0x10]
  842ecd:	d8 c9                	fmul   st,st(1)
  842ecf:	d9 58 f0             	fstp   DWORD PTR [eax-0x10]
  842ed2:	d9 40 f4             	fld    DWORD PTR [eax-0xc]
  842ed5:	d8 c9                	fmul   st,st(1)
  842ed7:	d9 58 f4             	fstp   DWORD PTR [eax-0xc]
  842eda:	0f 85 f4 fe ff ff    	jne    0x842dd4
  842ee0:	8b 07                	mov    eax,DWORD PTR [edi]
  842ee2:	dd d8                	fstp   st(0)
  842ee4:	51                   	push   ecx
  842ee5:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  842eeb:	68 c2 00 00 00       	push   0xc2
  842ef0:	57                   	push   edi
  842ef1:	ff d1                	call   ecx
  842ef3:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842ef6:	8b 10                	mov    edx,DWORD PTR [eax]
  842ef8:	8b c8                	mov    ecx,eax
  842efa:	8b 39                	mov    edi,DWORD PTR [ecx]
  842efc:	68 f8 a7 b1 00       	push   0xb1a7f8
  842f01:	50                   	push   eax
  842f02:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  842f05:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  842f08:	ff d0                	call   eax
  842f0a:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  842f0d:	8b 97 e8 00 00 00    	mov    edx,DWORD PTR [edi+0xe8]
  842f13:	50                   	push   eax
  842f14:	51                   	push   ecx
  842f15:	ff d2                	call   edx
  842f17:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842f1a:	8b 10                	mov    edx,DWORD PTR [eax]
  842f1c:	8b c8                	mov    ecx,eax
  842f1e:	8b 39                	mov    edi,DWORD PTR [ecx]
  842f20:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  842f23:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842f26:	51                   	push   ecx
  842f27:	68 98 a5 b1 00       	push   0xb1a598
  842f2c:	6a 00                	push   0x0
  842f2e:	50                   	push   eax
  842f2f:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842f32:	ff d0                	call   eax
  842f34:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  842f37:	8b 97 d0 00 00 00    	mov    edx,DWORD PTR [edi+0xd0]
  842f3d:	50                   	push   eax
  842f3e:	51                   	push   ecx
  842f3f:	ff d2                	call   edx
  842f41:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
  842f44:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  842f47:	8b 08                	mov    ecx,DWORD PTR [eax]
  842f49:	52                   	push   edx
  842f4a:	6a 00                	push   0x0
  842f4c:	50                   	push   eax
  842f4d:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  842f53:	ff d0                	call   eax
  842f55:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842f58:	8b 10                	mov    edx,DWORD PTR [eax]
  842f5a:	8b c8                	mov    ecx,eax
  842f5c:	8b 39                	mov    edi,DWORD PTR [ecx]
  842f5e:	6a 0d                	push   0xd
  842f60:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  842f63:	8d 8d b0 fd ff ff    	lea    ecx,[ebp-0x250]
  842f69:	51                   	push   ecx
  842f6a:	68 88 a5 b1 00       	push   0xb1a588
  842f6f:	6a 00                	push   0x0
  842f71:	50                   	push   eax
  842f72:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842f75:	ff d0                	call   eax
  842f77:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842f7a:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  842f80:	50                   	push   eax
  842f81:	51                   	push   ecx
  842f82:	ff d2                	call   edx
  842f84:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842f87:	8b 10                	mov    edx,DWORD PTR [eax]
  842f89:	8b c8                	mov    ecx,eax
  842f8b:	8b 39                	mov    edi,DWORD PTR [ecx]
  842f8d:	6a 0d                	push   0xd
  842f8f:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  842f92:	8d 8d b0 fe ff ff    	lea    ecx,[ebp-0x150]
  842f98:	51                   	push   ecx
  842f99:	68 78 a5 b1 00       	push   0xb1a578
  842f9e:	6a 00                	push   0x0
  842fa0:	50                   	push   eax
  842fa1:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  842fa4:	ff d0                	call   eax
  842fa6:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  842fa9:	8b 97 90 00 00 00    	mov    edx,DWORD PTR [edi+0x90]
  842faf:	50                   	push   eax
  842fb0:	51                   	push   ecx
  842fb1:	ff d2                	call   edx
  842fb3:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842fb6:	8b 08                	mov    ecx,DWORD PTR [eax]
  842fb8:	6a 01                	push   0x1
  842fba:	8d 55 f0             	lea    edx,[ebp-0x10]
  842fbd:	52                   	push   edx
  842fbe:	50                   	push   eax
  842fbf:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  842fc5:	ff d0                	call   eax
  842fc7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842fca:	8b 08                	mov    ecx,DWORD PTR [eax]
  842fcc:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  842fd2:	6a 00                	push   0x0
  842fd4:	50                   	push   eax
  842fd5:	ff d2                	call   edx
  842fd7:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  842fda:	8b 08                	mov    ecx,DWORD PTR [eax]
  842fdc:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  842fe2:	50                   	push   eax
  842fe3:	ff d2                	call   edx
  842fe5:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  842fe8:	8b 08                	mov    ecx,DWORD PTR [eax]
  842fea:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  842ff0:	6a 02                	push   0x2
  842ff2:	6a 00                	push   0x0
  842ff4:	6a 04                	push   0x4
  842ff6:	6a 00                	push   0x0
  842ff8:	6a 00                	push   0x0
  842ffa:	6a 04                	push   0x4
  842ffc:	50                   	push   eax
  842ffd:	ff d2                	call   edx
  842fff:	8b 46 28             	mov    eax,DWORD PTR [esi+0x28]
  843002:	8b 08                	mov    ecx,DWORD PTR [eax]
  843004:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  84300a:	50                   	push   eax
  84300b:	ff d2                	call   edx
  84300d:	8b 76 28             	mov    esi,DWORD PTR [esi+0x28]
  843010:	8b 06                	mov    eax,DWORD PTR [esi]
  843012:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  843018:	56                   	push   esi
  843019:	ff d1                	call   ecx
  84301b:	e8 02 06 0e 00       	call   0x923622
  843020:	5f                   	pop    edi
  843021:	b0 01                	mov    al,0x1
  843023:	5e                   	pop    esi
  843024:	8b e5                	mov    esp,ebp
  843026:	5d                   	pop    ebp
  843027:	8b e3                	mov    esp,ebx
  843029:	5b                   	pop    ebx
  84302a:	c2 08 00             	ret    0x8
```

### `0x0084fd60..0x0084fd9f` — sites `0x0084fd98`

```asm
  84fd60:	55                   	push   ebp
  84fd61:	8b ec                	mov    ebp,esp
  84fd63:	56                   	push   esi
  84fd64:	8b 75 08             	mov    esi,DWORD PTR [ebp+0x8]
  84fd67:	80 7e 04 00          	cmp    BYTE PTR [esi+0x4],0x0
  84fd6b:	74 07                	je     0x84fd74
  84fd6d:	8b ce                	mov    ecx,esi
  84fd6f:	e8 8c f2 ff ff       	call   0x84f000
  84fd74:	8b 55 20             	mov    edx,DWORD PTR [ebp+0x20]
  84fd77:	8b 46 08             	mov    eax,DWORD PTR [esi+0x8]
  84fd7a:	8b 08                	mov    ecx,DWORD PTR [eax]
  84fd7c:	52                   	push   edx
  84fd7d:	8b 55 1c             	mov    edx,DWORD PTR [ebp+0x1c]
  84fd80:	52                   	push   edx
  84fd81:	8b 55 18             	mov    edx,DWORD PTR [ebp+0x18]
  84fd84:	52                   	push   edx
  84fd85:	8b 55 14             	mov    edx,DWORD PTR [ebp+0x14]
  84fd88:	52                   	push   edx
  84fd89:	8b 55 10             	mov    edx,DWORD PTR [ebp+0x10]
  84fd8c:	52                   	push   edx
  84fd8d:	8b 55 0c             	mov    edx,DWORD PTR [ebp+0xc]
  84fd90:	52                   	push   edx
  84fd91:	50                   	push   eax
  84fd92:	8b 81 48 01 00 00    	mov    eax,DWORD PTR [ecx+0x148]
  84fd98:	ff d0                	call   eax
  84fd9a:	5e                   	pop    esi
  84fd9b:	5d                   	pop    ebp
  84fd9c:	c2 1c 00             	ret    0x1c
```

### `0x00850dc0..0x0085172e` — sites `0x0085129a`, `0x008514d9`, `0x008516f4`

```asm
  850dc0:	55                   	push   ebp
  850dc1:	8b ec                	mov    ebp,esp
  850dc3:	51                   	push   ecx
  850dc4:	8b 41 0c             	mov    eax,DWORD PTR [ecx+0xc]
  850dc7:	83 f8 04             	cmp    eax,0x4
  850dca:	53                   	push   ebx
  850dcb:	56                   	push   esi
  850dcc:	57                   	push   edi
  850dcd:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  850dd0:	75 07                	jne    0x850dd9
  850dd2:	bb c8 be b1 00       	mov    ebx,0xb1bec8
  850dd7:	eb 17                	jmp    0x850df0
  850dd9:	83 f8 03             	cmp    eax,0x3
  850ddc:	74 0a                	je     0x850de8
  850dde:	83 f8 02             	cmp    eax,0x2
  850de1:	bb 98 be b1 00       	mov    ebx,0xb1be98
  850de6:	75 08                	jne    0x850df0
  850de8:	bb b0 be b1 00       	mov    ebx,0xb1beb0
  850ded:	8d 49 00             	lea    ecx,[ecx+0x0]
  850df0:	8b 3d 58 60 c2 00    	mov    edi,DWORD PTR ds:0xc26058
  850df6:	8b 37                	mov    esi,DWORD PTR [edi]
  850df8:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850dfa:	6a 00                	push   0x0
  850dfc:	83 c6 48             	add    esi,0x48
  850dff:	e8 ac e1 fd ff       	call   0x82efb0
  850e04:	8b d0                	mov    edx,eax
  850e06:	8b 06                	mov    eax,DWORD PTR [esi]
  850e08:	8b cf                	mov    ecx,edi
  850e0a:	ff d0                	call   eax
  850e0c:	84 c0                	test   al,al
  850e0e:	75 0f                	jne    0x850e1f
  850e10:	83 c3 04             	add    ebx,0x4
  850e13:	83 3b 00             	cmp    DWORD PTR [ebx],0x0
  850e16:	75 d8                	jne    0x850df0
  850e18:	5f                   	pop    edi
  850e19:	5e                   	pop    esi
  850e1a:	5b                   	pop    ebx
  850e1b:	8b e5                	mov    esp,ebp
  850e1d:	5d                   	pop    ebp
  850e1e:	c3                   	ret
  850e1f:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850e21:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  850e24:	5f                   	pop    edi
  850e25:	5e                   	pop    esi
  850e26:	89 4a 38             	mov    DWORD PTR [edx+0x38],ecx
  850e29:	b0 01                	mov    al,0x1
  850e2b:	5b                   	pop    ebx
  850e2c:	8b e5                	mov    esp,ebp
  850e2e:	5d                   	pop    ebp
  850e2f:	c3                   	ret
  850e30:	55                   	push   ebp
  850e31:	8b ec                	mov    ebp,esp
  850e33:	51                   	push   ecx
  850e34:	8b 41 0c             	mov    eax,DWORD PTR [ecx+0xc]
  850e37:	83 f8 04             	cmp    eax,0x4
  850e3a:	53                   	push   ebx
  850e3b:	56                   	push   esi
  850e3c:	57                   	push   edi
  850e3d:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  850e40:	75 07                	jne    0x850e49
  850e42:	bb c8 be b1 00       	mov    ebx,0xb1bec8
  850e47:	eb 17                	jmp    0x850e60
  850e49:	83 f8 03             	cmp    eax,0x3
  850e4c:	74 0a                	je     0x850e58
  850e4e:	83 f8 02             	cmp    eax,0x2
  850e51:	bb 98 be b1 00       	mov    ebx,0xb1be98
  850e56:	75 08                	jne    0x850e60
  850e58:	bb b0 be b1 00       	mov    ebx,0xb1beb0
  850e5d:	8d 49 00             	lea    ecx,[ecx+0x0]
  850e60:	8b 3d 58 60 c2 00    	mov    edi,DWORD PTR ds:0xc26058
  850e66:	8b 37                	mov    esi,DWORD PTR [edi]
  850e68:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850e6a:	6a 00                	push   0x0
  850e6c:	83 c6 48             	add    esi,0x48
  850e6f:	e8 3c e1 fd ff       	call   0x82efb0
  850e74:	8b d0                	mov    edx,eax
  850e76:	8b 06                	mov    eax,DWORD PTR [esi]
  850e78:	8b cf                	mov    ecx,edi
  850e7a:	ff d0                	call   eax
  850e7c:	84 c0                	test   al,al
  850e7e:	75 0f                	jne    0x850e8f
  850e80:	83 c3 04             	add    ebx,0x4
  850e83:	83 3b 00             	cmp    DWORD PTR [ebx],0x0
  850e86:	75 d8                	jne    0x850e60
  850e88:	5f                   	pop    edi
  850e89:	5e                   	pop    esi
  850e8a:	5b                   	pop    ebx
  850e8b:	8b e5                	mov    esp,ebp
  850e8d:	5d                   	pop    ebp
  850e8e:	c3                   	ret
  850e8f:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850e91:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  850e94:	5f                   	pop    edi
  850e95:	5e                   	pop    esi
  850e96:	89 4a 3c             	mov    DWORD PTR [edx+0x3c],ecx
  850e99:	b0 01                	mov    al,0x1
  850e9b:	5b                   	pop    ebx
  850e9c:	8b e5                	mov    esp,ebp
  850e9e:	5d                   	pop    ebp
  850e9f:	c3                   	ret
  850ea0:	55                   	push   ebp
  850ea1:	8b ec                	mov    ebp,esp
  850ea3:	51                   	push   ecx
  850ea4:	8b 41 0c             	mov    eax,DWORD PTR [ecx+0xc]
  850ea7:	83 f8 04             	cmp    eax,0x4
  850eaa:	53                   	push   ebx
  850eab:	56                   	push   esi
  850eac:	57                   	push   edi
  850ead:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  850eb0:	75 07                	jne    0x850eb9
  850eb2:	bb c8 be b1 00       	mov    ebx,0xb1bec8
  850eb7:	eb 17                	jmp    0x850ed0
  850eb9:	83 f8 03             	cmp    eax,0x3
  850ebc:	74 0a                	je     0x850ec8
  850ebe:	83 f8 02             	cmp    eax,0x2
  850ec1:	bb 98 be b1 00       	mov    ebx,0xb1be98
  850ec6:	75 08                	jne    0x850ed0
  850ec8:	bb b0 be b1 00       	mov    ebx,0xb1beb0
  850ecd:	8d 49 00             	lea    ecx,[ecx+0x0]
  850ed0:	8b 3d 58 60 c2 00    	mov    edi,DWORD PTR ds:0xc26058
  850ed6:	8b 37                	mov    esi,DWORD PTR [edi]
  850ed8:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850eda:	6a 00                	push   0x0
  850edc:	83 c6 48             	add    esi,0x48
  850edf:	e8 cc e0 fd ff       	call   0x82efb0
  850ee4:	8b d0                	mov    edx,eax
  850ee6:	8b 06                	mov    eax,DWORD PTR [esi]
  850ee8:	8b cf                	mov    ecx,edi
  850eea:	ff d0                	call   eax
  850eec:	84 c0                	test   al,al
  850eee:	75 0f                	jne    0x850eff
  850ef0:	83 c3 04             	add    ebx,0x4
  850ef3:	83 3b 00             	cmp    DWORD PTR [ebx],0x0
  850ef6:	75 d8                	jne    0x850ed0
  850ef8:	5f                   	pop    edi
  850ef9:	5e                   	pop    esi
  850efa:	5b                   	pop    ebx
  850efb:	8b e5                	mov    esp,ebp
  850efd:	5d                   	pop    ebp
  850efe:	c3                   	ret
  850eff:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  850f01:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  850f04:	5f                   	pop    edi
  850f05:	5e                   	pop    esi
  850f06:	89 4a 40             	mov    DWORD PTR [edx+0x40],ecx
  850f09:	b0 01                	mov    al,0x1
  850f0b:	5b                   	pop    ebx
  850f0c:	8b e5                	mov    esp,ebp
  850f0e:	5d                   	pop    ebp
  850f0f:	c3                   	ret
  850f10:	55                   	push   ebp
  850f11:	8b ec                	mov    ebp,esp
  850f13:	81 ec 24 01 00 00    	sub    esp,0x124
  850f19:	53                   	push   ebx
  850f1a:	56                   	push   esi
  850f1b:	57                   	push   edi
  850f1c:	68 e0 bf b1 00       	push   0xb1bfe0
  850f21:	68 00 00 ff ff       	push   0xffff0000
  850f26:	8b f1                	mov    esi,ecx
  850f28:	e8 fb 26 0d 00       	call   0x923628
  850f2d:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  850f33:	e8 d8 d1 fd ff       	call   0x82e110
  850f38:	8b 5e 5c             	mov    ebx,DWORD PTR [esi+0x5c]
  850f3b:	8d 55 ec             	lea    edx,[ebp-0x14]
  850f3e:	8b f8                	mov    edi,eax
  850f40:	8b 46 74             	mov    eax,DWORD PTR [esi+0x74]
  850f43:	8b 08                	mov    ecx,DWORD PTR [eax]
  850f45:	52                   	push   edx
  850f46:	6a 00                	push   0x0
  850f48:	50                   	push   eax
  850f49:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  850f4c:	89 5d f0             	mov    DWORD PTR [ebp-0x10],ebx
  850f4f:	ff d0                	call   eax
  850f51:	85 c0                	test   eax,eax
  850f53:	7d 0e                	jge    0x850f63
  850f55:	e8 c8 26 0d 00       	call   0x923622
  850f5a:	5f                   	pop    edi
  850f5b:	5e                   	pop    esi
  850f5c:	32 c0                	xor    al,al
  850f5e:	5b                   	pop    ebx
  850f5f:	8b e5                	mov    esp,ebp
  850f61:	5d                   	pop    ebp
  850f62:	c3                   	ret
  850f63:	8b 8e a0 00 00 00    	mov    ecx,DWORD PTR [esi+0xa0]
  850f69:	8b c1                	mov    eax,ecx
  850f6b:	8b 08                	mov    ecx,DWORD PTR [eax]
  850f6d:	53                   	push   ebx
  850f6e:	68 c4 bf b1 00       	push   0xb1bfc4
  850f73:	6a 00                	push   0x0
  850f75:	8b d1                	mov    edx,ecx
  850f77:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  850f7a:	50                   	push   eax
  850f7b:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  850f7e:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  850f81:	ff d0                	call   eax
  850f83:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  850f86:	50                   	push   eax
  850f87:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  850f8a:	8b 90 d0 00 00 00    	mov    edx,DWORD PTR [eax+0xd0]
  850f90:	51                   	push   ecx
  850f91:	ff d2                	call   edx
  850f93:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  850f96:	8b 07                	mov    eax,DWORD PTR [edi]
  850f98:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  850f9e:	51                   	push   ecx
  850f9f:	6a 00                	push   0x0
  850fa1:	57                   	push   edi
  850fa2:	ff d2                	call   edx
  850fa4:	8b 8e c8 00 00 00    	mov    ecx,DWORD PTR [esi+0xc8]
  850faa:	8b 07                	mov    eax,DWORD PTR [edi]
  850fac:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  850fb2:	6a 14                	push   0x14
  850fb4:	6a 00                	push   0x0
  850fb6:	51                   	push   ecx
  850fb7:	6a 00                	push   0x0
  850fb9:	57                   	push   edi
  850fba:	ff d2                	call   edx
  850fbc:	85 c0                	test   eax,eax
  850fbe:	7c 95                	jl     0x850f55
  850fc0:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  850fc3:	8b 01                	mov    eax,DWORD PTR [ecx]
  850fc5:	8b 10                	mov    edx,DWORD PTR [eax]
  850fc7:	ff d2                	call   edx
  850fc9:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  850fcc:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  850fcf:	8b 01                	mov    eax,DWORD PTR [ecx]
  850fd1:	8b 50 04             	mov    edx,DWORD PTR [eax+0x4]
  850fd4:	ff d2                	call   edx
  850fd6:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  850fd9:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  850fdc:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  850fdf:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  850fe2:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  850fe5:	d9 5d b0             	fstp   DWORD PTR [ebp-0x50]
  850fe8:	d9 ee                	fldz
  850fea:	d9 55 b4             	fst    DWORD PTR [ebp-0x4c]
  850fed:	d9 5d b8             	fstp   DWORD PTR [ebp-0x48]
  850ff0:	8b 01                	mov    eax,DWORD PTR [ecx]
  850ff2:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  850ff5:	ff d2                	call   edx
  850ff7:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  850ffa:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  850ffd:	8b 01                	mov    eax,DWORD PTR [ecx]
  850fff:	8b 50 0c             	mov    edx,DWORD PTR [eax+0xc]
  851002:	ff d2                	call   edx
  851004:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  851007:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85100a:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851010:	d9 5d bc             	fstp   DWORD PTR [ebp-0x44]
  851013:	8d 4d ac             	lea    ecx,[ebp-0x54]
  851016:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  851019:	51                   	push   ecx
  85101a:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  85101d:	68 08 a6 b1 00       	push   0xb1a608
  851022:	d9 ee                	fldz
  851024:	6a 00                	push   0x0
  851026:	d9 55 c4             	fst    DWORD PTR [ebp-0x3c]
  851029:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85102c:	d9 5d c8             	fstp   DWORD PTR [ebp-0x38]
  85102f:	50                   	push   eax
  851030:	8b 18                	mov    ebx,DWORD PTR [eax]
  851032:	8b d3                	mov    edx,ebx
  851034:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851037:	ff d0                	call   eax
  851039:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85103c:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  851042:	50                   	push   eax
  851043:	51                   	push   ecx
  851044:	ff d2                	call   edx
  851046:	85 c0                	test   eax,eax
  851048:	0f 8c 07 ff ff ff    	jl     0x850f55
  85104e:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851054:	8b 18                	mov    ebx,DWORD PTR [eax]
  851056:	8d 4d bc             	lea    ecx,[ebp-0x44]
  851059:	51                   	push   ecx
  85105a:	68 f8 a5 b1 00       	push   0xb1a5f8
  85105f:	6a 00                	push   0x0
  851061:	8b d3                	mov    edx,ebx
  851063:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851066:	50                   	push   eax
  851067:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85106a:	ff d0                	call   eax
  85106c:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85106f:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  851075:	50                   	push   eax
  851076:	51                   	push   ecx
  851077:	ff d2                	call   edx
  851079:	85 c0                	test   eax,eax
  85107b:	0f 8c d4 fe ff ff    	jl     0x850f55
  851081:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  851084:	8b 08                	mov    ecx,DWORD PTR [eax]
  851086:	8d 95 fc fe ff ff    	lea    edx,[ebp-0x104]
  85108c:	52                   	push   edx
  85108d:	6a 00                	push   0x0
  85108f:	50                   	push   eax
  851090:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  851093:	ff d0                	call   eax
  851095:	db 85 14 ff ff ff    	fild   DWORD PTR [ebp-0xec]
  85109b:	8b 8d 14 ff ff ff    	mov    ecx,DWORD PTR [ebp-0xec]
  8510a1:	85 c9                	test   ecx,ecx
  8510a3:	7d 06                	jge    0x8510ab
  8510a5:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8510ab:	d9 e8                	fld1
  8510ad:	8b 95 18 ff ff ff    	mov    edx,DWORD PTR [ebp-0xe8]
  8510b3:	85 d2                	test   edx,edx
  8510b5:	d9 c0                	fld    st(0)
  8510b7:	de f2                	fdivrp st(2),st
  8510b9:	d9 c9                	fxch   st(1)
  8510bb:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  8510be:	db 85 18 ff ff ff    	fild   DWORD PTR [ebp-0xe8]
  8510c4:	7d 06                	jge    0x8510cc
  8510c6:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8510cc:	de f9                	fdivp  st(1),st
  8510ce:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  8510d1:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  8510d4:	d9 c0                	fld    st(0)
  8510d6:	dd 05 18 9a aa 00    	fld    QWORD PTR ds:0xaa9a18
  8510dc:	dc c9                	fmul   st(1),st
  8510de:	d9 c9                	fxch   st(1)
  8510e0:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  8510e3:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  8510e6:	d9 55 d8             	fst    DWORD PTR [ebp-0x28]
  8510e9:	8b 45 d8             	mov    eax,DWORD PTR [ebp-0x28]
  8510ec:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  8510ef:	89 85 1c ff ff ff    	mov    DWORD PTR [ebp-0xe4],eax
  8510f5:	d9 c0                	fld    st(0)
  8510f7:	dd 05 20 9a aa 00    	fld    QWORD PTR ds:0xaa9a20
  8510fd:	dc c9                	fmul   st(1),st
  8510ff:	d9 c9                	fxch   st(1)
  851101:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851104:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851107:	d9 55 dc             	fst    DWORD PTR [ebp-0x24]
  85110a:	8b 4d dc             	mov    ecx,DWORD PTR [ebp-0x24]
  85110d:	d9 ee                	fldz
  85110f:	89 8d 20 ff ff ff    	mov    DWORD PTR [ebp-0xe0],ecx
  851115:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  851118:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  85111b:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  85111e:	8b 45 e4             	mov    eax,DWORD PTR [ebp-0x1c]
  851121:	d9 ce                	fxch   st(6)
  851123:	de ca                	fmulp  st(2),st
  851125:	89 95 24 ff ff ff    	mov    DWORD PTR [ebp-0xdc],edx
  85112b:	d9 c9                	fxch   st(1)
  85112d:	89 85 28 ff ff ff    	mov    DWORD PTR [ebp-0xd8],eax
  851133:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851136:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851139:	d9 55 d8             	fst    DWORD PTR [ebp-0x28]
  85113c:	8b 4d d8             	mov    ecx,DWORD PTR [ebp-0x28]
  85113f:	d9 c9                	fxch   st(1)
  851141:	89 8d 2c ff ff ff    	mov    DWORD PTR [ebp-0xd4],ecx
  851147:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  85114a:	8b 55 dc             	mov    edx,DWORD PTR [ebp-0x24]
  85114d:	d9 cc                	fxch   st(4)
  85114f:	89 95 30 ff ff ff    	mov    DWORD PTR [ebp-0xd0],edx
  851155:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  851158:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  85115b:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  85115e:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
  851161:	d9 ca                	fxch   st(2)
  851163:	89 85 34 ff ff ff    	mov    DWORD PTR [ebp-0xcc],eax
  851169:	d9 5d d8             	fstp   DWORD PTR [ebp-0x28]
  85116c:	8b 55 d8             	mov    edx,DWORD PTR [ebp-0x28]
  85116f:	89 8d 38 ff ff ff    	mov    DWORD PTR [ebp-0xc8],ecx
  851175:	de ca                	fmulp  st(2),st
  851177:	89 95 3c ff ff ff    	mov    DWORD PTR [ebp-0xc4],edx
  85117d:	d9 c9                	fxch   st(1)
  85117f:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851182:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851185:	d9 55 dc             	fst    DWORD PTR [ebp-0x24]
  851188:	8b 45 dc             	mov    eax,DWORD PTR [ebp-0x24]
  85118b:	d9 c9                	fxch   st(1)
  85118d:	89 85 40 ff ff ff    	mov    DWORD PTR [ebp-0xc0],eax
  851193:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  851196:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  851199:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  85119c:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
  85119f:	d9 ca                	fxch   st(2)
  8511a1:	89 8d 44 ff ff ff    	mov    DWORD PTR [ebp-0xbc],ecx
  8511a7:	d9 5d d8             	fstp   DWORD PTR [ebp-0x28]
  8511aa:	8b 45 d8             	mov    eax,DWORD PTR [ebp-0x28]
  8511ad:	89 85 4c ff ff ff    	mov    DWORD PTR [ebp-0xb4],eax
  8511b3:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  8511b6:	8b 4d dc             	mov    ecx,DWORD PTR [ebp-0x24]
  8511b9:	89 95 48 ff ff ff    	mov    DWORD PTR [ebp-0xb8],edx
  8511bf:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  8511c2:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  8511c5:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  8511c8:	8b 45 e4             	mov    eax,DWORD PTR [ebp-0x1c]
  8511cb:	89 8d 50 ff ff ff    	mov    DWORD PTR [ebp-0xb0],ecx
  8511d1:	8b 8e a0 00 00 00    	mov    ecx,DWORD PTR [esi+0xa0]
  8511d7:	89 85 58 ff ff ff    	mov    DWORD PTR [ebp-0xa8],eax
  8511dd:	89 95 54 ff ff ff    	mov    DWORD PTR [ebp-0xac],edx
  8511e3:	8b c1                	mov    eax,ecx
  8511e5:	8b 18                	mov    ebx,DWORD PTR [eax]
  8511e7:	6a 04                	push   0x4
  8511e9:	8d 95 1c ff ff ff    	lea    edx,[ebp-0xe4]
  8511ef:	52                   	push   edx
  8511f0:	68 a8 bf b1 00       	push   0xb1bfa8
  8511f5:	8b cb                	mov    ecx,ebx
  8511f7:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8511fa:	6a 00                	push   0x0
  8511fc:	50                   	push   eax
  8511fd:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851200:	ff d2                	call   edx
  851202:	8b 8b 90 00 00 00    	mov    ecx,DWORD PTR [ebx+0x90]
  851208:	50                   	push   eax
  851209:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85120c:	50                   	push   eax
  85120d:	ff d1                	call   ecx
  85120f:	85 c0                	test   eax,eax
  851211:	0f 8c 3e fd ff ff    	jl     0x850f55
  851217:	80 7e 0a 00          	cmp    BYTE PTR [esi+0xa],0x0
  85121b:	b9 8c bf b1 00       	mov    ecx,0xb1bf8c
  851220:	75 05                	jne    0x851227
  851222:	b9 78 bf b1 00       	mov    ecx,0xb1bf78
  851227:	8b 96 a0 00 00 00    	mov    edx,DWORD PTR [esi+0xa0]
  85122d:	8b c2                	mov    eax,edx
  85122f:	8b 18                	mov    ebx,DWORD PTR [eax]
  851231:	51                   	push   ecx
  851232:	8b d3                	mov    edx,ebx
  851234:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851237:	50                   	push   eax
  851238:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  85123b:	ff d0                	call   eax
  85123d:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851240:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  851246:	50                   	push   eax
  851247:	51                   	push   ecx
  851248:	ff d2                	call   edx
  85124a:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851250:	8b 08                	mov    ecx,DWORD PTR [eax]
  851252:	6a 01                	push   0x1
  851254:	8d 55 d4             	lea    edx,[ebp-0x2c]
  851257:	52                   	push   edx
  851258:	50                   	push   eax
  851259:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85125f:	ff d0                	call   eax
  851261:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851267:	8b 08                	mov    ecx,DWORD PTR [eax]
  851269:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85126f:	6a 00                	push   0x0
  851271:	50                   	push   eax
  851272:	ff d2                	call   edx
  851274:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85127a:	8b 08                	mov    ecx,DWORD PTR [eax]
  85127c:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  851282:	50                   	push   eax
  851283:	ff d2                	call   edx
  851285:	8b 07                	mov    eax,DWORD PTR [edi]
  851287:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  85128d:	6a 02                	push   0x2
  85128f:	6a 00                	push   0x0
  851291:	6a 04                	push   0x4
  851293:	6a 00                	push   0x0
  851295:	6a 00                	push   0x0
  851297:	6a 04                	push   0x4
  851299:	57                   	push   edi
  85129a:	ff d1                	call   ecx
  85129c:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8512a2:	8b 10                	mov    edx,DWORD PTR [eax]
  8512a4:	50                   	push   eax
  8512a5:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8512ab:	ff d0                	call   eax
  8512ad:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8512b3:	8b 08                	mov    ecx,DWORD PTR [eax]
  8512b5:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8512bb:	50                   	push   eax
  8512bc:	ff d2                	call   edx
  8512be:	8d 4d ec             	lea    ecx,[ebp-0x14]
  8512c1:	e8 ea f0 ff ff       	call   0x8503b0
  8512c6:	80 7e 0a 00          	cmp    BYTE PTR [esi+0xa],0x0
  8512ca:	b9 5c bf b1 00       	mov    ecx,0xb1bf5c
  8512cf:	75 05                	jne    0x8512d6
  8512d1:	b9 44 bf b1 00       	mov    ecx,0xb1bf44
  8512d6:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8512dc:	8b 18                	mov    ebx,DWORD PTR [eax]
  8512de:	51                   	push   ecx
  8512df:	8b d3                	mov    edx,ebx
  8512e1:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8512e4:	50                   	push   eax
  8512e5:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  8512e8:	ff d0                	call   eax
  8512ea:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8512ed:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  8512f3:	50                   	push   eax
  8512f4:	51                   	push   ecx
  8512f5:	ff d2                	call   edx
  8512f7:	85 c0                	test   eax,eax
  8512f9:	0f 8c 56 fc ff ff    	jl     0x850f55
  8512ff:	8d 46 70             	lea    eax,[esi+0x70]
  851302:	c7 45 f8 05 00 00 00 	mov    DWORD PTR [ebp-0x8],0x5
  851309:	89 45 e8             	mov    DWORD PTR [ebp-0x18],eax
  85130c:	8d 64 24 00          	lea    esp,[esp+0x0]
  851310:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  851313:	8b 49 04             	mov    ecx,DWORD PTR [ecx+0x4]
  851316:	8b 96 a0 00 00 00    	mov    edx,DWORD PTR [esi+0xa0]
  85131c:	8b c2                	mov    eax,edx
  85131e:	8b 18                	mov    ebx,DWORD PTR [eax]
  851320:	51                   	push   ecx
  851321:	68 c4 bf b1 00       	push   0xb1bfc4
  851326:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  851329:	8b cb                	mov    ecx,ebx
  85132b:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85132e:	6a 00                	push   0x0
  851330:	50                   	push   eax
  851331:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851334:	ff d2                	call   edx
  851336:	8b 8b d0 00 00 00    	mov    ecx,DWORD PTR [ebx+0xd0]
  85133c:	50                   	push   eax
  85133d:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  851340:	50                   	push   eax
  851341:	ff d1                	call   ecx
  851343:	8b 5d e8             	mov    ebx,DWORD PTR [ebp-0x18]
  851346:	8b 03                	mov    eax,DWORD PTR [ebx]
  851348:	8b 10                	mov    edx,DWORD PTR [eax]
  85134a:	8b 52 48             	mov    edx,DWORD PTR [edx+0x48]
  85134d:	8d 4d ec             	lea    ecx,[ebp-0x14]
  851350:	51                   	push   ecx
  851351:	6a 00                	push   0x0
  851353:	50                   	push   eax
  851354:	ff d2                	call   edx
  851356:	85 c0                	test   eax,eax
  851358:	0f 8c f7 fb ff ff    	jl     0x850f55
  85135e:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  851361:	8b 07                	mov    eax,DWORD PTR [edi]
  851363:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  851369:	51                   	push   ecx
  85136a:	6a 00                	push   0x0
  85136c:	57                   	push   edi
  85136d:	ff d2                	call   edx
  85136f:	8b 4b 54             	mov    ecx,DWORD PTR [ebx+0x54]
  851372:	8b 07                	mov    eax,DWORD PTR [edi]
  851374:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  85137a:	6a 14                	push   0x14
  85137c:	6a 00                	push   0x0
  85137e:	51                   	push   ecx
  85137f:	6a 00                	push   0x0
  851381:	57                   	push   edi
  851382:	ff d2                	call   edx
  851384:	85 c0                	test   eax,eax
  851386:	0f 8c c9 fb ff ff    	jl     0x850f55
  85138c:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  85138f:	8b 08                	mov    ecx,DWORD PTR [eax]
  851391:	8d 95 dc fe ff ff    	lea    edx,[ebp-0x124]
  851397:	52                   	push   edx
  851398:	6a 00                	push   0x0
  85139a:	50                   	push   eax
  85139b:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  85139e:	ff d0                	call   eax
  8513a0:	db 85 f4 fe ff ff    	fild   DWORD PTR [ebp-0x10c]
  8513a6:	8b 8d f4 fe ff ff    	mov    ecx,DWORD PTR [ebp-0x10c]
  8513ac:	85 c9                	test   ecx,ecx
  8513ae:	7d 06                	jge    0x8513b6
  8513b0:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8513b6:	d9 e8                	fld1
  8513b8:	8b 95 f8 fe ff ff    	mov    edx,DWORD PTR [ebp-0x108]
  8513be:	85 d2                	test   edx,edx
  8513c0:	d9 c0                	fld    st(0)
  8513c2:	de f2                	fdivrp st(2),st
  8513c4:	d9 c9                	fxch   st(1)
  8513c6:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  8513c9:	db 85 f8 fe ff ff    	fild   DWORD PTR [ebp-0x108]
  8513cf:	7d 06                	jge    0x8513d7
  8513d1:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8513d7:	de f9                	fdivp  st(1),st
  8513d9:	83 c9 ff             	or     ecx,0xffffffff
  8513dc:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  8513df:	8d 85 20 ff ff ff    	lea    eax,[ebp-0xe0]
  8513e5:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  8513e8:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  8513eb:	dd 05 f8 68 ab 00    	fld    QWORD PTR ds:0xab68f8
  8513f1:	d8 c9                	fmul   st,st(1)
  8513f3:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  8513f6:	dd 05 68 dd aa 00    	fld    QWORD PTR ds:0xaadd68
  8513fc:	d8 c9                	fmul   st,st(1)
  8513fe:	d9 5d d0             	fstp   DWORD PTR [ebp-0x30]
  851401:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  851404:	d9 45 cc             	fld    DWORD PTR [ebp-0x34]
  851407:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85140a:	d9 45 d0             	fld    DWORD PTR [ebp-0x30]
  85140d:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  851410:	eb 06                	jmp    0x851418
  851412:	d9 c9                	fxch   st(1)
  851414:	d9 ca                	fxch   st(2)
  851416:	d9 c9                	fxch   st(1)
  851418:	db 45 f0             	fild   DWORD PTR [ebp-0x10]
  85141b:	83 c1 01             	add    ecx,0x1
  85141e:	83 c0 30             	add    eax,0x30
  851421:	83 f9 02             	cmp    ecx,0x2
  851424:	d8 cc                	fmul   st,st(4)
  851426:	89 4d f0             	mov    DWORD PTR [ebp-0x10],ecx
  851429:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  85142c:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  85142f:	d9 50 cc             	fst    DWORD PTR [eax-0x34]
  851432:	d9 50 dc             	fst    DWORD PTR [eax-0x24]
  851435:	d9 58 ec             	fstp   DWORD PTR [eax-0x14]
  851438:	d9 ca                	fxch   st(2)
  85143a:	d9 50 d0             	fst    DWORD PTR [eax-0x30]
  85143d:	d9 c9                	fxch   st(1)
  85143f:	d9 50 e0             	fst    DWORD PTR [eax-0x20]
  851442:	d9 ca                	fxch   st(2)
  851444:	d9 50 f0             	fst    DWORD PTR [eax-0x10]
  851447:	7c c9                	jl     0x851412
  851449:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85144f:	dd db                	fstp   st(3)
  851451:	8b 18                	mov    ebx,DWORD PTR [eax]
  851453:	dd d8                	fstp   st(0)
  851455:	6a 09                	push   0x9
  851457:	dd d8                	fstp   st(0)
  851459:	8d 8d 1c ff ff ff    	lea    ecx,[ebp-0xe4]
  85145f:	dd d8                	fstp   st(0)
  851461:	51                   	push   ecx
  851462:	68 28 bf b1 00       	push   0xb1bf28
  851467:	6a 00                	push   0x0
  851469:	8b d3                	mov    edx,ebx
  85146b:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85146e:	50                   	push   eax
  85146f:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851472:	ff d0                	call   eax
  851474:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851477:	8b 93 90 00 00 00    	mov    edx,DWORD PTR [ebx+0x90]
  85147d:	50                   	push   eax
  85147e:	51                   	push   ecx
  85147f:	ff d2                	call   edx
  851481:	85 c0                	test   eax,eax
  851483:	0f 8c cc fa ff ff    	jl     0x850f55
  851489:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85148f:	8b 08                	mov    ecx,DWORD PTR [eax]
  851491:	6a 01                	push   0x1
  851493:	8d 55 d4             	lea    edx,[ebp-0x2c]
  851496:	52                   	push   edx
  851497:	50                   	push   eax
  851498:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85149e:	ff d0                	call   eax
  8514a0:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8514a6:	8b 08                	mov    ecx,DWORD PTR [eax]
  8514a8:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  8514ae:	6a 00                	push   0x0
  8514b0:	50                   	push   eax
  8514b1:	ff d2                	call   edx
  8514b3:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8514b9:	8b 08                	mov    ecx,DWORD PTR [eax]
  8514bb:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  8514c1:	50                   	push   eax
  8514c2:	ff d2                	call   edx
  8514c4:	8b 07                	mov    eax,DWORD PTR [edi]
  8514c6:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  8514cc:	6a 02                	push   0x2
  8514ce:	6a 00                	push   0x0
  8514d0:	6a 04                	push   0x4
  8514d2:	6a 00                	push   0x0
  8514d4:	6a 00                	push   0x0
  8514d6:	6a 04                	push   0x4
  8514d8:	57                   	push   edi
  8514d9:	ff d1                	call   ecx
  8514db:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8514e1:	8b 10                	mov    edx,DWORD PTR [eax]
  8514e3:	50                   	push   eax
  8514e4:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8514ea:	ff d0                	call   eax
  8514ec:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8514f2:	8b 08                	mov    ecx,DWORD PTR [eax]
  8514f4:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8514fa:	50                   	push   eax
  8514fb:	ff d2                	call   edx
  8514fd:	8d 4d ec             	lea    ecx,[ebp-0x14]
  851500:	e8 ab ee ff ff       	call   0x8503b0
  851505:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  851508:	83 6d e8 04          	sub    DWORD PTR [ebp-0x18],0x4
  85150c:	83 e8 01             	sub    eax,0x1
  85150f:	85 c0                	test   eax,eax
  851511:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  851514:	0f 87 f6 fd ff ff    	ja     0x851310
  85151a:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851520:	8b 18                	mov    ebx,DWORD PTR [eax]
  851522:	8b cb                	mov    ecx,ebx
  851524:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  851527:	68 10 bf b1 00       	push   0xb1bf10
  85152c:	50                   	push   eax
  85152d:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851530:	ff d2                	call   edx
  851532:	8b 8b e8 00 00 00    	mov    ecx,DWORD PTR [ebx+0xe8]
  851538:	50                   	push   eax
  851539:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85153c:	50                   	push   eax
  85153d:	ff d1                	call   ecx
  85153f:	85 c0                	test   eax,eax
  851541:	0f 8c 0e fa ff ff    	jl     0x850f55
  851547:	8b 96 a0 00 00 00    	mov    edx,DWORD PTR [esi+0xa0]
  85154d:	8b 4e 60             	mov    ecx,DWORD PTR [esi+0x60]
  851550:	b8 01 00 00 00       	mov    eax,0x1
  851555:	31 86 90 00 00 00    	xor    DWORD PTR [esi+0x90],eax
  85155b:	31 86 94 00 00 00    	xor    DWORD PTR [esi+0x94],eax
  851561:	8b c2                	mov    eax,edx
  851563:	8b 18                	mov    ebx,DWORD PTR [eax]
  851565:	51                   	push   ecx
  851566:	68 c4 bf b1 00       	push   0xb1bfc4
  85156b:	6a 00                	push   0x0
  85156d:	8b d3                	mov    edx,ebx
  85156f:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  851572:	50                   	push   eax
  851573:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851576:	ff d0                	call   eax
  851578:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85157b:	8b 93 d0 00 00 00    	mov    edx,DWORD PTR [ebx+0xd0]
  851581:	50                   	push   eax
  851582:	51                   	push   ecx
  851583:	ff d2                	call   edx
  851585:	8b 8e 90 00 00 00    	mov    ecx,DWORD PTR [esi+0x90]
  85158b:	8b 94 8e 88 00 00 00 	mov    edx,DWORD PTR [esi+ecx*4+0x88]
  851592:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851598:	8b 18                	mov    ebx,DWORD PTR [eax]
  85159a:	52                   	push   edx
  85159b:	68 f4 be b1 00       	push   0xb1bef4
  8515a0:	8b cb                	mov    ecx,ebx
  8515a2:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8515a5:	6a 00                	push   0x0
  8515a7:	50                   	push   eax
  8515a8:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  8515ab:	ff d2                	call   edx
  8515ad:	8b 8b d0 00 00 00    	mov    ecx,DWORD PTR [ebx+0xd0]
  8515b3:	50                   	push   eax
  8515b4:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8515b7:	50                   	push   eax
  8515b8:	ff d1                	call   ecx
  8515ba:	8b 96 94 00 00 00    	mov    edx,DWORD PTR [esi+0x94]
  8515c0:	8b 84 96 88 00 00 00 	mov    eax,DWORD PTR [esi+edx*4+0x88]
  8515c7:	8b 08                	mov    ecx,DWORD PTR [eax]
  8515c9:	8d 55 ec             	lea    edx,[ebp-0x14]
  8515cc:	52                   	push   edx
  8515cd:	6a 00                	push   0x0
  8515cf:	50                   	push   eax
  8515d0:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  8515d3:	ff d0                	call   eax
  8515d5:	85 c0                	test   eax,eax
  8515d7:	0f 8c 78 f9 ff ff    	jl     0x850f55
  8515dd:	8b 55 ec             	mov    edx,DWORD PTR [ebp-0x14]
  8515e0:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8515e2:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  8515e8:	52                   	push   edx
  8515e9:	6a 00                	push   0x0
  8515eb:	57                   	push   edi
  8515ec:	ff d0                	call   eax
  8515ee:	8b 96 b4 00 00 00    	mov    edx,DWORD PTR [esi+0xb4]
  8515f4:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8515f6:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  8515fc:	6a 14                	push   0x14
  8515fe:	6a 00                	push   0x0
  851600:	52                   	push   edx
  851601:	6a 00                	push   0x0
  851603:	57                   	push   edi
  851604:	ff d0                	call   eax
  851606:	85 c0                	test   eax,eax
  851608:	0f 8c 47 f9 ff ff    	jl     0x850f55
  85160e:	e8 6d 53 03 00       	call   0x886980
  851613:	8d 88 94 00 00 00    	lea    ecx,[eax+0x94]
  851619:	e8 b2 da bb ff       	call   0x40f0d0
  85161e:	8b c8                	mov    ecx,eax
  851620:	e8 ab 0b bf ff       	call   0x4421d0
  851625:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851628:	d9 ee                	fldz
  85162a:	d8 5e 30             	fcomp  DWORD PTR [esi+0x30]
  85162d:	df e0                	fnstsw ax
  85162f:	f6 c4 41             	test   ah,0x41
  851632:	7a 30                	jp     0x851664
  851634:	d9 46 2c             	fld    DWORD PTR [esi+0x2c]
  851637:	d9 e8                	fld1
  851639:	de e1                	fsubrp st(1),st
  85163b:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  85163e:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  851641:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851644:	d8 66 30             	fsub   DWORD PTR [esi+0x30]
  851647:	dc 0d 88 ac aa 00    	fmul   QWORD PTR ds:0xaaac88
  85164d:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  851650:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  851653:	e8 e8 17 0b 00       	call   0x902e40
  851658:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  85165b:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  85165e:	d9 e8                	fld1
  851660:	de e1                	fsubrp st(1),st
  851662:	eb 02                	jmp    0x851666
  851664:	d9 e8                	fld1
  851666:	8b 8e a0 00 00 00    	mov    ecx,DWORD PTR [esi+0xa0]
  85166c:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  85166f:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851672:	51                   	push   ecx
  851673:	d9 5e 30             	fstp   DWORD PTR [esi+0x30]
  851676:	8b c1                	mov    eax,ecx
  851678:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  85167b:	8b 18                	mov    ebx,DWORD PTR [eax]
  85167d:	d9 1c 24             	fstp   DWORD PTR [esp]
  851680:	68 e0 be b1 00       	push   0xb1bee0
  851685:	6a 00                	push   0x0
  851687:	8b d3                	mov    edx,ebx
  851689:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85168c:	50                   	push   eax
  85168d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851690:	ff d0                	call   eax
  851692:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851695:	8b 53 78             	mov    edx,DWORD PTR [ebx+0x78]
  851698:	50                   	push   eax
  851699:	51                   	push   ecx
  85169a:	ff d2                	call   edx
  85169c:	85 c0                	test   eax,eax
  85169e:	0f 8c b1 f8 ff ff    	jl     0x850f55
  8516a4:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8516aa:	8b 08                	mov    ecx,DWORD PTR [eax]
  8516ac:	6a 01                	push   0x1
  8516ae:	8d 55 d4             	lea    edx,[ebp-0x2c]
  8516b1:	52                   	push   edx
  8516b2:	50                   	push   eax
  8516b3:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  8516b9:	ff d0                	call   eax
  8516bb:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8516c1:	8b 08                	mov    ecx,DWORD PTR [eax]
  8516c3:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  8516c9:	6a 00                	push   0x0
  8516cb:	50                   	push   eax
  8516cc:	ff d2                	call   edx
  8516ce:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8516d4:	8b 08                	mov    ecx,DWORD PTR [eax]
  8516d6:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  8516dc:	50                   	push   eax
  8516dd:	ff d2                	call   edx
  8516df:	8b 07                	mov    eax,DWORD PTR [edi]
  8516e1:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  8516e7:	6a 02                	push   0x2
  8516e9:	6a 00                	push   0x0
  8516eb:	6a 04                	push   0x4
  8516ed:	6a 00                	push   0x0
  8516ef:	6a 00                	push   0x0
  8516f1:	6a 04                	push   0x4
  8516f3:	57                   	push   edi
  8516f4:	ff d1                	call   ecx
  8516f6:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8516fc:	8b 10                	mov    edx,DWORD PTR [eax]
  8516fe:	50                   	push   eax
  8516ff:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  851705:	ff d0                	call   eax
  851707:	8b b6 a0 00 00 00    	mov    esi,DWORD PTR [esi+0xa0]
  85170d:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85170f:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  851715:	56                   	push   esi
  851716:	ff d2                	call   edx
  851718:	8d 4d ec             	lea    ecx,[ebp-0x14]
  85171b:	e8 90 ec ff ff       	call   0x8503b0
  851720:	e8 fd 1e 0d 00       	call   0x923622
  851725:	5f                   	pop    edi
  851726:	5e                   	pop    esi
  851727:	b0 01                	mov    al,0x1
  851729:	5b                   	pop    ebx
  85172a:	8b e5                	mov    esp,ebp
  85172c:	5d                   	pop    ebp
  85172d:	c3                   	ret
```

### `0x00851730..0x008521e9` — sites `0x00851b5f`, `0x00851d9e`, `0x00851f9f`, `0x008521af`

```asm
  851730:	55                   	push   ebp
  851731:	8b ec                	mov    ebp,esp
  851733:	81 ec d4 01 00 00    	sub    esp,0x1d4
  851739:	56                   	push   esi
  85173a:	57                   	push   edi
  85173b:	68 28 c1 b1 00       	push   0xb1c128
  851740:	68 00 00 ff ff       	push   0xffff0000
  851745:	8b f1                	mov    esi,ecx
  851747:	e8 dc 1e 0d 00       	call   0x923628
  85174c:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  851752:	e8 b9 c9 fd ff       	call   0x82e110
  851757:	d9 ee                	fldz
  851759:	d8 5e 18             	fcomp  DWORD PTR [esi+0x18]
  85175c:	8b f8                	mov    edi,eax
  85175e:	df e0                	fnstsw ax
  851760:	f6 c4 01             	test   ah,0x1
  851763:	75 08                	jne    0x85176d
  851765:	5f                   	pop    edi
  851766:	b0 01                	mov    al,0x1
  851768:	5e                   	pop    esi
  851769:	8b e5                	mov    esp,ebp
  85176b:	5d                   	pop    ebp
  85176c:	c3                   	ret
  85176d:	8b 46 78             	mov    eax,DWORD PTR [esi+0x78]
  851770:	8b 08                	mov    ecx,DWORD PTR [eax]
  851772:	53                   	push   ebx
  851773:	8b 5e 5c             	mov    ebx,DWORD PTR [esi+0x5c]
  851776:	8d 55 f0             	lea    edx,[ebp-0x10]
  851779:	52                   	push   edx
  85177a:	6a 00                	push   0x0
  85177c:	50                   	push   eax
  85177d:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  851780:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  851783:	ff d0                	call   eax
  851785:	85 c0                	test   eax,eax
  851787:	0f 8c 9d 09 00 00    	jl     0x85212a
  85178d:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851793:	8b 10                	mov    edx,DWORD PTR [eax]
  851795:	53                   	push   ebx
  851796:	8b c8                	mov    ecx,eax
  851798:	68 14 c1 b1 00       	push   0xb1c114
  85179d:	6a 00                	push   0x0
  85179f:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  8517a2:	8b 09                	mov    ecx,DWORD PTR [ecx]
  8517a4:	50                   	push   eax
  8517a5:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8517a8:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  8517ab:	ff d0                	call   eax
  8517ad:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  8517b0:	50                   	push   eax
  8517b1:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8517b4:	8b 90 d0 00 00 00    	mov    edx,DWORD PTR [eax+0xd0]
  8517ba:	51                   	push   ecx
  8517bb:	ff d2                	call   edx
  8517bd:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  8517c0:	8b 07                	mov    eax,DWORD PTR [edi]
  8517c2:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  8517c8:	51                   	push   ecx
  8517c9:	6a 00                	push   0x0
  8517cb:	57                   	push   edi
  8517cc:	ff d2                	call   edx
  8517ce:	8b 8e cc 00 00 00    	mov    ecx,DWORD PTR [esi+0xcc]
  8517d4:	8b 07                	mov    eax,DWORD PTR [edi]
  8517d6:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  8517dc:	6a 14                	push   0x14
  8517de:	6a 00                	push   0x0
  8517e0:	51                   	push   ecx
  8517e1:	6a 00                	push   0x0
  8517e3:	57                   	push   edi
  8517e4:	ff d2                	call   edx
  8517e6:	85 c0                	test   eax,eax
  8517e8:	0f 8c 3c 09 00 00    	jl     0x85212a
  8517ee:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  8517f1:	8b 01                	mov    eax,DWORD PTR [ecx]
  8517f3:	8b 10                	mov    edx,DWORD PTR [eax]
  8517f5:	ff d2                	call   edx
  8517f7:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  8517fa:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  8517fd:	8b 01                	mov    eax,DWORD PTR [ecx]
  8517ff:	8b 50 04             	mov    edx,DWORD PTR [eax+0x4]
  851802:	ff d2                	call   edx
  851804:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  851807:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85180a:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  85180d:	d9 5d c4             	fstp   DWORD PTR [ebp-0x3c]
  851810:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  851813:	d9 5d c8             	fstp   DWORD PTR [ebp-0x38]
  851816:	d9 ee                	fldz
  851818:	d9 55 cc             	fst    DWORD PTR [ebp-0x34]
  85181b:	d9 5d d0             	fstp   DWORD PTR [ebp-0x30]
  85181e:	8b 01                	mov    eax,DWORD PTR [ecx]
  851820:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  851823:	ff d2                	call   edx
  851825:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851828:	8b 4e 34             	mov    ecx,DWORD PTR [esi+0x34]
  85182b:	8b 01                	mov    eax,DWORD PTR [ecx]
  85182d:	8b 50 0c             	mov    edx,DWORD PTR [eax+0xc]
  851830:	ff d2                	call   edx
  851832:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  851835:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851838:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85183e:	d9 5d b4             	fstp   DWORD PTR [ebp-0x4c]
  851841:	8b c8                	mov    ecx,eax
  851843:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  851846:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851849:	d9 5d b8             	fstp   DWORD PTR [ebp-0x48]
  85184c:	d9 ee                	fldz
  85184e:	d9 55 bc             	fst    DWORD PTR [ebp-0x44]
  851851:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  851854:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851856:	8b 10                	mov    edx,DWORD PTR [eax]
  851858:	8d 4d c4             	lea    ecx,[ebp-0x3c]
  85185b:	51                   	push   ecx
  85185c:	68 08 a6 b1 00       	push   0xb1a608
  851861:	6a 00                	push   0x0
  851863:	50                   	push   eax
  851864:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851867:	ff d0                	call   eax
  851869:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85186c:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  851872:	50                   	push   eax
  851873:	51                   	push   ecx
  851874:	ff d2                	call   edx
  851876:	85 c0                	test   eax,eax
  851878:	0f 8c ac 08 00 00    	jl     0x85212a
  85187e:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851884:	8b 10                	mov    edx,DWORD PTR [eax]
  851886:	8b c8                	mov    ecx,eax
  851888:	8b 19                	mov    ebx,DWORD PTR [ecx]
  85188a:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85188d:	8d 4d b4             	lea    ecx,[ebp-0x4c]
  851890:	51                   	push   ecx
  851891:	68 f8 a5 b1 00       	push   0xb1a5f8
  851896:	6a 00                	push   0x0
  851898:	50                   	push   eax
  851899:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85189c:	ff d0                	call   eax
  85189e:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  8518a1:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  8518a7:	50                   	push   eax
  8518a8:	51                   	push   ecx
  8518a9:	ff d2                	call   edx
  8518ab:	85 c0                	test   eax,eax
  8518ad:	0f 8c 77 08 00 00    	jl     0x85212a
  8518b3:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  8518b6:	8b 08                	mov    ecx,DWORD PTR [eax]
  8518b8:	8d 95 2c ff ff ff    	lea    edx,[ebp-0xd4]
  8518be:	52                   	push   edx
  8518bf:	6a 00                	push   0x0
  8518c1:	50                   	push   eax
  8518c2:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  8518c5:	ff d0                	call   eax
  8518c7:	db 85 44 ff ff ff    	fild   DWORD PTR [ebp-0xbc]
  8518cd:	8b 8d 44 ff ff ff    	mov    ecx,DWORD PTR [ebp-0xbc]
  8518d3:	85 c9                	test   ecx,ecx
  8518d5:	7d 06                	jge    0x8518dd
  8518d7:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8518dd:	d9 e8                	fld1
  8518df:	8b 95 48 ff ff ff    	mov    edx,DWORD PTR [ebp-0xb8]
  8518e5:	85 d2                	test   edx,edx
  8518e7:	d9 c0                	fld    st(0)
  8518e9:	de f2                	fdivrp st(2),st
  8518eb:	d9 c9                	fxch   st(1)
  8518ed:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  8518f0:	db 85 48 ff ff ff    	fild   DWORD PTR [ebp-0xb8]
  8518f6:	7d 06                	jge    0x8518fe
  8518f8:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8518fe:	de f9                	fdivp  st(1),st
  851900:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  851903:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851906:	d9 c0                	fld    st(0)
  851908:	dd 05 18 9a aa 00    	fld    QWORD PTR ds:0xaa9a18
  85190e:	dc c9                	fmul   st(1),st
  851910:	d9 c9                	fxch   st(1)
  851912:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851915:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851918:	d9 55 dc             	fst    DWORD PTR [ebp-0x24]
  85191b:	8b 45 dc             	mov    eax,DWORD PTR [ebp-0x24]
  85191e:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  851921:	89 85 2c fe ff ff    	mov    DWORD PTR [ebp-0x1d4],eax
  851927:	d9 c0                	fld    st(0)
  851929:	dd 05 20 9a aa 00    	fld    QWORD PTR ds:0xaa9a20
  85192f:	dc c9                	fmul   st(1),st
  851931:	d9 c9                	fxch   st(1)
  851933:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851936:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851939:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  85193c:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  85193f:	d9 ee                	fldz
  851941:	89 8d 30 fe ff ff    	mov    DWORD PTR [ebp-0x1d0],ecx
  851947:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  85194a:	d9 55 e8             	fst    DWORD PTR [ebp-0x18]
  85194d:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
  851950:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  851953:	d9 ce                	fxch   st(6)
  851955:	de ca                	fmulp  st(2),st
  851957:	89 95 34 fe ff ff    	mov    DWORD PTR [ebp-0x1cc],edx
  85195d:	d9 c9                	fxch   st(1)
  85195f:	89 85 38 fe ff ff    	mov    DWORD PTR [ebp-0x1c8],eax
  851965:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851968:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85196b:	d9 55 dc             	fst    DWORD PTR [ebp-0x24]
  85196e:	8b 4d dc             	mov    ecx,DWORD PTR [ebp-0x24]
  851971:	d9 c9                	fxch   st(1)
  851973:	89 8d 3c fe ff ff    	mov    DWORD PTR [ebp-0x1c4],ecx
  851979:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  85197c:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  85197f:	d9 cc                	fxch   st(4)
  851981:	89 95 40 fe ff ff    	mov    DWORD PTR [ebp-0x1c0],edx
  851987:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  85198a:	8b 45 e4             	mov    eax,DWORD PTR [ebp-0x1c]
  85198d:	d9 55 e8             	fst    DWORD PTR [ebp-0x18]
  851990:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  851993:	d9 ca                	fxch   st(2)
  851995:	89 85 44 fe ff ff    	mov    DWORD PTR [ebp-0x1bc],eax
  85199b:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  85199e:	8b 55 dc             	mov    edx,DWORD PTR [ebp-0x24]
  8519a1:	89 8d 48 fe ff ff    	mov    DWORD PTR [ebp-0x1b8],ecx
  8519a7:	de ca                	fmulp  st(2),st
  8519a9:	89 95 4c fe ff ff    	mov    DWORD PTR [ebp-0x1b4],edx
  8519af:	d9 c9                	fxch   st(1)
  8519b1:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  8519b4:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  8519b7:	d9 55 e0             	fst    DWORD PTR [ebp-0x20]
  8519ba:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
  8519bd:	d9 c9                	fxch   st(1)
  8519bf:	89 85 50 fe ff ff    	mov    DWORD PTR [ebp-0x1b0],eax
  8519c5:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  8519c8:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
  8519cb:	d9 55 e8             	fst    DWORD PTR [ebp-0x18]
  8519ce:	8b 55 e8             	mov    edx,DWORD PTR [ebp-0x18]
  8519d1:	d9 ca                	fxch   st(2)
  8519d3:	89 8d 54 fe ff ff    	mov    DWORD PTR [ebp-0x1ac],ecx
  8519d9:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  8519dc:	8b 45 dc             	mov    eax,DWORD PTR [ebp-0x24]
  8519df:	89 85 5c fe ff ff    	mov    DWORD PTR [ebp-0x1a4],eax
  8519e5:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  8519e8:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  8519eb:	89 95 58 fe ff ff    	mov    DWORD PTR [ebp-0x1a8],edx
  8519f1:	d9 55 e4             	fst    DWORD PTR [ebp-0x1c]
  8519f4:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
  8519f7:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  8519fa:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  8519fd:	89 85 68 fe ff ff    	mov    DWORD PTR [ebp-0x198],eax
  851a03:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851a09:	89 8d 60 fe ff ff    	mov    DWORD PTR [ebp-0x1a0],ecx
  851a0f:	89 95 64 fe ff ff    	mov    DWORD PTR [ebp-0x19c],edx
  851a15:	8b c8                	mov    ecx,eax
  851a17:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851a19:	8b 10                	mov    edx,DWORD PTR [eax]
  851a1b:	6a 04                	push   0x4
  851a1d:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851a20:	8d 8d 2c fe ff ff    	lea    ecx,[ebp-0x1d4]
  851a26:	51                   	push   ecx
  851a27:	68 fc c0 b1 00       	push   0xb1c0fc
  851a2c:	6a 00                	push   0x0
  851a2e:	50                   	push   eax
  851a2f:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851a32:	ff d0                	call   eax
  851a34:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851a37:	8b 93 90 00 00 00    	mov    edx,DWORD PTR [ebx+0x90]
  851a3d:	50                   	push   eax
  851a3e:	51                   	push   ecx
  851a3f:	ff d2                	call   edx
  851a41:	85 c0                	test   eax,eax
  851a43:	0f 8c e1 06 00 00    	jl     0x85212a
  851a49:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851a4f:	d9 46 18             	fld    DWORD PTR [esi+0x18]
  851a52:	8b c8                	mov    ecx,eax
  851a54:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851a56:	51                   	push   ecx
  851a57:	d9 1c 24             	fstp   DWORD PTR [esp]
  851a5a:	68 f0 c0 b1 00       	push   0xb1c0f0
  851a5f:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851a62:	8b 08                	mov    ecx,DWORD PTR [eax]
  851a64:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  851a67:	6a 00                	push   0x0
  851a69:	50                   	push   eax
  851a6a:	ff d2                	call   edx
  851a6c:	8b 4b 78             	mov    ecx,DWORD PTR [ebx+0x78]
  851a6f:	50                   	push   eax
  851a70:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  851a73:	50                   	push   eax
  851a74:	ff d1                	call   ecx
  851a76:	85 c0                	test   eax,eax
  851a78:	0f 8c ac 06 00 00    	jl     0x85212a
  851a7e:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851a84:	d9 46 10             	fld    DWORD PTR [esi+0x10]
  851a87:	8b 10                	mov    edx,DWORD PTR [eax]
  851a89:	8b c8                	mov    ecx,eax
  851a8b:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851a8d:	51                   	push   ecx
  851a8e:	d9 1c 24             	fstp   DWORD PTR [esp]
  851a91:	68 dc c0 b1 00       	push   0xb1c0dc
  851a96:	6a 00                	push   0x0
  851a98:	50                   	push   eax
  851a99:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851a9c:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851a9f:	ff d0                	call   eax
  851aa1:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851aa4:	8b 53 78             	mov    edx,DWORD PTR [ebx+0x78]
  851aa7:	50                   	push   eax
  851aa8:	51                   	push   ecx
  851aa9:	ff d2                	call   edx
  851aab:	85 c0                	test   eax,eax
  851aad:	0f 8c 77 06 00 00    	jl     0x85212a
  851ab3:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851ab9:	d9 46 14             	fld    DWORD PTR [esi+0x14]
  851abc:	8b c8                	mov    ecx,eax
  851abe:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851ac0:	51                   	push   ecx
  851ac1:	d9 1c 24             	fstp   DWORD PTR [esp]
  851ac4:	68 c8 c0 b1 00       	push   0xb1c0c8
  851ac9:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851acc:	8b 08                	mov    ecx,DWORD PTR [eax]
  851ace:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  851ad1:	6a 00                	push   0x0
  851ad3:	50                   	push   eax
  851ad4:	ff d2                	call   edx
  851ad6:	8b 4b 78             	mov    ecx,DWORD PTR [ebx+0x78]
  851ad9:	50                   	push   eax
  851ada:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  851add:	50                   	push   eax
  851ade:	ff d1                	call   ecx
  851ae0:	85 c0                	test   eax,eax
  851ae2:	0f 8c 42 06 00 00    	jl     0x85212a
  851ae8:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851aee:	8b 10                	mov    edx,DWORD PTR [eax]
  851af0:	8b c8                	mov    ecx,eax
  851af2:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851af4:	68 b8 c0 b1 00       	push   0xb1c0b8
  851af9:	50                   	push   eax
  851afa:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  851afd:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851b00:	ff d0                	call   eax
  851b02:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851b05:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  851b0b:	50                   	push   eax
  851b0c:	51                   	push   ecx
  851b0d:	ff d2                	call   edx
  851b0f:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851b15:	8b 08                	mov    ecx,DWORD PTR [eax]
  851b17:	6a 01                	push   0x1
  851b19:	8d 55 d8             	lea    edx,[ebp-0x28]
  851b1c:	52                   	push   edx
  851b1d:	50                   	push   eax
  851b1e:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  851b24:	ff d0                	call   eax
  851b26:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851b2c:	8b 08                	mov    ecx,DWORD PTR [eax]
  851b2e:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  851b34:	6a 00                	push   0x0
  851b36:	50                   	push   eax
  851b37:	ff d2                	call   edx
  851b39:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851b3f:	8b 08                	mov    ecx,DWORD PTR [eax]
  851b41:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  851b47:	50                   	push   eax
  851b48:	ff d2                	call   edx
  851b4a:	8b 07                	mov    eax,DWORD PTR [edi]
  851b4c:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  851b52:	6a 02                	push   0x2
  851b54:	6a 00                	push   0x0
  851b56:	6a 04                	push   0x4
  851b58:	6a 00                	push   0x0
  851b5a:	6a 00                	push   0x0
  851b5c:	6a 04                	push   0x4
  851b5e:	57                   	push   edi
  851b5f:	ff d1                	call   ecx
  851b61:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851b67:	8b 10                	mov    edx,DWORD PTR [eax]
  851b69:	50                   	push   eax
  851b6a:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  851b70:	ff d0                	call   eax
  851b72:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851b78:	8b 08                	mov    ecx,DWORD PTR [eax]
  851b7a:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  851b80:	50                   	push   eax
  851b81:	ff d2                	call   edx
  851b83:	8d 4d f0             	lea    ecx,[ebp-0x10]
  851b86:	e8 25 e8 ff ff       	call   0x8503b0
  851b8b:	8b 46 7c             	mov    eax,DWORD PTR [esi+0x7c]
  851b8e:	8b 08                	mov    ecx,DWORD PTR [eax]
  851b90:	8b 5e 78             	mov    ebx,DWORD PTR [esi+0x78]
  851b93:	8d 55 f0             	lea    edx,[ebp-0x10]
  851b96:	52                   	push   edx
  851b97:	6a 00                	push   0x0
  851b99:	50                   	push   eax
  851b9a:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  851b9d:	ff d0                	call   eax
  851b9f:	85 c0                	test   eax,eax
  851ba1:	0f 8c 88 05 00 00    	jl     0x85212f
  851ba7:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851bad:	8b 10                	mov    edx,DWORD PTR [eax]
  851baf:	53                   	push   ebx
  851bb0:	8b c8                	mov    ecx,eax
  851bb2:	68 14 c1 b1 00       	push   0xb1c114
  851bb7:	6a 00                	push   0x0
  851bb9:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  851bbc:	8b 09                	mov    ecx,DWORD PTR [ecx]
  851bbe:	50                   	push   eax
  851bbf:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851bc2:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  851bc5:	ff d0                	call   eax
  851bc7:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  851bca:	50                   	push   eax
  851bcb:	8b 45 ec             	mov    eax,DWORD PTR [ebp-0x14]
  851bce:	8b 90 d0 00 00 00    	mov    edx,DWORD PTR [eax+0xd0]
  851bd4:	51                   	push   ecx
  851bd5:	ff d2                	call   edx
  851bd7:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  851bda:	8b 07                	mov    eax,DWORD PTR [edi]
  851bdc:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  851be2:	51                   	push   ecx
  851be3:	6a 00                	push   0x0
  851be5:	57                   	push   edi
  851be6:	ff d2                	call   edx
  851be8:	8b 8e d0 00 00 00    	mov    ecx,DWORD PTR [esi+0xd0]
  851bee:	8b 07                	mov    eax,DWORD PTR [edi]
  851bf0:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  851bf6:	6a 14                	push   0x14
  851bf8:	6a 00                	push   0x0
  851bfa:	51                   	push   ecx
  851bfb:	6a 00                	push   0x0
  851bfd:	57                   	push   edi
  851bfe:	ff d2                	call   edx
  851c00:	85 c0                	test   eax,eax
  851c02:	0f 8c 22 05 00 00    	jl     0x85212a
  851c08:	8d 55 94             	lea    edx,[ebp-0x6c]
  851c0b:	52                   	push   edx
  851c0c:	8b c3                	mov    eax,ebx
  851c0e:	8b 08                	mov    ecx,DWORD PTR [eax]
  851c10:	6a 00                	push   0x0
  851c12:	50                   	push   eax
  851c13:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  851c16:	ff d0                	call   eax
  851c18:	db 45 ac             	fild   DWORD PTR [ebp-0x54]
  851c1b:	8b 4d ac             	mov    ecx,DWORD PTR [ebp-0x54]
  851c1e:	85 c9                	test   ecx,ecx
  851c20:	7d 06                	jge    0x851c28
  851c22:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  851c28:	d9 e8                	fld1
  851c2a:	8b 55 b0             	mov    edx,DWORD PTR [ebp-0x50]
  851c2d:	85 d2                	test   edx,edx
  851c2f:	d9 c0                	fld    st(0)
  851c31:	de f2                	fdivrp st(2),st
  851c33:	d9 c9                	fxch   st(1)
  851c35:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  851c38:	db 45 b0             	fild   DWORD PTR [ebp-0x50]
  851c3b:	7d 06                	jge    0x851c43
  851c3d:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  851c43:	de f9                	fdivp  st(1),st
  851c45:	b9 fe ff ff ff       	mov    ecx,0xfffffffe
  851c4a:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  851c4d:	8d 85 30 fe ff ff    	lea    eax,[ebp-0x1d0]
  851c53:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851c56:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851c59:	dd 05 00 3e b0 00    	fld    QWORD PTR ds:0xb03e00
  851c5f:	d8 c9                	fmul   st,st(1)
  851c61:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  851c64:	dd 05 18 9a aa 00    	fld    QWORD PTR ds:0xaa9a18
  851c6a:	d8 c9                	fmul   st,st(1)
  851c6c:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  851c6f:	d9 ee                	fldz
  851c71:	dd 05 20 9a aa 00    	fld    QWORD PTR ds:0xaa9a20
  851c77:	dc c1                	fadd   st(1),st
  851c79:	d9 c2                	fld    st(2)
  851c7b:	de ca                	fmulp  st(2),st
  851c7d:	d9 c9                	fxch   st(1)
  851c7f:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  851c82:	d9 c9                	fxch   st(1)
  851c84:	dc 0d 18 4d ab 00    	fmul   QWORD PTR ds:0xab4d18
  851c8a:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851c8d:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  851c90:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  851c93:	d9 45 d4             	fld    DWORD PTR [ebp-0x2c]
  851c96:	d9 45 e8             	fld    DWORD PTR [ebp-0x18]
  851c99:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851c9c:	eb 08                	jmp    0x851ca6
  851c9e:	d9 ca                	fxch   st(2)
  851ca0:	d9 cb                	fxch   st(3)
  851ca2:	d9 c9                	fxch   st(1)
  851ca4:	d9 ca                	fxch   st(2)
  851ca6:	db 45 f4             	fild   DWORD PTR [ebp-0xc]
  851ca9:	83 c1 01             	add    ecx,0x1
  851cac:	83 c0 40             	add    eax,0x40
  851caf:	83 f9 02             	cmp    ecx,0x2
  851cb2:	d8 c6                	fadd   st,st(6)
  851cb4:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  851cb7:	d8 cd                	fmul   st,st(5)
  851cb9:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851cbc:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851cbf:	d9 50 bc             	fst    DWORD PTR [eax-0x44]
  851cc2:	d9 50 cc             	fst    DWORD PTR [eax-0x34]
  851cc5:	d9 50 dc             	fst    DWORD PTR [eax-0x24]
  851cc8:	d9 58 ec             	fstp   DWORD PTR [eax-0x14]
  851ccb:	d9 cb                	fxch   st(3)
  851ccd:	d9 50 c0             	fst    DWORD PTR [eax-0x40]
  851cd0:	d9 ca                	fxch   st(2)
  851cd2:	d9 50 d0             	fst    DWORD PTR [eax-0x30]
  851cd5:	d9 c9                	fxch   st(1)
  851cd7:	d9 50 e0             	fst    DWORD PTR [eax-0x20]
  851cda:	d9 cb                	fxch   st(3)
  851cdc:	d9 50 f0             	fst    DWORD PTR [eax-0x10]
  851cdf:	7c bd                	jl     0x851c9e
  851ce1:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851ce7:	dd dd                	fstp   st(5)
  851ce9:	8b 10                	mov    edx,DWORD PTR [eax]
  851ceb:	dd db                	fstp   st(3)
  851ced:	8b c8                	mov    ecx,eax
  851cef:	dd d8                	fstp   st(0)
  851cf1:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851cf3:	dd d9                	fstp   st(1)
  851cf5:	6a 10                	push   0x10
  851cf7:	dd d8                	fstp   st(0)
  851cf9:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851cfc:	dd d8                	fstp   st(0)
  851cfe:	8d 8d 2c fe ff ff    	lea    ecx,[ebp-0x1d4]
  851d04:	51                   	push   ecx
  851d05:	68 a0 c0 b1 00       	push   0xb1c0a0
  851d0a:	6a 00                	push   0x0
  851d0c:	50                   	push   eax
  851d0d:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851d10:	ff d0                	call   eax
  851d12:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  851d15:	8b 93 90 00 00 00    	mov    edx,DWORD PTR [ebx+0x90]
  851d1b:	50                   	push   eax
  851d1c:	51                   	push   ecx
  851d1d:	ff d2                	call   edx
  851d1f:	85 c0                	test   eax,eax
  851d21:	0f 8c 03 04 00 00    	jl     0x85212a
  851d27:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851d2d:	8b c8                	mov    ecx,eax
  851d2f:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851d31:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851d34:	8b 08                	mov    ecx,DWORD PTR [eax]
  851d36:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  851d39:	68 8c c0 b1 00       	push   0xb1c08c
  851d3e:	50                   	push   eax
  851d3f:	ff d2                	call   edx
  851d41:	8b 8b e8 00 00 00    	mov    ecx,DWORD PTR [ebx+0xe8]
  851d47:	50                   	push   eax
  851d48:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  851d4b:	50                   	push   eax
  851d4c:	ff d1                	call   ecx
  851d4e:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851d54:	8b 10                	mov    edx,DWORD PTR [eax]
  851d56:	8b 92 fc 00 00 00    	mov    edx,DWORD PTR [edx+0xfc]
  851d5c:	6a 01                	push   0x1
  851d5e:	8d 4d d8             	lea    ecx,[ebp-0x28]
  851d61:	51                   	push   ecx
  851d62:	50                   	push   eax
  851d63:	ff d2                	call   edx
  851d65:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851d6b:	8b 08                	mov    ecx,DWORD PTR [eax]
  851d6d:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  851d73:	6a 00                	push   0x0
  851d75:	50                   	push   eax
  851d76:	ff d2                	call   edx
  851d78:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851d7e:	8b 08                	mov    ecx,DWORD PTR [eax]
  851d80:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  851d86:	50                   	push   eax
  851d87:	ff d2                	call   edx
  851d89:	8b 07                	mov    eax,DWORD PTR [edi]
  851d8b:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  851d91:	6a 02                	push   0x2
  851d93:	6a 00                	push   0x0
  851d95:	6a 04                	push   0x4
  851d97:	6a 00                	push   0x0
  851d99:	6a 00                	push   0x0
  851d9b:	6a 04                	push   0x4
  851d9d:	57                   	push   edi
  851d9e:	ff d1                	call   ecx
  851da0:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851da6:	8b 10                	mov    edx,DWORD PTR [eax]
  851da8:	50                   	push   eax
  851da9:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  851daf:	ff d0                	call   eax
  851db1:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851db7:	8b 08                	mov    ecx,DWORD PTR [eax]
  851db9:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  851dbf:	50                   	push   eax
  851dc0:	ff d2                	call   edx
  851dc2:	8d 4d f0             	lea    ecx,[ebp-0x10]
  851dc5:	e8 e6 e5 ff ff       	call   0x8503b0
  851dca:	8b 86 80 00 00 00    	mov    eax,DWORD PTR [esi+0x80]
  851dd0:	8b 08                	mov    ecx,DWORD PTR [eax]
  851dd2:	8b 5e 7c             	mov    ebx,DWORD PTR [esi+0x7c]
  851dd5:	8d 55 f0             	lea    edx,[ebp-0x10]
  851dd8:	52                   	push   edx
  851dd9:	6a 00                	push   0x0
  851ddb:	50                   	push   eax
  851ddc:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  851ddf:	ff d0                	call   eax
  851de1:	85 c0                	test   eax,eax
  851de3:	0f 8c 41 03 00 00    	jl     0x85212a
  851de9:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851def:	8b 10                	mov    edx,DWORD PTR [eax]
  851df1:	53                   	push   ebx
  851df2:	8b c8                	mov    ecx,eax
  851df4:	68 14 c1 b1 00       	push   0xb1c114
  851df9:	6a 00                	push   0x0
  851dfb:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851dfe:	8b 09                	mov    ecx,DWORD PTR [ecx]
  851e00:	50                   	push   eax
  851e01:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  851e04:	89 4d e8             	mov    DWORD PTR [ebp-0x18],ecx
  851e07:	ff d0                	call   eax
  851e09:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  851e0c:	50                   	push   eax
  851e0d:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  851e10:	8b 90 d0 00 00 00    	mov    edx,DWORD PTR [eax+0xd0]
  851e16:	51                   	push   ecx
  851e17:	ff d2                	call   edx
  851e19:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  851e1c:	8b 07                	mov    eax,DWORD PTR [edi]
  851e1e:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  851e24:	51                   	push   ecx
  851e25:	6a 00                	push   0x0
  851e27:	57                   	push   edi
  851e28:	ff d2                	call   edx
  851e2a:	8b 8e d4 00 00 00    	mov    ecx,DWORD PTR [esi+0xd4]
  851e30:	8b 07                	mov    eax,DWORD PTR [edi]
  851e32:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  851e38:	6a 14                	push   0x14
  851e3a:	6a 00                	push   0x0
  851e3c:	51                   	push   ecx
  851e3d:	6a 00                	push   0x0
  851e3f:	57                   	push   edi
  851e40:	ff d2                	call   edx
  851e42:	85 c0                	test   eax,eax
  851e44:	0f 8c e0 02 00 00    	jl     0x85212a
  851e4a:	8d 55 94             	lea    edx,[ebp-0x6c]
  851e4d:	52                   	push   edx
  851e4e:	8b c3                	mov    eax,ebx
  851e50:	8b 08                	mov    ecx,DWORD PTR [eax]
  851e52:	6a 00                	push   0x0
  851e54:	50                   	push   eax
  851e55:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  851e58:	ff d0                	call   eax
  851e5a:	db 45 ac             	fild   DWORD PTR [ebp-0x54]
  851e5d:	8b 4d ac             	mov    ecx,DWORD PTR [ebp-0x54]
  851e60:	33 db                	xor    ebx,ebx
  851e62:	85 c9                	test   ecx,ecx
  851e64:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  851e67:	7d 06                	jge    0x851e6f
  851e69:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  851e6f:	d9 e8                	fld1
  851e71:	de f1                	fdivrp st(1),st
  851e73:	dd 5d e4             	fstp   QWORD PTR [ebp-0x1c]
  851e76:	db 45 f4             	fild   DWORD PTR [ebp-0xc]
  851e79:	51                   	push   ecx
  851e7a:	8b ce                	mov    ecx,esi
  851e7c:	dc 25 b8 44 ab 00    	fsub   QWORD PTR ds:0xab44b8
  851e82:	dd 45 e4             	fld    QWORD PTR [ebp-0x1c]
  851e85:	d8 c9                	fmul   st,st(1)
  851e87:	d9 9c 9d 70 ff ff ff 	fstp   DWORD PTR [ebp+ebx*4-0x90]
  851e8e:	dc 0d 08 9b aa 00    	fmul   QWORD PTR ds:0xaa9b08
  851e94:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  851e97:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  851e9a:	d9 1c 24             	fstp   DWORD PTR [esp]
  851e9d:	e8 9e e4 ff ff       	call   0x850340
  851ea2:	d9 9c 9d 4c ff ff ff 	fstp   DWORD PTR [ebp+ebx*4-0xb4]
  851ea9:	83 c3 01             	add    ebx,0x1
  851eac:	83 fb 09             	cmp    ebx,0x9
  851eaf:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  851eb2:	7c c2                	jl     0x851e76
  851eb4:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851eba:	6a 09                	push   0x9
  851ebc:	8d 95 4c ff ff ff    	lea    edx,[ebp-0xb4]
  851ec2:	52                   	push   edx
  851ec3:	8b c8                	mov    ecx,eax
  851ec5:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851ec7:	68 78 c0 b1 00       	push   0xb1c078
  851ecc:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851ecf:	8b 08                	mov    ecx,DWORD PTR [eax]
  851ed1:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  851ed4:	6a 00                	push   0x0
  851ed6:	50                   	push   eax
  851ed7:	ff d2                	call   edx
  851ed9:	8b 8b 80 00 00 00    	mov    ecx,DWORD PTR [ebx+0x80]
  851edf:	50                   	push   eax
  851ee0:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  851ee3:	50                   	push   eax
  851ee4:	ff d1                	call   ecx
  851ee6:	85 c0                	test   eax,eax
  851ee8:	0f 8c 3c 02 00 00    	jl     0x85212a
  851eee:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851ef4:	6a 09                	push   0x9
  851ef6:	8d 95 70 ff ff ff    	lea    edx,[ebp-0x90]
  851efc:	52                   	push   edx
  851efd:	8b c8                	mov    ecx,eax
  851eff:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851f01:	68 64 c0 b1 00       	push   0xb1c064
  851f06:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851f09:	8b 08                	mov    ecx,DWORD PTR [eax]
  851f0b:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  851f0e:	6a 00                	push   0x0
  851f10:	50                   	push   eax
  851f11:	ff d2                	call   edx
  851f13:	8b 8b 80 00 00 00    	mov    ecx,DWORD PTR [ebx+0x80]
  851f19:	50                   	push   eax
  851f1a:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  851f1d:	50                   	push   eax
  851f1e:	ff d1                	call   ecx
  851f20:	85 c0                	test   eax,eax
  851f22:	0f 8c 02 02 00 00    	jl     0x85212a
  851f28:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851f2e:	8b 10                	mov    edx,DWORD PTR [eax]
  851f30:	8b c8                	mov    ecx,eax
  851f32:	8b 19                	mov    ebx,DWORD PTR [ecx]
  851f34:	68 54 c0 b1 00       	push   0xb1c054
  851f39:	50                   	push   eax
  851f3a:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  851f3d:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  851f40:	ff d0                	call   eax
  851f42:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  851f45:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  851f4b:	50                   	push   eax
  851f4c:	51                   	push   ecx
  851f4d:	ff d2                	call   edx
  851f4f:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851f55:	8b 08                	mov    ecx,DWORD PTR [eax]
  851f57:	6a 01                	push   0x1
  851f59:	8d 55 d8             	lea    edx,[ebp-0x28]
  851f5c:	52                   	push   edx
  851f5d:	50                   	push   eax
  851f5e:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  851f64:	ff d0                	call   eax
  851f66:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851f6c:	8b 08                	mov    ecx,DWORD PTR [eax]
  851f6e:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  851f74:	6a 00                	push   0x0
  851f76:	50                   	push   eax
  851f77:	ff d2                	call   edx
  851f79:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851f7f:	8b 08                	mov    ecx,DWORD PTR [eax]
  851f81:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  851f87:	50                   	push   eax
  851f88:	ff d2                	call   edx
  851f8a:	8b 07                	mov    eax,DWORD PTR [edi]
  851f8c:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  851f92:	6a 02                	push   0x2
  851f94:	6a 00                	push   0x0
  851f96:	6a 04                	push   0x4
  851f98:	6a 00                	push   0x0
  851f9a:	6a 00                	push   0x0
  851f9c:	6a 04                	push   0x4
  851f9e:	57                   	push   edi
  851f9f:	ff d1                	call   ecx
  851fa1:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851fa7:	8b 10                	mov    edx,DWORD PTR [eax]
  851fa9:	50                   	push   eax
  851faa:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  851fb0:	ff d0                	call   eax
  851fb2:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851fb8:	8b 08                	mov    ecx,DWORD PTR [eax]
  851fba:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  851fc0:	50                   	push   eax
  851fc1:	ff d2                	call   edx
  851fc3:	8d 4d f0             	lea    ecx,[ebp-0x10]
  851fc6:	e8 e5 e3 ff ff       	call   0x8503b0
  851fcb:	8b 86 84 00 00 00    	mov    eax,DWORD PTR [esi+0x84]
  851fd1:	8b 08                	mov    ecx,DWORD PTR [eax]
  851fd3:	8b 9e 80 00 00 00    	mov    ebx,DWORD PTR [esi+0x80]
  851fd9:	8d 55 f0             	lea    edx,[ebp-0x10]
  851fdc:	52                   	push   edx
  851fdd:	6a 00                	push   0x0
  851fdf:	50                   	push   eax
  851fe0:	8b 41 48             	mov    eax,DWORD PTR [ecx+0x48]
  851fe3:	ff d0                	call   eax
  851fe5:	85 c0                	test   eax,eax
  851fe7:	0f 8c 3d 01 00 00    	jl     0x85212a
  851fed:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  851ff3:	8b 10                	mov    edx,DWORD PTR [eax]
  851ff5:	53                   	push   ebx
  851ff6:	8b c8                	mov    ecx,eax
  851ff8:	68 14 c1 b1 00       	push   0xb1c114
  851ffd:	6a 00                	push   0x0
  851fff:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  852002:	8b 09                	mov    ecx,DWORD PTR [ecx]
  852004:	50                   	push   eax
  852005:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  852008:	89 4d e8             	mov    DWORD PTR [ebp-0x18],ecx
  85200b:	ff d0                	call   eax
  85200d:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  852010:	50                   	push   eax
  852011:	8b 45 e8             	mov    eax,DWORD PTR [ebp-0x18]
  852014:	8b 90 d0 00 00 00    	mov    edx,DWORD PTR [eax+0xd0]
  85201a:	51                   	push   ecx
  85201b:	ff d2                	call   edx
  85201d:	8b 4d f0             	mov    ecx,DWORD PTR [ebp-0x10]
  852020:	8b 07                	mov    eax,DWORD PTR [edi]
  852022:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  852028:	51                   	push   ecx
  852029:	6a 00                	push   0x0
  85202b:	57                   	push   edi
  85202c:	ff d2                	call   edx
  85202e:	8b 8e d8 00 00 00    	mov    ecx,DWORD PTR [esi+0xd8]
  852034:	8b 07                	mov    eax,DWORD PTR [edi]
  852036:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  85203c:	6a 14                	push   0x14
  85203e:	6a 00                	push   0x0
  852040:	51                   	push   ecx
  852041:	6a 00                	push   0x0
  852043:	57                   	push   edi
  852044:	ff d2                	call   edx
  852046:	85 c0                	test   eax,eax
  852048:	0f 8c dc 00 00 00    	jl     0x85212a
  85204e:	8d 55 94             	lea    edx,[ebp-0x6c]
  852051:	52                   	push   edx
  852052:	8b c3                	mov    eax,ebx
  852054:	8b 08                	mov    ecx,DWORD PTR [eax]
  852056:	6a 00                	push   0x0
  852058:	50                   	push   eax
  852059:	8b 41 44             	mov    eax,DWORD PTR [ecx+0x44]
  85205c:	ff d0                	call   eax
  85205e:	db 45 b0             	fild   DWORD PTR [ebp-0x50]
  852061:	8b 4d b0             	mov    ecx,DWORD PTR [ebp-0x50]
  852064:	33 db                	xor    ebx,ebx
  852066:	85 c9                	test   ecx,ecx
  852068:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  85206b:	7d 06                	jge    0x852073
  85206d:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  852073:	d9 e8                	fld1
  852075:	de f1                	fdivrp st(1),st
  852077:	dd 5d e4             	fstp   QWORD PTR [ebp-0x1c]
  85207a:	8d 9b 00 00 00 00    	lea    ebx,[ebx+0x0]
  852080:	db 45 f4             	fild   DWORD PTR [ebp-0xc]
  852083:	51                   	push   ecx
  852084:	8b ce                	mov    ecx,esi
  852086:	dc 25 b8 44 ab 00    	fsub   QWORD PTR ds:0xab44b8
  85208c:	dd 45 e4             	fld    QWORD PTR [ebp-0x1c]
  85208f:	d8 c9                	fmul   st,st(1)
  852091:	d9 9c 9d 70 ff ff ff 	fstp   DWORD PTR [ebp+ebx*4-0x90]
  852098:	dc 0d 08 9b aa 00    	fmul   QWORD PTR ds:0xaa9b08
  85209e:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  8520a1:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  8520a4:	d9 1c 24             	fstp   DWORD PTR [esp]
  8520a7:	e8 94 e2 ff ff       	call   0x850340
  8520ac:	d9 9c 9d 4c ff ff ff 	fstp   DWORD PTR [ebp+ebx*4-0xb4]
  8520b3:	83 c3 01             	add    ebx,0x1
  8520b6:	83 fb 09             	cmp    ebx,0x9
  8520b9:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  8520bc:	7c c2                	jl     0x852080
  8520be:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8520c4:	6a 09                	push   0x9
  8520c6:	8d 95 4c ff ff ff    	lea    edx,[ebp-0xb4]
  8520cc:	52                   	push   edx
  8520cd:	8b c8                	mov    ecx,eax
  8520cf:	8b 19                	mov    ebx,DWORD PTR [ecx]
  8520d1:	68 44 c0 b1 00       	push   0xb1c044
  8520d6:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  8520d9:	8b 08                	mov    ecx,DWORD PTR [eax]
  8520db:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8520de:	6a 00                	push   0x0
  8520e0:	50                   	push   eax
  8520e1:	ff d2                	call   edx
  8520e3:	8b 8b 80 00 00 00    	mov    ecx,DWORD PTR [ebx+0x80]
  8520e9:	50                   	push   eax
  8520ea:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  8520ed:	50                   	push   eax
  8520ee:	ff d1                	call   ecx
  8520f0:	85 c0                	test   eax,eax
  8520f2:	7c 36                	jl     0x85212a
  8520f4:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8520fa:	6a 09                	push   0x9
  8520fc:	8d 95 70 ff ff ff    	lea    edx,[ebp-0x90]
  852102:	52                   	push   edx
  852103:	8b c8                	mov    ecx,eax
  852105:	8b 19                	mov    ebx,DWORD PTR [ecx]
  852107:	68 34 c0 b1 00       	push   0xb1c034
  85210c:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  85210f:	8b 08                	mov    ecx,DWORD PTR [eax]
  852111:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  852114:	6a 00                	push   0x0
  852116:	50                   	push   eax
  852117:	ff d2                	call   edx
  852119:	8b 8b 80 00 00 00    	mov    ecx,DWORD PTR [ebx+0x80]
  85211f:	50                   	push   eax
  852120:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  852123:	50                   	push   eax
  852124:	ff d1                	call   ecx
  852126:	85 c0                	test   eax,eax
  852128:	7d 0e                	jge    0x852138
  85212a:	e8 f3 14 0d 00       	call   0x923622
  85212f:	5b                   	pop    ebx
  852130:	5f                   	pop    edi
  852131:	32 c0                	xor    al,al
  852133:	5e                   	pop    esi
  852134:	8b e5                	mov    esp,ebp
  852136:	5d                   	pop    ebp
  852137:	c3                   	ret
  852138:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85213e:	8b 10                	mov    edx,DWORD PTR [eax]
  852140:	8b c8                	mov    ecx,eax
  852142:	8b 19                	mov    ebx,DWORD PTR [ecx]
  852144:	68 20 c0 b1 00       	push   0xb1c020
  852149:	50                   	push   eax
  85214a:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  85214d:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  852150:	ff d0                	call   eax
  852152:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  852155:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  85215b:	50                   	push   eax
  85215c:	51                   	push   ecx
  85215d:	ff d2                	call   edx
  85215f:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  852165:	8b 08                	mov    ecx,DWORD PTR [eax]
  852167:	6a 01                	push   0x1
  852169:	8d 55 d8             	lea    edx,[ebp-0x28]
  85216c:	52                   	push   edx
  85216d:	50                   	push   eax
  85216e:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  852174:	ff d0                	call   eax
  852176:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85217c:	8b 08                	mov    ecx,DWORD PTR [eax]
  85217e:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  852184:	6a 00                	push   0x0
  852186:	50                   	push   eax
  852187:	ff d2                	call   edx
  852189:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  85218f:	8b 08                	mov    ecx,DWORD PTR [eax]
  852191:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  852197:	50                   	push   eax
  852198:	ff d2                	call   edx
  85219a:	8b 07                	mov    eax,DWORD PTR [edi]
  85219c:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  8521a2:	6a 02                	push   0x2
  8521a4:	6a 00                	push   0x0
  8521a6:	6a 04                	push   0x4
  8521a8:	6a 00                	push   0x0
  8521aa:	6a 00                	push   0x0
  8521ac:	6a 04                	push   0x4
  8521ae:	57                   	push   edi
  8521af:	ff d1                	call   ecx
  8521b1:	8b 86 a0 00 00 00    	mov    eax,DWORD PTR [esi+0xa0]
  8521b7:	8b 10                	mov    edx,DWORD PTR [eax]
  8521b9:	50                   	push   eax
  8521ba:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  8521c0:	ff d0                	call   eax
  8521c2:	8b b6 a0 00 00 00    	mov    esi,DWORD PTR [esi+0xa0]
  8521c8:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8521ca:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  8521d0:	56                   	push   esi
  8521d1:	ff d2                	call   edx
  8521d3:	8d 4d f0             	lea    ecx,[ebp-0x10]
  8521d6:	e8 d5 e1 ff ff       	call   0x8503b0
  8521db:	e8 42 14 0d 00       	call   0x923622
  8521e0:	5b                   	pop    ebx
  8521e1:	5f                   	pop    edi
  8521e2:	b0 01                	mov    al,0x1
  8521e4:	5e                   	pop    esi
  8521e5:	8b e5                	mov    esp,ebp
  8521e7:	5d                   	pop    ebp
  8521e8:	c3                   	ret
```

### `0x008521f0..0x0085257a` — sites `0x00852554`

```asm
  8521f0:	55                   	push   ebp
  8521f1:	8b ec                	mov    ebp,esp
  8521f3:	83 ec 50             	sub    esp,0x50
  8521f6:	56                   	push   esi
  8521f7:	57                   	push   edi
  8521f8:	68 10 c2 b1 00       	push   0xb1c210
  8521fd:	68 00 00 ff ff       	push   0xffff0000
  852202:	8b f9                	mov    edi,ecx
  852204:	e8 1f 14 0d 00       	call   0x923628
  852209:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85220f:	e8 fc be fd ff       	call   0x82e110
  852214:	8b 4f 34             	mov    ecx,DWORD PTR [edi+0x34]
  852217:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85221a:	8b 01                	mov    eax,DWORD PTR [ecx]
  85221c:	8b 10                	mov    edx,DWORD PTR [eax]
  85221e:	ff d2                	call   edx
  852220:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  852223:	8b 4f 34             	mov    ecx,DWORD PTR [edi+0x34]
  852226:	8b 01                	mov    eax,DWORD PTR [ecx]
  852228:	8b 50 04             	mov    edx,DWORD PTR [eax+0x4]
  85222b:	ff d2                	call   edx
  85222d:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  852230:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  852233:	8b 4f 34             	mov    ecx,DWORD PTR [edi+0x34]
  852236:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  852239:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  85223c:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  85223f:	d9 ee                	fldz
  852241:	d9 55 e8             	fst    DWORD PTR [ebp-0x18]
  852244:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  852247:	8b 01                	mov    eax,DWORD PTR [ecx]
  852249:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  85224c:	ff d2                	call   edx
  85224e:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  852251:	8b 4f 34             	mov    ecx,DWORD PTR [edi+0x34]
  852254:	8b 01                	mov    eax,DWORD PTR [ecx]
  852256:	8b 50 0c             	mov    edx,DWORD PTR [eax+0xc]
  852259:	ff d2                	call   edx
  85225b:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  85225e:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  852261:	8b b7 a4 00 00 00    	mov    esi,DWORD PTR [edi+0xa4]
  852267:	85 f6                	test   esi,esi
  852269:	d9 5d d0             	fstp   DWORD PTR [ebp-0x30]
  85226c:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85226f:	d9 5d d4             	fstp   DWORD PTR [ebp-0x2c]
  852272:	d9 ee                	fldz
  852274:	d9 55 d8             	fst    DWORD PTR [ebp-0x28]
  852277:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  85227a:	75 08                	jne    0x852284
  85227c:	5f                   	pop    edi
  85227d:	32 c0                	xor    al,al
  85227f:	5e                   	pop    esi
  852280:	8b e5                	mov    esp,ebp
  852282:	5d                   	pop    ebp
  852283:	c3                   	ret
  852284:	53                   	push   ebx
  852285:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852287:	8d 45 e0             	lea    eax,[ebp-0x20]
  85228a:	50                   	push   eax
  85228b:	68 08 a6 b1 00       	push   0xb1a608
  852290:	8b cb                	mov    ecx,ebx
  852292:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  852295:	6a 00                	push   0x0
  852297:	56                   	push   esi
  852298:	ff d2                	call   edx
  85229a:	50                   	push   eax
  85229b:	8b 83 88 00 00 00    	mov    eax,DWORD PTR [ebx+0x88]
  8522a1:	56                   	push   esi
  8522a2:	ff d0                	call   eax
  8522a4:	85 c0                	test   eax,eax
  8522a6:	0f 8c d0 00 00 00    	jl     0x85237c
  8522ac:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8522ae:	8d 4d d0             	lea    ecx,[ebp-0x30]
  8522b1:	51                   	push   ecx
  8522b2:	68 f8 a5 b1 00       	push   0xb1a5f8
  8522b7:	8b d3                	mov    edx,ebx
  8522b9:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8522bc:	6a 00                	push   0x0
  8522be:	56                   	push   esi
  8522bf:	ff d0                	call   eax
  8522c1:	8b 8b 88 00 00 00    	mov    ecx,DWORD PTR [ebx+0x88]
  8522c7:	50                   	push   eax
  8522c8:	56                   	push   esi
  8522c9:	ff d1                	call   ecx
  8522cb:	85 c0                	test   eax,eax
  8522cd:	0f 8c a9 00 00 00    	jl     0x85237c
  8522d3:	8b 47 5c             	mov    eax,DWORD PTR [edi+0x5c]
  8522d6:	8b 97 84 00 00 00    	mov    edx,DWORD PTR [edi+0x84]
  8522dc:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8522de:	8b 8f 9c 00 00 00    	mov    ecx,DWORD PTR [edi+0x9c]
  8522e4:	50                   	push   eax
  8522e5:	68 00 c2 b1 00       	push   0xb1c200
  8522ea:	89 55 fc             	mov    DWORD PTR [ebp-0x4],edx
  8522ed:	8b d3                	mov    edx,ebx
  8522ef:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8522f2:	6a 00                	push   0x0
  8522f4:	56                   	push   esi
  8522f5:	89 4d f4             	mov    DWORD PTR [ebp-0xc],ecx
  8522f8:	ff d0                	call   eax
  8522fa:	8b 8b d0 00 00 00    	mov    ecx,DWORD PTR [ebx+0xd0]
  852300:	50                   	push   eax
  852301:	56                   	push   esi
  852302:	ff d1                	call   ecx
  852304:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  852307:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852309:	52                   	push   edx
  85230a:	68 14 c1 b1 00       	push   0xb1c114
  85230f:	8b c3                	mov    eax,ebx
  852311:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  852314:	6a 00                	push   0x0
  852316:	56                   	push   esi
  852317:	ff d1                	call   ecx
  852319:	8b 93 d0 00 00 00    	mov    edx,DWORD PTR [ebx+0xd0]
  85231f:	50                   	push   eax
  852320:	56                   	push   esi
  852321:	ff d2                	call   edx
  852323:	8b 87 94 00 00 00    	mov    eax,DWORD PTR [edi+0x94]
  852329:	8b 8c 87 88 00 00 00 	mov    ecx,DWORD PTR [edi+eax*4+0x88]
  852330:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852332:	51                   	push   ecx
  852333:	68 c4 bf b1 00       	push   0xb1bfc4
  852338:	8b d3                	mov    edx,ebx
  85233a:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85233d:	6a 00                	push   0x0
  85233f:	56                   	push   esi
  852340:	ff d0                	call   eax
  852342:	8b 8b d0 00 00 00    	mov    ecx,DWORD PTR [ebx+0xd0]
  852348:	50                   	push   eax
  852349:	56                   	push   esi
  85234a:	ff d1                	call   ecx
  85234c:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85234f:	8b 5d f8             	mov    ebx,DWORD PTR [ebp-0x8]
  852352:	8b 13                	mov    edx,DWORD PTR [ebx]
  852354:	8b 8a 94 00 00 00    	mov    ecx,DWORD PTR [edx+0x94]
  85235a:	50                   	push   eax
  85235b:	6a 00                	push   0x0
  85235d:	53                   	push   ebx
  85235e:	ff d1                	call   ecx
  852360:	8b 87 b0 00 00 00    	mov    eax,DWORD PTR [edi+0xb0]
  852366:	8b 13                	mov    edx,DWORD PTR [ebx]
  852368:	8b 8a 90 01 00 00    	mov    ecx,DWORD PTR [edx+0x190]
  85236e:	6a 14                	push   0x14
  852370:	6a 00                	push   0x0
  852372:	50                   	push   eax
  852373:	6a 00                	push   0x0
  852375:	53                   	push   ebx
  852376:	ff d1                	call   ecx
  852378:	85 c0                	test   eax,eax
  85237a:	7d 0e                	jge    0x85238a
  85237c:	e8 a1 12 0d 00       	call   0x923622
  852381:	5b                   	pop    ebx
  852382:	5f                   	pop    edi
  852383:	32 c0                	xor    al,al
  852385:	5e                   	pop    esi
  852386:	8b e5                	mov    esp,ebp
  852388:	5d                   	pop    ebp
  852389:	c3                   	ret
  85238a:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85238d:	8b 10                	mov    edx,DWORD PTR [eax]
  85238f:	8b 52 44             	mov    edx,DWORD PTR [edx+0x44]
  852392:	8d 4d b0             	lea    ecx,[ebp-0x50]
  852395:	51                   	push   ecx
  852396:	6a 00                	push   0x0
  852398:	50                   	push   eax
  852399:	ff d2                	call   edx
  85239b:	db 45 c8             	fild   DWORD PTR [ebp-0x38]
  85239e:	8b 45 c8             	mov    eax,DWORD PTR [ebp-0x38]
  8523a1:	85 c0                	test   eax,eax
  8523a3:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8523a5:	7d 06                	jge    0x8523ad
  8523a7:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8523ad:	51                   	push   ecx
  8523ae:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8523b0:	d9 1c 24             	fstp   DWORD PTR [esp]
  8523b3:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8523b6:	68 ec c1 b1 00       	push   0xb1c1ec
  8523bb:	6a 00                	push   0x0
  8523bd:	56                   	push   esi
  8523be:	ff d2                	call   edx
  8523c0:	50                   	push   eax
  8523c1:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  8523c4:	56                   	push   esi
  8523c5:	ff d0                	call   eax
  8523c7:	db 45 cc             	fild   DWORD PTR [ebp-0x34]
  8523ca:	8b 4d cc             	mov    ecx,DWORD PTR [ebp-0x34]
  8523cd:	85 c9                	test   ecx,ecx
  8523cf:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8523d1:	7d 06                	jge    0x8523d9
  8523d3:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  8523d9:	8b 16                	mov    edx,DWORD PTR [esi]
  8523db:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8523de:	51                   	push   ecx
  8523df:	d9 1c 24             	fstp   DWORD PTR [esp]
  8523e2:	68 d8 c1 b1 00       	push   0xb1c1d8
  8523e7:	6a 00                	push   0x0
  8523e9:	56                   	push   esi
  8523ea:	ff d0                	call   eax
  8523ec:	8b 4b 78             	mov    ecx,DWORD PTR [ebx+0x78]
  8523ef:	50                   	push   eax
  8523f0:	56                   	push   esi
  8523f1:	ff d1                	call   ecx
  8523f3:	db 45 c8             	fild   DWORD PTR [ebp-0x38]
  8523f6:	8b 55 c8             	mov    edx,DWORD PTR [ebp-0x38]
  8523f9:	85 d2                	test   edx,edx
  8523fb:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8523fd:	7d 06                	jge    0x852405
  8523ff:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  852405:	d9 e8                	fld1
  852407:	8b 06                	mov    eax,DWORD PTR [esi]
  852409:	de f1                	fdivrp st(1),st
  85240b:	51                   	push   ecx
  85240c:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  85240f:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  852412:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  852415:	d9 1c 24             	fstp   DWORD PTR [esp]
  852418:	68 c4 c1 b1 00       	push   0xb1c1c4
  85241d:	6a 00                	push   0x0
  85241f:	56                   	push   esi
  852420:	ff d1                	call   ecx
  852422:	8b 53 78             	mov    edx,DWORD PTR [ebx+0x78]
  852425:	50                   	push   eax
  852426:	56                   	push   esi
  852427:	ff d2                	call   edx
  852429:	db 45 cc             	fild   DWORD PTR [ebp-0x34]
  85242c:	8b 45 cc             	mov    eax,DWORD PTR [ebp-0x34]
  85242f:	85 c0                	test   eax,eax
  852431:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852433:	7d 06                	jge    0x85243b
  852435:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85243b:	d9 e8                	fld1
  85243d:	51                   	push   ecx
  85243e:	de f1                	fdivrp st(1),st
  852440:	8b 0e                	mov    ecx,DWORD PTR [esi]
  852442:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  852445:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  852448:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  85244b:	d9 1c 24             	fstp   DWORD PTR [esp]
  85244e:	68 ac c1 b1 00       	push   0xb1c1ac
  852453:	6a 00                	push   0x0
  852455:	56                   	push   esi
  852456:	ff d2                	call   edx
  852458:	50                   	push   eax
  852459:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85245c:	56                   	push   esi
  85245d:	ff d0                	call   eax
  85245f:	d9 47 18             	fld    DWORD PTR [edi+0x18]
  852462:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852464:	51                   	push   ecx
  852465:	d9 1c 24             	fstp   DWORD PTR [esp]
  852468:	68 f0 c0 b1 00       	push   0xb1c0f0
  85246d:	8b cb                	mov    ecx,ebx
  85246f:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  852472:	6a 00                	push   0x0
  852474:	56                   	push   esi
  852475:	ff d2                	call   edx
  852477:	50                   	push   eax
  852478:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85247b:	56                   	push   esi
  85247c:	ff d0                	call   eax
  85247e:	d9 47 24             	fld    DWORD PTR [edi+0x24]
  852481:	8b 1e                	mov    ebx,DWORD PTR [esi]
  852483:	51                   	push   ecx
  852484:	d9 1c 24             	fstp   DWORD PTR [esp]
  852487:	68 a0 c1 b1 00       	push   0xb1c1a0
  85248c:	8b cb                	mov    ecx,ebx
  85248e:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  852491:	6a 00                	push   0x0
  852493:	56                   	push   esi
  852494:	ff d2                	call   edx
  852496:	50                   	push   eax
  852497:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85249a:	56                   	push   esi
  85249b:	ff d0                	call   eax
  85249d:	d9 47 28             	fld    DWORD PTR [edi+0x28]
  8524a0:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8524a2:	51                   	push   ecx
  8524a3:	d9 1c 24             	fstp   DWORD PTR [esp]
  8524a6:	68 94 c1 b1 00       	push   0xb1c194
  8524ab:	8b cb                	mov    ecx,ebx
  8524ad:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8524b0:	6a 00                	push   0x0
  8524b2:	56                   	push   esi
  8524b3:	ff d2                	call   edx
  8524b5:	50                   	push   eax
  8524b6:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  8524b9:	56                   	push   esi
  8524ba:	ff d0                	call   eax
  8524bc:	d9 47 20             	fld    DWORD PTR [edi+0x20]
  8524bf:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8524c1:	51                   	push   ecx
  8524c2:	d9 1c 24             	fstp   DWORD PTR [esp]
  8524c5:	68 88 c1 b1 00       	push   0xb1c188
  8524ca:	8b cb                	mov    ecx,ebx
  8524cc:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8524cf:	6a 00                	push   0x0
  8524d1:	56                   	push   esi
  8524d2:	ff d2                	call   edx
  8524d4:	50                   	push   eax
  8524d5:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  8524d8:	56                   	push   esi
  8524d9:	ff d0                	call   eax
  8524db:	d9 47 1c             	fld    DWORD PTR [edi+0x1c]
  8524de:	8b 1e                	mov    ebx,DWORD PTR [esi]
  8524e0:	51                   	push   ecx
  8524e1:	d9 1c 24             	fstp   DWORD PTR [esp]
  8524e4:	68 80 c1 b1 00       	push   0xb1c180
  8524e9:	8b cb                	mov    ecx,ebx
  8524eb:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  8524ee:	6a 00                	push   0x0
  8524f0:	56                   	push   esi
  8524f1:	ff d2                	call   edx
  8524f3:	50                   	push   eax
  8524f4:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  8524f7:	56                   	push   esi
  8524f8:	ff d0                	call   eax
  8524fa:	8b 3e                	mov    edi,DWORD PTR [esi]
  8524fc:	8b cf                	mov    ecx,edi
  8524fe:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  852501:	68 70 c1 b1 00       	push   0xb1c170
  852506:	56                   	push   esi
  852507:	ff d2                	call   edx
  852509:	50                   	push   eax
  85250a:	8b 87 e8 00 00 00    	mov    eax,DWORD PTR [edi+0xe8]
  852510:	56                   	push   esi
  852511:	ff d0                	call   eax
  852513:	8b 0e                	mov    ecx,DWORD PTR [esi]
  852515:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85251b:	6a 01                	push   0x1
  85251d:	8d 55 f0             	lea    edx,[ebp-0x10]
  852520:	52                   	push   edx
  852521:	56                   	push   esi
  852522:	ff d0                	call   eax
  852524:	8b 0e                	mov    ecx,DWORD PTR [esi]
  852526:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85252c:	6a 00                	push   0x0
  85252e:	56                   	push   esi
  85252f:	ff d2                	call   edx
  852531:	8b 06                	mov    eax,DWORD PTR [esi]
  852533:	8b 88 04 01 00 00    	mov    ecx,DWORD PTR [eax+0x104]
  852539:	56                   	push   esi
  85253a:	ff d1                	call   ecx
  85253c:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85253f:	8b 10                	mov    edx,DWORD PTR [eax]
  852541:	6a 02                	push   0x2
  852543:	6a 00                	push   0x0
  852545:	6a 04                	push   0x4
  852547:	6a 00                	push   0x0
  852549:	6a 00                	push   0x0
  85254b:	6a 04                	push   0x4
  85254d:	50                   	push   eax
  85254e:	8b 82 48 01 00 00    	mov    eax,DWORD PTR [edx+0x148]
  852554:	ff d0                	call   eax
  852556:	8b 0e                	mov    ecx,DWORD PTR [esi]
  852558:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  85255e:	56                   	push   esi
  85255f:	ff d2                	call   edx
  852561:	8b 06                	mov    eax,DWORD PTR [esi]
  852563:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  852569:	56                   	push   esi
  85256a:	ff d1                	call   ecx
  85256c:	e8 b1 10 0d 00       	call   0x923622
  852571:	5b                   	pop    ebx
  852572:	5f                   	pop    edi
  852573:	b0 01                	mov    al,0x1
  852575:	5e                   	pop    esi
  852576:	8b e5                	mov    esp,ebp
  852578:	5d                   	pop    ebp
  852579:	c3                   	ret
```

### `0x0085c370..0x0085cacf` — sites `0x0085c8b1`, `0x0085ca3b`

```asm
  85c370:	55                   	push   ebp
  85c371:	8b ec                	mov    ebp,esp
  85c373:	56                   	push   esi
  85c374:	8b f1                	mov    esi,ecx
  85c376:	8b 06                	mov    eax,DWORD PTR [esi]
  85c378:	57                   	push   edi
  85c379:	8b fa                	mov    edi,edx
  85c37b:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  85c37e:	ff d2                	call   edx
  85c380:	84 c0                	test   al,al
  85c382:	74 56                	je     0x85c3da
  85c384:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  85c387:	53                   	push   ebx
  85c388:	6a 01                	push   0x1
  85c38a:	50                   	push   eax
  85c38b:	8b d7                	mov    edx,edi
  85c38d:	8b ce                	mov    ecx,esi
  85c38f:	e8 7c 88 00 00       	call   0x864c10
  85c394:	8b 3d 58 60 c2 00    	mov    edi,DWORD PTR ds:0xc26058
  85c39a:	8b 07                	mov    eax,DWORD PTR [edi]
  85c39c:	8b 80 b0 00 00 00    	mov    eax,DWORD PTR [eax+0xb0]
  85c3a2:	33 d2                	xor    edx,edx
  85c3a4:	8b cf                	mov    ecx,edi
  85c3a6:	ff d0                	call   eax
  85c3a8:	8b 8e 94 09 00 00    	mov    ecx,DWORD PTR [esi+0x994]
  85c3ae:	89 86 98 09 00 00    	mov    DWORD PTR [esi+0x998],eax
  85c3b4:	8b 86 90 09 00 00    	mov    eax,DWORD PTR [esi+0x990]
  85c3ba:	51                   	push   ecx
  85c3bb:	50                   	push   eax
  85c3bc:	89 96 9c 09 00 00    	mov    DWORD PTR [esi+0x99c],edx
  85c3c2:	8b 1f                	mov    ebx,DWORD PTR [edi]
  85c3c4:	51                   	push   ecx
  85c3c5:	50                   	push   eax
  85c3c6:	8b 83 b4 00 00 00    	mov    eax,DWORD PTR [ebx+0xb4]
  85c3cc:	33 d2                	xor    edx,edx
  85c3ce:	8b cf                	mov    ecx,edi
  85c3d0:	ff d0                	call   eax
  85c3d2:	c6 86 2e 03 00 00 01 	mov    BYTE PTR [esi+0x32e],0x1
  85c3d9:	5b                   	pop    ebx
  85c3da:	5f                   	pop    edi
  85c3db:	5e                   	pop    esi
  85c3dc:	5d                   	pop    ebp
  85c3dd:	c2 08 00             	ret    0x8
  85c3e0:	55                   	push   ebp
  85c3e1:	8b ec                	mov    ebp,esp
  85c3e3:	81 ec b4 00 00 00    	sub    esp,0xb4
  85c3e9:	53                   	push   ebx
  85c3ea:	56                   	push   esi
  85c3eb:	8b f1                	mov    esi,ecx
  85c3ed:	57                   	push   edi
  85c3ee:	b9 c0 d7 b1 00       	mov    ecx,0xb1d7c0
  85c3f3:	e8 f8 a6 de ff       	call   0x646af0
  85c3f8:	d9 ee                	fldz
  85c3fa:	8b 3d 58 60 c2 00    	mov    edi,DWORD PTR ds:0xc26058
  85c400:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  85c403:	84 c0                	test   al,al
  85c405:	8b cf                	mov    ecx,edi
  85c407:	0f 95 c3             	setne  bl
  85c40a:	e8 01 1d fd ff       	call   0x82e110
  85c40f:	8b 55 f4             	mov    edx,DWORD PTR [ebp-0xc]
  85c412:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c414:	52                   	push   edx
  85c415:	68 af 00 00 00       	push   0xaf
  85c41a:	50                   	push   eax
  85c41b:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  85c421:	ff d0                	call   eax
  85c423:	8b cf                	mov    ecx,edi
  85c425:	e8 e6 1c fd ff       	call   0x82e110
  85c42a:	8b 55 f4             	mov    edx,DWORD PTR [ebp-0xc]
  85c42d:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c42f:	52                   	push   edx
  85c430:	68 c3 00 00 00       	push   0xc3
  85c435:	50                   	push   eax
  85c436:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  85c43c:	ff d0                	call   eax
  85c43e:	8b 96 9c 09 00 00    	mov    edx,DWORD PTR [esi+0x99c]
  85c444:	8b 86 98 09 00 00    	mov    eax,DWORD PTR [esi+0x998]
  85c44a:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85c450:	8b 09                	mov    ecx,DWORD PTR [ecx]
  85c452:	52                   	push   edx
  85c453:	50                   	push   eax
  85c454:	52                   	push   edx
  85c455:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  85c458:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85c45e:	50                   	push   eax
  85c45f:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85c462:	8b 80 b4 00 00 00    	mov    eax,DWORD PTR [eax+0xb4]
  85c468:	33 d2                	xor    edx,edx
  85c46a:	ff d0                	call   eax
  85c46c:	84 db                	test   bl,bl
  85c46e:	c6 86 2e 03 00 00 00 	mov    BYTE PTR [esi+0x32e],0x0
  85c475:	0f 84 4d 06 00 00    	je     0x85cac8
  85c47b:	8b cf                	mov    ecx,edi
  85c47d:	e8 8e 1c fd ff       	call   0x82e110
  85c482:	8b 96 f8 09 00 00    	mov    edx,DWORD PTR [esi+0x9f8]
  85c488:	8b d8                	mov    ebx,eax
  85c48a:	8b cf                	mov    ecx,edi
  85c48c:	89 5d f0             	mov    DWORD PTR [ebp-0x10],ebx
  85c48f:	e8 7c 20 fd ff       	call   0x82e510
  85c494:	8b 96 fc 09 00 00    	mov    edx,DWORD PTR [esi+0x9fc]
  85c49a:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  85c49c:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  85c4a2:	6a 14                	push   0x14
  85c4a4:	6a 00                	push   0x0
  85c4a6:	52                   	push   edx
  85c4a7:	6a 00                	push   0x0
  85c4a9:	53                   	push   ebx
  85c4aa:	ff d0                	call   eax
  85c4ac:	8b 96 00 0a 00 00    	mov    edx,DWORD PTR [esi+0xa00]
  85c4b2:	8b 0b                	mov    ecx,DWORD PTR [ebx]
  85c4b4:	8b 81 a0 01 00 00    	mov    eax,DWORD PTR [ecx+0x1a0]
  85c4ba:	52                   	push   edx
  85c4bb:	53                   	push   ebx
  85c4bc:	ff d0                	call   eax
  85c4be:	8b 8e f4 09 00 00    	mov    ecx,DWORD PTR [esi+0x9f4]
  85c4c4:	8b c1                	mov    eax,ecx
  85c4c6:	8b 8e c4 09 00 00    	mov    ecx,DWORD PTR [esi+0x9c4]
  85c4cc:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c4ce:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c4d1:	e8 1a c9 fd ff       	call   0x838df0
  85c4d6:	50                   	push   eax
  85c4d7:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c4da:	8b 10                	mov    edx,DWORD PTR [eax]
  85c4dc:	68 b4 d7 b1 00       	push   0xb1d7b4
  85c4e1:	6a 00                	push   0x0
  85c4e3:	50                   	push   eax
  85c4e4:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85c4e7:	ff d0                	call   eax
  85c4e9:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85c4ec:	8b 93 d0 00 00 00    	mov    edx,DWORD PTR [ebx+0xd0]
  85c4f2:	50                   	push   eax
  85c4f3:	51                   	push   ecx
  85c4f4:	ff d2                	call   edx
  85c4f6:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c4fc:	8b 8e 08 0a 00 00    	mov    ecx,DWORD PTR [esi+0xa08]
  85c502:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c504:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c507:	e8 e4 c8 fd ff       	call   0x838df0
  85c50c:	50                   	push   eax
  85c50d:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c510:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c512:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85c515:	68 a8 d7 b1 00       	push   0xb1d7a8
  85c51a:	6a 00                	push   0x0
  85c51c:	50                   	push   eax
  85c51d:	ff d2                	call   edx
  85c51f:	8b 8b d0 00 00 00    	mov    ecx,DWORD PTR [ebx+0xd0]
  85c525:	50                   	push   eax
  85c526:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c529:	50                   	push   eax
  85c52a:	ff d1                	call   ecx
  85c52c:	e8 1f fb fc ff       	call   0x82c050
  85c531:	8b c8                	mov    ecx,eax
  85c533:	e8 28 e1 fc ff       	call   0x82a660
  85c538:	e8 73 fb fc ff       	call   0x82c0b0
  85c53d:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  85c540:	8b 10                	mov    edx,DWORD PTR [eax]
  85c542:	6a 00                	push   0x0
  85c544:	68 c2 00 00 00       	push   0xc2
  85c549:	50                   	push   eax
  85c54a:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  85c550:	ff d0                	call   eax
  85c552:	33 d2                	xor    edx,edx
  85c554:	38 96 04 05 00 00    	cmp    BYTE PTR [esi+0x504],dl
  85c55a:	89 55 f4             	mov    DWORD PTR [ebp-0xc],edx
  85c55d:	0f 86 36 05 00 00    	jbe    0x85ca99
  85c563:	d9 e8                	fld1
  85c565:	d9 ee                	fldz
  85c567:	8b 86 20 03 00 00    	mov    eax,DWORD PTR [esi+0x320]
  85c56d:	d9 ee                	fldz
  85c56f:	8b c8                	mov    ecx,eax
  85c571:	c1 e1 05             	shl    ecx,0x5
  85c574:	2b c8                	sub    ecx,eax
  85c576:	03 ca                	add    ecx,edx
  85c578:	d8 9c 8e 6c 01 00 00 	fcomp  DWORD PTR [esi+ecx*4+0x16c]
  85c57f:	8d 8c 8e 6c 01 00 00 	lea    ecx,[esi+ecx*4+0x16c]
  85c586:	df e0                	fnstsw ax
  85c588:	f6 c4 01             	test   ah,0x1
  85c58b:	0f 84 ef 04 00 00    	je     0x85ca80
  85c591:	8b 96 24 03 00 00    	mov    edx,DWORD PTR [esi+0x324]
  85c597:	db 86 24 03 00 00    	fild   DWORD PTR [esi+0x324]
  85c59d:	85 d2                	test   edx,edx
  85c59f:	7d 06                	jge    0x85c5a7
  85c5a1:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c5a7:	d8 fa                	fdivr  st,st(2)
  85c5a9:	8b 86 28 03 00 00    	mov    eax,DWORD PTR [esi+0x328]
  85c5af:	85 c0                	test   eax,eax
  85c5b1:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  85c5b4:	db 86 28 03 00 00    	fild   DWORD PTR [esi+0x328]
  85c5ba:	7d 06                	jge    0x85c5c2
  85c5bc:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c5c2:	de fa                	fdivp  st(2),st
  85c5c4:	d9 c9                	fxch   st(1)
  85c5c6:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  85c5c9:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85c5cc:	dd 05 a0 42 ab 00    	fld    QWORD PTR ds:0xab42a0
  85c5d2:	d8 c9                	fmul   st,st(1)
  85c5d4:	d9 9d 4c ff ff ff    	fstp   DWORD PTR [ebp-0xb4]
  85c5da:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85c5dd:	d9 c0                	fld    st(0)
  85c5df:	d8 cb                	fmul   st,st(3)
  85c5e1:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  85c5e4:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85c5e7:	d9 95 50 ff ff ff    	fst    DWORD PTR [ebp-0xb0]
  85c5ed:	d9 c2                	fld    st(2)
  85c5ef:	dc 0d f8 68 ab 00    	fmul   QWORD PTR ds:0xab68f8
  85c5f5:	d9 9d 5c ff ff ff    	fstp   DWORD PTR [ebp-0xa4]
  85c5fb:	d9 95 60 ff ff ff    	fst    DWORD PTR [ebp-0xa0]
  85c601:	d9 c2                	fld    st(2)
  85c603:	de cc                	fmulp  st(4),st
  85c605:	d9 cb                	fxch   st(3)
  85c607:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  85c60a:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85c60d:	d9 95 6c ff ff ff    	fst    DWORD PTR [ebp-0x94]
  85c613:	d9 cb                	fxch   st(3)
  85c615:	d9 95 70 ff ff ff    	fst    DWORD PTR [ebp-0x90]
  85c61b:	d9 55 80             	fst    DWORD PTR [ebp-0x80]
  85c61e:	d9 ca                	fxch   st(2)
  85c620:	d9 95 7c ff ff ff    	fst    DWORD PTR [ebp-0x84]
  85c626:	d9 c0                	fld    st(0)
  85c628:	d8 c1                	fadd   st,st(1)
  85c62a:	d9 5d 8c             	fstp   DWORD PTR [ebp-0x74]
  85c62d:	d9 ca                	fxch   st(2)
  85c62f:	d9 5d 90             	fstp   DWORD PTR [ebp-0x70]
  85c632:	d9 ca                	fxch   st(2)
  85c634:	d9 55 9c             	fst    DWORD PTR [ebp-0x64]
  85c637:	d9 c2                	fld    st(2)
  85c639:	dc 0d 00 3e b0 00    	fmul   QWORD PTR ds:0xb03e00
  85c63f:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  85c642:	d9 55 ac             	fst    DWORD PTR [ebp-0x54]
  85c645:	d9 c2                	fld    st(2)
  85c647:	dc 0d 18 9a aa 00    	fmul   QWORD PTR ds:0xaa9a18
  85c64d:	d9 5d b0             	fstp   DWORD PTR [ebp-0x50]
  85c650:	d9 55 bc             	fst    DWORD PTR [ebp-0x44]
  85c653:	d9 c2                	fld    st(2)
  85c655:	dc 0d 20 9a aa 00    	fmul   QWORD PTR ds:0xaa9a20
  85c65b:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  85c65e:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  85c661:	d9 c9                	fxch   st(1)
  85c663:	dc 0d 18 4d ab 00    	fmul   QWORD PTR ds:0xab4d18
  85c669:	d9 5d d0             	fstp   DWORD PTR [ebp-0x30]
  85c66c:	d9 85 4c ff ff ff    	fld    DWORD PTR [ebp-0xb4]
  85c672:	d8 09                	fmul   DWORD PTR [ecx]
  85c674:	d9 9d 4c ff ff ff    	fstp   DWORD PTR [ebp-0xb4]
  85c67a:	d9 85 50 ff ff ff    	fld    DWORD PTR [ebp-0xb0]
  85c680:	d8 09                	fmul   DWORD PTR [ecx]
  85c682:	d9 9d 50 ff ff ff    	fstp   DWORD PTR [ebp-0xb0]
  85c688:	d9 85 5c ff ff ff    	fld    DWORD PTR [ebp-0xa4]
  85c68e:	d8 09                	fmul   DWORD PTR [ecx]
  85c690:	d9 9d 5c ff ff ff    	fstp   DWORD PTR [ebp-0xa4]
  85c696:	d9 85 60 ff ff ff    	fld    DWORD PTR [ebp-0xa0]
  85c69c:	d8 09                	fmul   DWORD PTR [ecx]
  85c69e:	d9 9d 60 ff ff ff    	fstp   DWORD PTR [ebp-0xa0]
  85c6a4:	d9 85 6c ff ff ff    	fld    DWORD PTR [ebp-0x94]
  85c6aa:	d8 09                	fmul   DWORD PTR [ecx]
  85c6ac:	d9 9d 6c ff ff ff    	fstp   DWORD PTR [ebp-0x94]
  85c6b2:	d9 85 70 ff ff ff    	fld    DWORD PTR [ebp-0x90]
  85c6b8:	d8 09                	fmul   DWORD PTR [ecx]
  85c6ba:	d9 9d 70 ff ff ff    	fstp   DWORD PTR [ebp-0x90]
  85c6c0:	d8 09                	fmul   DWORD PTR [ecx]
  85c6c2:	d9 9d 7c ff ff ff    	fstp   DWORD PTR [ebp-0x84]
  85c6c8:	d9 45 80             	fld    DWORD PTR [ebp-0x80]
  85c6cb:	d8 09                	fmul   DWORD PTR [ecx]
  85c6cd:	d9 5d 80             	fstp   DWORD PTR [ebp-0x80]
  85c6d0:	d9 45 8c             	fld    DWORD PTR [ebp-0x74]
  85c6d3:	d8 09                	fmul   DWORD PTR [ecx]
  85c6d5:	d9 5d 8c             	fstp   DWORD PTR [ebp-0x74]
  85c6d8:	d9 45 90             	fld    DWORD PTR [ebp-0x70]
  85c6db:	d8 09                	fmul   DWORD PTR [ecx]
  85c6dd:	d9 5d 90             	fstp   DWORD PTR [ebp-0x70]
  85c6e0:	d9 45 9c             	fld    DWORD PTR [ebp-0x64]
  85c6e3:	d8 09                	fmul   DWORD PTR [ecx]
  85c6e5:	d9 5d 9c             	fstp   DWORD PTR [ebp-0x64]
  85c6e8:	6a 09                	push   0x9
  85c6ea:	d9 45 a0             	fld    DWORD PTR [ebp-0x60]
  85c6ed:	8d 95 4c ff ff ff    	lea    edx,[ebp-0xb4]
  85c6f3:	d8 09                	fmul   DWORD PTR [ecx]
  85c6f5:	52                   	push   edx
  85c6f6:	68 a0 d7 b1 00       	push   0xb1d7a0
  85c6fb:	6a 00                	push   0x0
  85c6fd:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  85c700:	d9 45 ac             	fld    DWORD PTR [ebp-0x54]
  85c703:	d8 09                	fmul   DWORD PTR [ecx]
  85c705:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  85c708:	d9 45 b0             	fld    DWORD PTR [ebp-0x50]
  85c70b:	d8 09                	fmul   DWORD PTR [ecx]
  85c70d:	d9 5d b0             	fstp   DWORD PTR [ebp-0x50]
  85c710:	d9 45 bc             	fld    DWORD PTR [ebp-0x44]
  85c713:	d8 09                	fmul   DWORD PTR [ecx]
  85c715:	d9 5d bc             	fstp   DWORD PTR [ebp-0x44]
  85c718:	d9 45 c0             	fld    DWORD PTR [ebp-0x40]
  85c71b:	d8 09                	fmul   DWORD PTR [ecx]
  85c71d:	d9 5d c0             	fstp   DWORD PTR [ebp-0x40]
  85c720:	d9 45 cc             	fld    DWORD PTR [ebp-0x34]
  85c723:	d8 09                	fmul   DWORD PTR [ecx]
  85c725:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  85c728:	d9 45 d0             	fld    DWORD PTR [ebp-0x30]
  85c72b:	d8 09                	fmul   DWORD PTR [ecx]
  85c72d:	8b 8e f4 09 00 00    	mov    ecx,DWORD PTR [esi+0x9f4]
  85c733:	8b c1                	mov    eax,ecx
  85c735:	50                   	push   eax
  85c736:	d9 5d d0             	fstp   DWORD PTR [ebp-0x30]
  85c739:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c73b:	8b cb                	mov    ecx,ebx
  85c73d:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85c740:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c743:	ff d2                	call   edx
  85c745:	8b 8b 90 00 00 00    	mov    ecx,DWORD PTR [ebx+0x90]
  85c74b:	50                   	push   eax
  85c74c:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c74f:	50                   	push   eax
  85c750:	ff d1                	call   ecx
  85c752:	8b 07                	mov    eax,DWORD PTR [edi]
  85c754:	8b 96 04 0a 00 00    	mov    edx,DWORD PTR [esi+0xa04]
  85c75a:	8b 80 38 01 00 00    	mov    eax,DWORD PTR [eax+0x138]
  85c760:	6a 00                	push   0x0
  85c762:	6a 00                	push   0x0
  85c764:	6a 00                	push   0x0
  85c766:	6a 00                	push   0x0
  85c768:	6a 00                	push   0x0
  85c76a:	8b cf                	mov    ecx,edi
  85c76c:	ff d0                	call   eax
  85c76e:	d9 ee                	fldz
  85c770:	8b 8e 24 03 00 00    	mov    ecx,DWORD PTR [esi+0x324]
  85c776:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  85c779:	85 c9                	test   ecx,ecx
  85c77b:	d9 e8                	fld1
  85c77d:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  85c780:	db 86 24 03 00 00    	fild   DWORD PTR [esi+0x324]
  85c786:	7d 06                	jge    0x85c78e
  85c788:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c78e:	d9 e8                	fld1
  85c790:	8b 96 28 03 00 00    	mov    edx,DWORD PTR [esi+0x328]
  85c796:	85 d2                	test   edx,edx
  85c798:	de f1                	fdivrp st(1),st
  85c79a:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  85c79d:	db 86 28 03 00 00    	fild   DWORD PTR [esi+0x328]
  85c7a3:	7d 06                	jge    0x85c7ab
  85c7a5:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c7ab:	dc 3d f8 68 ab 00    	fdivr  QWORD PTR ds:0xab68f8
  85c7b1:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c7b7:	8d 4d e0             	lea    ecx,[ebp-0x20]
  85c7ba:	51                   	push   ecx
  85c7bb:	68 88 d7 b1 00       	push   0xb1d788
  85c7c0:	6a 00                	push   0x0
  85c7c2:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c7c5:	50                   	push   eax
  85c7c6:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  85c7c9:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c7cb:	8b d3                	mov    edx,ebx
  85c7cd:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85c7d0:	ff d0                	call   eax
  85c7d2:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85c7d5:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  85c7db:	50                   	push   eax
  85c7dc:	51                   	push   ecx
  85c7dd:	ff d2                	call   edx
  85c7df:	db 45 f4             	fild   DWORD PTR [ebp-0xc]
  85c7e2:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85c7e5:	85 c0                	test   eax,eax
  85c7e7:	7d 06                	jge    0x85c7ef
  85c7e9:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c7ef:	0f b6 8e 04 05 00 00 	movzx  ecx,BYTE PTR [esi+0x504]
  85c7f6:	d9 5d f8             	fstp   DWORD PTR [ebp-0x8]
  85c7f9:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85c7fc:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c802:	8d 55 e0             	lea    edx,[ebp-0x20]
  85c805:	db 45 fc             	fild   DWORD PTR [ebp-0x4]
  85c808:	52                   	push   edx
  85c809:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85c80c:	68 70 d7 b1 00       	push   0xb1d770
  85c811:	6a 00                	push   0x0
  85c813:	d8 f1                	fdiv   st,st(1)
  85c815:	50                   	push   eax
  85c816:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c819:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  85c81c:	d9 e8                	fld1
  85c81e:	de f1                	fdivrp st(1),st
  85c820:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  85c823:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c825:	8b cb                	mov    ecx,ebx
  85c827:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85c82a:	ff d2                	call   edx
  85c82c:	8b 8b 88 00 00 00    	mov    ecx,DWORD PTR [ebx+0x88]
  85c832:	50                   	push   eax
  85c833:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c836:	50                   	push   eax
  85c837:	ff d1                	call   ecx
  85c839:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c83f:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c841:	68 64 d7 b1 00       	push   0xb1d764
  85c846:	8b d3                	mov    edx,ebx
  85c848:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c84b:	50                   	push   eax
  85c84c:	8b 42 34             	mov    eax,DWORD PTR [edx+0x34]
  85c84f:	ff d0                	call   eax
  85c851:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85c854:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  85c85a:	50                   	push   eax
  85c85b:	51                   	push   ecx
  85c85c:	ff d2                	call   edx
  85c85e:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c864:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c866:	6a 01                	push   0x1
  85c868:	8d 55 dc             	lea    edx,[ebp-0x24]
  85c86b:	52                   	push   edx
  85c86c:	50                   	push   eax
  85c86d:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85c873:	ff d0                	call   eax
  85c875:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c87b:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c87d:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85c883:	6a 00                	push   0x0
  85c885:	50                   	push   eax
  85c886:	ff d2                	call   edx
  85c888:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c88e:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c890:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85c896:	50                   	push   eax
  85c897:	ff d2                	call   edx
  85c899:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  85c89c:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c89e:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  85c8a4:	6a 02                	push   0x2
  85c8a6:	6a 00                	push   0x0
  85c8a8:	6a 04                	push   0x4
  85c8aa:	6a 00                	push   0x0
  85c8ac:	6a 00                	push   0x0
  85c8ae:	6a 05                	push   0x5
  85c8b0:	50                   	push   eax
  85c8b1:	ff d2                	call   edx
  85c8b3:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c8b9:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c8bb:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  85c8c1:	50                   	push   eax
  85c8c2:	ff d2                	call   edx
  85c8c4:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c8ca:	8b 08                	mov    ecx,DWORD PTR [eax]
  85c8cc:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85c8d2:	50                   	push   eax
  85c8d3:	ff d2                	call   edx
  85c8d5:	8b 07                	mov    eax,DWORD PTR [edi]
  85c8d7:	6a 00                	push   0x0
  85c8d9:	8b 96 04 0a 00 00    	mov    edx,DWORD PTR [esi+0xa04]
  85c8df:	8b 80 3c 01 00 00    	mov    eax,DWORD PTR [eax+0x13c]
  85c8e5:	6a 00                	push   0x0
  85c8e7:	6a ff                	push   0xffffffff
  85c8e9:	8b cf                	mov    ecx,edi
  85c8eb:	ff d0                	call   eax
  85c8ed:	8b 07                	mov    eax,DWORD PTR [edi]
  85c8ef:	8b 96 b4 09 00 00    	mov    edx,DWORD PTR [esi+0x9b4]
  85c8f5:	8b 80 38 01 00 00    	mov    eax,DWORD PTR [eax+0x138]
  85c8fb:	6a 00                	push   0x0
  85c8fd:	6a 00                	push   0x0
  85c8ff:	6a 00                	push   0x0
  85c901:	6a 00                	push   0x0
  85c903:	6a 00                	push   0x0
  85c905:	8b cf                	mov    ecx,edi
  85c907:	ff d0                	call   eax
  85c909:	0f b6 8e 04 05 00 00 	movzx  ecx,BYTE PTR [esi+0x504]
  85c910:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85c913:	8b 96 24 03 00 00    	mov    edx,DWORD PTR [esi+0x324]
  85c919:	85 d2                	test   edx,edx
  85c91b:	db 45 fc             	fild   DWORD PTR [ebp-0x4]
  85c91e:	d9 45 f8             	fld    DWORD PTR [ebp-0x8]
  85c921:	d8 f1                	fdiv   st,st(1)
  85c923:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  85c926:	d9 e8                	fld1
  85c928:	d9 c0                	fld    st(0)
  85c92a:	d8 f2                	fdiv   st,st(2)
  85c92c:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  85c92f:	db 86 24 03 00 00    	fild   DWORD PTR [esi+0x324]
  85c935:	7d 06                	jge    0x85c93d
  85c937:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c93d:	de f9                	fdivp  st(1),st
  85c93f:	8b 86 28 03 00 00    	mov    eax,DWORD PTR [esi+0x328]
  85c945:	85 c0                	test   eax,eax
  85c947:	d9 5d e8             	fstp   DWORD PTR [ebp-0x18]
  85c94a:	db 86 28 03 00 00    	fild   DWORD PTR [esi+0x328]
  85c950:	7d 06                	jge    0x85c958
  85c952:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85c958:	de c9                	fmulp  st(1),st
  85c95a:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c960:	8d 4d e0             	lea    ecx,[ebp-0x20]
  85c963:	51                   	push   ecx
  85c964:	dc 3d f8 68 ab 00    	fdivr  QWORD PTR ds:0xab68f8
  85c96a:	68 88 d7 b1 00       	push   0xb1d788
  85c96f:	6a 00                	push   0x0
  85c971:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c974:	50                   	push   eax
  85c975:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  85c978:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c97a:	8b d3                	mov    edx,ebx
  85c97c:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85c97f:	ff d0                	call   eax
  85c981:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85c984:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  85c98a:	50                   	push   eax
  85c98b:	51                   	push   ecx
  85c98c:	ff d2                	call   edx
  85c98e:	d9 ee                	fldz
  85c990:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c996:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  85c999:	d9 e8                	fld1
  85c99b:	8d 4d e0             	lea    ecx,[ebp-0x20]
  85c99e:	51                   	push   ecx
  85c99f:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  85c9a2:	68 70 d7 b1 00       	push   0xb1d770
  85c9a7:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c9a9:	6a 00                	push   0x0
  85c9ab:	8b d3                	mov    edx,ebx
  85c9ad:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c9b0:	50                   	push   eax
  85c9b1:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85c9b4:	ff d0                	call   eax
  85c9b6:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85c9b9:	8b 93 88 00 00 00    	mov    edx,DWORD PTR [ebx+0x88]
  85c9bf:	50                   	push   eax
  85c9c0:	51                   	push   ecx
  85c9c1:	ff d2                	call   edx
  85c9c3:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c9c9:	8b 18                	mov    ebx,DWORD PTR [eax]
  85c9cb:	8b cb                	mov    ecx,ebx
  85c9cd:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  85c9d0:	68 58 d7 b1 00       	push   0xb1d758
  85c9d5:	50                   	push   eax
  85c9d6:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85c9d9:	ff d2                	call   edx
  85c9db:	8b 8b e8 00 00 00    	mov    ecx,DWORD PTR [ebx+0xe8]
  85c9e1:	50                   	push   eax
  85c9e2:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85c9e5:	50                   	push   eax
  85c9e6:	ff d1                	call   ecx
  85c9e8:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85c9ee:	8b 10                	mov    edx,DWORD PTR [eax]
  85c9f0:	8b 92 fc 00 00 00    	mov    edx,DWORD PTR [edx+0xfc]
  85c9f6:	6a 01                	push   0x1
  85c9f8:	8d 4d dc             	lea    ecx,[ebp-0x24]
  85c9fb:	51                   	push   ecx
  85c9fc:	50                   	push   eax
  85c9fd:	ff d2                	call   edx
  85c9ff:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85ca05:	8b 08                	mov    ecx,DWORD PTR [eax]
  85ca07:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85ca0d:	6a 00                	push   0x0
  85ca0f:	50                   	push   eax
  85ca10:	ff d2                	call   edx
  85ca12:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85ca18:	8b 08                	mov    ecx,DWORD PTR [eax]
  85ca1a:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85ca20:	50                   	push   eax
  85ca21:	ff d2                	call   edx
  85ca23:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  85ca26:	8b 08                	mov    ecx,DWORD PTR [eax]
  85ca28:	8b 91 48 01 00 00    	mov    edx,DWORD PTR [ecx+0x148]
  85ca2e:	6a 02                	push   0x2
  85ca30:	6a 00                	push   0x0
  85ca32:	6a 04                	push   0x4
  85ca34:	6a 00                	push   0x0
  85ca36:	6a 00                	push   0x0
  85ca38:	6a 05                	push   0x5
  85ca3a:	50                   	push   eax
  85ca3b:	ff d2                	call   edx
  85ca3d:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85ca43:	8b 08                	mov    ecx,DWORD PTR [eax]
  85ca45:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  85ca4b:	50                   	push   eax
  85ca4c:	ff d2                	call   edx
  85ca4e:	8b 86 f4 09 00 00    	mov    eax,DWORD PTR [esi+0x9f4]
  85ca54:	8b 08                	mov    ecx,DWORD PTR [eax]
  85ca56:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85ca5c:	50                   	push   eax
  85ca5d:	ff d2                	call   edx
  85ca5f:	8b 07                	mov    eax,DWORD PTR [edi]
  85ca61:	8b 96 b4 09 00 00    	mov    edx,DWORD PTR [esi+0x9b4]
  85ca67:	8b 80 3c 01 00 00    	mov    eax,DWORD PTR [eax+0x13c]
  85ca6d:	6a 00                	push   0x0
  85ca6f:	6a 00                	push   0x0
  85ca71:	6a ff                	push   0xffffffff
  85ca73:	8b cf                	mov    ecx,edi
  85ca75:	ff d0                	call   eax
  85ca77:	d9 ee                	fldz
  85ca79:	d9 e8                	fld1
  85ca7b:	8b 55 f4             	mov    edx,DWORD PTR [ebp-0xc]
  85ca7e:	d9 c9                	fxch   st(1)
  85ca80:	0f b6 8e 04 05 00 00 	movzx  ecx,BYTE PTR [esi+0x504]
  85ca87:	83 c2 01             	add    edx,0x1
  85ca8a:	3b d1                	cmp    edx,ecx
  85ca8c:	89 55 f4             	mov    DWORD PTR [ebp-0xc],edx
  85ca8f:	0f 82 d2 fa ff ff    	jb     0x85c567
  85ca95:	dd d9                	fstp   st(1)
  85ca97:	dd d8                	fstp   st(0)
  85ca99:	e8 72 d5 de ff       	call   0x64a010
  85ca9e:	ba 09 00 00 00       	mov    edx,0x9
  85caa3:	8b c8                	mov    ecx,eax
  85caa5:	e8 76 d4 de ff       	call   0x649f20
  85caaa:	84 c0                	test   al,al
  85caac:	74 1a                	je     0x85cac8
  85caae:	8b 8e c4 09 00 00    	mov    ecx,DWORD PTR [esi+0x9c4]
  85cab4:	6a 00                	push   0x0
  85cab6:	e8 35 c3 fd ff       	call   0x838df0
  85cabb:	50                   	push   eax
  85cabc:	6a 04                	push   0x4
  85cabe:	68 48 d7 b1 00       	push   0xb1d748
  85cac3:	e8 1a 6c 0c 00       	call   0x9236e2
  85cac8:	5f                   	pop    edi
  85cac9:	5e                   	pop    esi
  85caca:	5b                   	pop    ebx
  85cacb:	8b e5                	mov    esp,ebp
  85cacd:	5d                   	pop    ebp
  85cace:	c3                   	ret
```

### `0x0085e040..0x0085e6d3` — sites `0x0085e49f`, `0x0085e5bd`

```asm
  85e040:	53                   	push   ebx
  85e041:	8b dc                	mov    ebx,esp
  85e043:	83 ec 08             	sub    esp,0x8
  85e046:	83 e4 f0             	and    esp,0xfffffff0
  85e049:	83 c4 04             	add    esp,0x4
  85e04c:	55                   	push   ebp
  85e04d:	8b 6b 04             	mov    ebp,DWORD PTR [ebx+0x4]
  85e050:	89 6c 24 04          	mov    DWORD PTR [esp+0x4],ebp
  85e054:	8b ec                	mov    ebp,esp
  85e056:	81 ec 08 01 00 00    	sub    esp,0x108
  85e05c:	56                   	push   esi
  85e05d:	8b f1                	mov    esi,ecx
  85e05f:	80 7e 1c 00          	cmp    BYTE PTR [esi+0x1c],0x0
  85e063:	57                   	push   edi
  85e064:	89 55 e8             	mov    DWORD PTR [ebp-0x18],edx
  85e067:	89 75 d4             	mov    DWORD PTR [ebp-0x2c],esi
  85e06a:	0f 84 f7 00 00 00    	je     0x85e167
  85e070:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e076:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e078:	8b 90 14 01 00 00    	mov    edx,DWORD PTR [eax+0x114]
  85e07e:	ff d2                	call   edx
  85e080:	8b c8                	mov    ecx,eax
  85e082:	89 45 f4             	mov    DWORD PTR [ebp-0xc],eax
  85e085:	e8 86 0e 00 00       	call   0x85ef10
  85e08a:	85 c0                	test   eax,eax
  85e08c:	89 45 fc             	mov    DWORD PTR [ebp-0x4],eax
  85e08f:	0f 84 d2 00 00 00    	je     0x85e167
  85e095:	83 7e 24 00          	cmp    DWORD PTR [esi+0x24],0x0
  85e099:	0f 85 d3 00 00 00    	jne    0x85e172
  85e09f:	83 7e 2c 00          	cmp    DWORD PTR [esi+0x2c],0x0
  85e0a3:	0f 84 be 00 00 00    	je     0x85e167
  85e0a9:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e0af:	e8 5c 00 fd ff       	call   0x82e110
  85e0b4:	8d 4d f4             	lea    ecx,[ebp-0xc]
  85e0b7:	8b f8                	mov    edi,eax
  85e0b9:	8b 07                	mov    eax,DWORD PTR [edi]
  85e0bb:	8b 90 98 00 00 00    	mov    edx,DWORD PTR [eax+0x98]
  85e0c1:	51                   	push   ecx
  85e0c2:	6a 00                	push   0x0
  85e0c4:	57                   	push   edi
  85e0c5:	ff d2                	call   edx
  85e0c7:	8b 07                	mov    eax,DWORD PTR [edi]
  85e0c9:	8b 90 a0 00 00 00    	mov    edx,DWORD PTR [eax+0xa0]
  85e0cf:	8d 4d fc             	lea    ecx,[ebp-0x4]
  85e0d2:	51                   	push   ecx
  85e0d3:	57                   	push   edi
  85e0d4:	ff d2                	call   edx
  85e0d6:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e0d9:	8d 45 e8             	lea    eax,[ebp-0x18]
  85e0dc:	50                   	push   eax
  85e0dd:	33 d2                	xor    edx,edx
  85e0df:	e8 ec 4e ff ff       	call   0x852fd0
  85e0e4:	8b 55 e8             	mov    edx,DWORD PTR [ebp-0x18]
  85e0e7:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e0e9:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  85e0ef:	52                   	push   edx
  85e0f0:	6a 00                	push   0x0
  85e0f2:	57                   	push   edi
  85e0f3:	ff d0                	call   eax
  85e0f5:	d9 e8                	fld1
  85e0f7:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e0fa:	d9 55 c0             	fst    DWORD PTR [ebp-0x40]
  85e0fd:	6a 07                	push   0x7
  85e0ff:	d9 55 c4             	fst    DWORD PTR [ebp-0x3c]
  85e102:	d9 55 c8             	fst    DWORD PTR [ebp-0x38]
  85e105:	6a 00                	push   0x0
  85e107:	d9 55 cc             	fst    DWORD PTR [ebp-0x34]
  85e10a:	6a 00                	push   0x0
  85e10c:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e10e:	8b 40 60             	mov    eax,DWORD PTR [eax+0x60]
  85e111:	51                   	push   ecx
  85e112:	8d 55 c0             	lea    edx,[ebp-0x40]
  85e115:	d9 1c 24             	fstp   DWORD PTR [esp]
  85e118:	ff d0                	call   eax
  85e11a:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e11d:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e11f:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e122:	33 d2                	xor    edx,edx
  85e124:	ff d0                	call   eax
  85e126:	89 46 30             	mov    DWORD PTR [esi+0x30],eax
  85e129:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85e12c:	85 c0                	test   eax,eax
  85e12e:	74 19                	je     0x85e149
  85e130:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e132:	8b 91 94 00 00 00    	mov    edx,DWORD PTR [ecx+0x94]
  85e138:	50                   	push   eax
  85e139:	6a 00                	push   0x0
  85e13b:	57                   	push   edi
  85e13c:	ff d2                	call   edx
  85e13e:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85e141:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e143:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  85e146:	50                   	push   eax
  85e147:	ff d2                	call   edx
  85e149:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85e14c:	85 c0                	test   eax,eax
  85e14e:	74 17                	je     0x85e167
  85e150:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e152:	8b 91 9c 00 00 00    	mov    edx,DWORD PTR [ecx+0x9c]
  85e158:	50                   	push   eax
  85e159:	57                   	push   edi
  85e15a:	ff d2                	call   edx
  85e15c:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85e15f:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e161:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  85e164:	50                   	push   eax
  85e165:	ff d2                	call   edx
  85e167:	32 c0                	xor    al,al
  85e169:	5f                   	pop    edi
  85e16a:	5e                   	pop    esi
  85e16b:	8b e5                	mov    esp,ebp
  85e16d:	5d                   	pop    ebp
  85e16e:	8b e3                	mov    esp,ebx
  85e170:	5b                   	pop    ebx
  85e171:	c3                   	ret
  85e172:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e178:	e8 93 ff fc ff       	call   0x82e110
  85e17d:	8b 56 04             	mov    edx,DWORD PTR [esi+0x4]
  85e180:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e186:	8b f8                	mov    edi,eax
  85e188:	89 7d e4             	mov    DWORD PTR [ebp-0x1c],edi
  85e18b:	e8 80 03 fd ff       	call   0x82e510
  85e190:	8b 4e 08             	mov    ecx,DWORD PTR [esi+0x8]
  85e193:	8b 07                	mov    eax,DWORD PTR [edi]
  85e195:	8b 90 a0 01 00 00    	mov    edx,DWORD PTR [eax+0x1a0]
  85e19b:	51                   	push   ecx
  85e19c:	57                   	push   edi
  85e19d:	ff d2                	call   edx
  85e19f:	85 c0                	test   eax,eax
  85e1a1:	7d 10                	jge    0x85e1b3
  85e1a3:	e8 7a 54 0c 00       	call   0x923622
  85e1a8:	32 c0                	xor    al,al
  85e1aa:	5f                   	pop    edi
  85e1ab:	5e                   	pop    esi
  85e1ac:	8b e5                	mov    esp,ebp
  85e1ae:	5d                   	pop    ebp
  85e1af:	8b e3                	mov    esp,ebx
  85e1b1:	5b                   	pop    ebx
  85e1b2:	c3                   	ret
  85e1b3:	8b 4e 14             	mov    ecx,DWORD PTR [esi+0x14]
  85e1b6:	8b 07                	mov    eax,DWORD PTR [edi]
  85e1b8:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  85e1be:	6a 14                	push   0x14
  85e1c0:	6a 00                	push   0x0
  85e1c2:	51                   	push   ecx
  85e1c3:	6a 00                	push   0x0
  85e1c5:	57                   	push   edi
  85e1c6:	ff d2                	call   edx
  85e1c8:	85 c0                	test   eax,eax
  85e1ca:	7c d7                	jl     0x85e1a3
  85e1cc:	8b 07                	mov    eax,DWORD PTR [edi]
  85e1ce:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  85e1d4:	6a 00                	push   0x0
  85e1d6:	68 c2 00 00 00       	push   0xc2
  85e1db:	57                   	push   edi
  85e1dc:	ff d1                	call   ecx
  85e1de:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85e1e1:	e8 0a ac fd ff       	call   0x838df0
  85e1e6:	8b 17                	mov    edx,DWORD PTR [edi]
  85e1e8:	8b 8a 98 00 00 00    	mov    ecx,DWORD PTR [edx+0x98]
  85e1ee:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85e1f1:	8d 45 d8             	lea    eax,[ebp-0x28]
  85e1f4:	50                   	push   eax
  85e1f5:	6a 00                	push   0x0
  85e1f7:	57                   	push   edi
  85e1f8:	ff d1                	call   ecx
  85e1fa:	8b 17                	mov    edx,DWORD PTR [edi]
  85e1fc:	8b 8a a0 00 00 00    	mov    ecx,DWORD PTR [edx+0xa0]
  85e202:	8d 45 dc             	lea    eax,[ebp-0x24]
  85e205:	50                   	push   eax
  85e206:	57                   	push   edi
  85e207:	ff d1                	call   ecx
  85e209:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  85e20c:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e20e:	8b 02                	mov    eax,DWORD PTR [edx]
  85e210:	ff d0                	call   eax
  85e212:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  85e215:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  85e218:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e21a:	8b 42 04             	mov    eax,DWORD PTR [edx+0x4]
  85e21d:	ff d0                	call   eax
  85e21f:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  85e222:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  85e225:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  85e228:	d9 5d 80             	fstp   DWORD PTR [ebp-0x80]
  85e22b:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  85e22e:	d9 5d 84             	fstp   DWORD PTR [ebp-0x7c]
  85e231:	d9 ee                	fldz
  85e233:	d9 55 88             	fst    DWORD PTR [ebp-0x78]
  85e236:	d9 5d 8c             	fstp   DWORD PTR [ebp-0x74]
  85e239:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e23b:	8b 42 08             	mov    eax,DWORD PTR [edx+0x8]
  85e23e:	ff d0                	call   eax
  85e240:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  85e243:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  85e246:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e248:	8b 42 0c             	mov    eax,DWORD PTR [edx+0xc]
  85e24b:	ff d0                	call   eax
  85e24d:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  85e250:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  85e253:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e256:	d9 5d 90             	fstp   DWORD PTR [ebp-0x70]
  85e259:	8d 4d 80             	lea    ecx,[ebp-0x80]
  85e25c:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  85e25f:	51                   	push   ecx
  85e260:	d9 5d 94             	fstp   DWORD PTR [ebp-0x6c]
  85e263:	68 08 a6 b1 00       	push   0xb1a608
  85e268:	d9 ee                	fldz
  85e26a:	6a 00                	push   0x0
  85e26c:	d9 55 98             	fst    DWORD PTR [ebp-0x68]
  85e26f:	50                   	push   eax
  85e270:	d9 5d 9c             	fstp   DWORD PTR [ebp-0x64]
  85e273:	8b 38                	mov    edi,DWORD PTR [eax]
  85e275:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  85e278:	ff d2                	call   edx
  85e27a:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  85e280:	50                   	push   eax
  85e281:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e284:	50                   	push   eax
  85e285:	ff d1                	call   ecx
  85e287:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e28a:	8b 38                	mov    edi,DWORD PTR [eax]
  85e28c:	8d 55 90             	lea    edx,[ebp-0x70]
  85e28f:	52                   	push   edx
  85e290:	68 f8 a5 b1 00       	push   0xb1a5f8
  85e295:	6a 00                	push   0x0
  85e297:	50                   	push   eax
  85e298:	8b 47 24             	mov    eax,DWORD PTR [edi+0x24]
  85e29b:	ff d0                	call   eax
  85e29d:	8b 4e 24             	mov    ecx,DWORD PTR [esi+0x24]
  85e2a0:	50                   	push   eax
  85e2a1:	8b 97 88 00 00 00    	mov    edx,DWORD PTR [edi+0x88]
  85e2a7:	51                   	push   ecx
  85e2a8:	ff d2                	call   edx
  85e2aa:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  85e2ad:	8b 07                	mov    eax,DWORD PTR [edi]
  85e2af:	8b 50 14             	mov    edx,DWORD PTR [eax+0x14]
  85e2b2:	8b cf                	mov    ecx,edi
  85e2b4:	ff d2                	call   edx
  85e2b6:	85 c0                	test   eax,eax
  85e2b8:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  85e2bb:	db 45 ec             	fild   DWORD PTR [ebp-0x14]
  85e2be:	7d 06                	jge    0x85e2c6
  85e2c0:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85e2c6:	8b 07                	mov    eax,DWORD PTR [edi]
  85e2c8:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  85e2cb:	8b 50 18             	mov    edx,DWORD PTR [eax+0x18]
  85e2ce:	8b cf                	mov    ecx,edi
  85e2d0:	ff d2                	call   edx
  85e2d2:	85 c0                	test   eax,eax
  85e2d4:	89 45 f0             	mov    DWORD PTR [ebp-0x10],eax
  85e2d7:	db 45 f0             	fild   DWORD PTR [ebp-0x10]
  85e2da:	7d 06                	jge    0x85e2e2
  85e2dc:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  85e2e2:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e2e5:	d9 5d f0             	fstp   DWORD PTR [ebp-0x10]
  85e2e8:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  85e2eb:	8d 4d b0             	lea    ecx,[ebp-0x50]
  85e2ee:	d9 5d b0             	fstp   DWORD PTR [ebp-0x50]
  85e2f1:	51                   	push   ecx
  85e2f2:	d9 45 f0             	fld    DWORD PTR [ebp-0x10]
  85e2f5:	68 9c d9 b1 00       	push   0xb1d99c
  85e2fa:	d9 5d b4             	fstp   DWORD PTR [ebp-0x4c]
  85e2fd:	6a 00                	push   0x0
  85e2ff:	d9 ee                	fldz
  85e301:	50                   	push   eax
  85e302:	d9 55 b8             	fst    DWORD PTR [ebp-0x48]
  85e305:	d9 5d bc             	fstp   DWORD PTR [ebp-0x44]
  85e308:	8b 38                	mov    edi,DWORD PTR [eax]
  85e30a:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  85e30d:	ff d2                	call   edx
  85e30f:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  85e315:	50                   	push   eax
  85e316:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e319:	50                   	push   eax
  85e31a:	ff d1                	call   ecx
  85e31c:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  85e31f:	e8 9c 65 fe ff       	call   0x8448c0
  85e324:	8d 95 40 ff ff ff    	lea    edx,[ebp-0xc0]
  85e32a:	52                   	push   edx
  85e32b:	8b f0                	mov    esi,eax
  85e32d:	6a 00                	push   0x0
  85e32f:	8d 85 00 ff ff ff    	lea    eax,[ebp-0x100]
  85e335:	b9 10 00 00 00       	mov    ecx,0x10
  85e33a:	8d bd 40 ff ff ff    	lea    edi,[ebp-0xc0]
  85e340:	50                   	push   eax
  85e341:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  85e343:	e8 30 f6 d1 ff       	call   0x57d978
  85e348:	8b 75 d4             	mov    esi,DWORD PTR [ebp-0x2c]
  85e34b:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e34e:	8b 38                	mov    edi,DWORD PTR [eax]
  85e350:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  85e353:	8d 8d 00 ff ff ff    	lea    ecx,[ebp-0x100]
  85e359:	51                   	push   ecx
  85e35a:	68 90 d9 b1 00       	push   0xb1d990
  85e35f:	6a 00                	push   0x0
  85e361:	50                   	push   eax
  85e362:	ff d2                	call   edx
  85e364:	8b 8f 98 00 00 00    	mov    ecx,DWORD PTR [edi+0x98]
  85e36a:	50                   	push   eax
  85e36b:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e36e:	50                   	push   eax
  85e36f:	ff d1                	call   ecx
  85e371:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e374:	8b 38                	mov    edi,DWORD PTR [eax]
  85e376:	8d 95 40 ff ff ff    	lea    edx,[ebp-0xc0]
  85e37c:	52                   	push   edx
  85e37d:	68 88 d9 b1 00       	push   0xb1d988
  85e382:	6a 00                	push   0x0
  85e384:	50                   	push   eax
  85e385:	8b 47 24             	mov    eax,DWORD PTR [edi+0x24]
  85e388:	ff d0                	call   eax
  85e38a:	8b 4e 24             	mov    ecx,DWORD PTR [esi+0x24]
  85e38d:	8b 97 98 00 00 00    	mov    edx,DWORD PTR [edi+0x98]
  85e393:	50                   	push   eax
  85e394:	51                   	push   ecx
  85e395:	ff d2                	call   edx
  85e397:	8b 7d e8             	mov    edi,DWORD PTR [ebp-0x18]
  85e39a:	8b 07                	mov    eax,DWORD PTR [edi]
  85e39c:	8b 50 3c             	mov    edx,DWORD PTR [eax+0x3c]
  85e39f:	8b cf                	mov    ecx,edi
  85e3a1:	ff d2                	call   edx
  85e3a3:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  85e3a6:	8b 07                	mov    eax,DWORD PTR [edi]
  85e3a8:	8b 50 40             	mov    edx,DWORD PTR [eax+0x40]
  85e3ab:	8b cf                	mov    ecx,edi
  85e3ad:	ff d2                	call   edx
  85e3af:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  85e3b2:	d9 ee                	fldz
  85e3b4:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e3b7:	d9 55 a8             	fst    DWORD PTR [ebp-0x58]
  85e3ba:	8d 4d a0             	lea    ecx,[ebp-0x60]
  85e3bd:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  85e3c0:	51                   	push   ecx
  85e3c1:	8b 38                	mov    edi,DWORD PTR [eax]
  85e3c3:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  85e3c6:	68 7c d9 b1 00       	push   0xb1d97c
  85e3cb:	6a 00                	push   0x0
  85e3cd:	50                   	push   eax
  85e3ce:	ff d2                	call   edx
  85e3d0:	8b 8f 88 00 00 00    	mov    ecx,DWORD PTR [edi+0x88]
  85e3d6:	50                   	push   eax
  85e3d7:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e3da:	50                   	push   eax
  85e3db:	ff d1                	call   ecx
  85e3dd:	8b 4e 28             	mov    ecx,DWORD PTR [esi+0x28]
  85e3e0:	8d 55 e0             	lea    edx,[ebp-0x20]
  85e3e3:	52                   	push   edx
  85e3e4:	33 d2                	xor    edx,edx
  85e3e6:	e8 e5 4b ff ff       	call   0x852fd0
  85e3eb:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
  85e3ee:	8b 7d e4             	mov    edi,DWORD PTR [ebp-0x1c]
  85e3f1:	8b 07                	mov    eax,DWORD PTR [edi]
  85e3f3:	8b 90 94 00 00 00    	mov    edx,DWORD PTR [eax+0x94]
  85e3f9:	51                   	push   ecx
  85e3fa:	6a 00                	push   0x0
  85e3fc:	57                   	push   edi
  85e3fd:	ff d2                	call   edx
  85e3ff:	8b 07                	mov    eax,DWORD PTR [edi]
  85e401:	8b 88 9c 00 00 00    	mov    ecx,DWORD PTR [eax+0x9c]
  85e407:	6a 00                	push   0x0
  85e409:	57                   	push   edi
  85e40a:	ff d1                	call   ecx
  85e40c:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e40f:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e411:	8b 51 34             	mov    edx,DWORD PTR [ecx+0x34]
  85e414:	68 64 d9 b1 00       	push   0xb1d964
  85e419:	50                   	push   eax
  85e41a:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85e41d:	ff d2                	call   edx
  85e41f:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85e422:	8b 91 e8 00 00 00    	mov    edx,DWORD PTR [ecx+0xe8]
  85e428:	50                   	push   eax
  85e429:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e42c:	50                   	push   eax
  85e42d:	ff d2                	call   edx
  85e42f:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  85e432:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e435:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e437:	52                   	push   edx
  85e438:	68 d0 a5 b1 00       	push   0xb1a5d0
  85e43d:	6a 00                	push   0x0
  85e43f:	50                   	push   eax
  85e440:	8b 41 24             	mov    eax,DWORD PTR [ecx+0x24]
  85e443:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85e446:	ff d0                	call   eax
  85e448:	8b 4e 24             	mov    ecx,DWORD PTR [esi+0x24]
  85e44b:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85e44e:	50                   	push   eax
  85e44f:	8b 82 d0 00 00 00    	mov    eax,DWORD PTR [edx+0xd0]
  85e455:	51                   	push   ecx
  85e456:	ff d0                	call   eax
  85e458:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e45b:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e45d:	6a 01                	push   0x1
  85e45f:	8d 55 d0             	lea    edx,[ebp-0x30]
  85e462:	52                   	push   edx
  85e463:	50                   	push   eax
  85e464:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85e46a:	ff d0                	call   eax
  85e46c:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e46f:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e471:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85e477:	6a 00                	push   0x0
  85e479:	50                   	push   eax
  85e47a:	ff d2                	call   edx
  85e47c:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e47f:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e481:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85e487:	50                   	push   eax
  85e488:	ff d2                	call   edx
  85e48a:	8b 07                	mov    eax,DWORD PTR [edi]
  85e48c:	6a 02                	push   0x2
  85e48e:	6a 00                	push   0x0
  85e490:	6a 04                	push   0x4
  85e492:	6a 00                	push   0x0
  85e494:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  85e49a:	6a 00                	push   0x0
  85e49c:	6a 04                	push   0x4
  85e49e:	57                   	push   edi
  85e49f:	ff d1                	call   ecx
  85e4a1:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e4a4:	8b 10                	mov    edx,DWORD PTR [eax]
  85e4a6:	50                   	push   eax
  85e4a7:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  85e4ad:	ff d0                	call   eax
  85e4af:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e4b2:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e4b4:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85e4ba:	50                   	push   eax
  85e4bb:	ff d2                	call   edx
  85e4bd:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e4c0:	8d 45 e0             	lea    eax,[ebp-0x20]
  85e4c3:	50                   	push   eax
  85e4c4:	33 d2                	xor    edx,edx
  85e4c6:	e8 05 4b ff ff       	call   0x852fd0
  85e4cb:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  85e4ce:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e4d0:	8b 81 94 00 00 00    	mov    eax,DWORD PTR [ecx+0x94]
  85e4d6:	52                   	push   edx
  85e4d7:	6a 00                	push   0x0
  85e4d9:	57                   	push   edi
  85e4da:	ff d0                	call   eax
  85e4dc:	8b 4e 28             	mov    ecx,DWORD PTR [esi+0x28]
  85e4df:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e4e1:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e4e4:	33 d2                	xor    edx,edx
  85e4e6:	ff d0                	call   eax
  85e4e8:	8b c8                	mov    ecx,eax
  85e4ea:	e8 01 a9 fd ff       	call   0x838df0
  85e4ef:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85e4f2:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e4f5:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e4f7:	68 58 d9 b1 00       	push   0xb1d958
  85e4fc:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85e4ff:	8b 49 34             	mov    ecx,DWORD PTR [ecx+0x34]
  85e502:	50                   	push   eax
  85e503:	ff d1                	call   ecx
  85e505:	8b 56 24             	mov    edx,DWORD PTR [esi+0x24]
  85e508:	50                   	push   eax
  85e509:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85e50c:	8b 88 e8 00 00 00    	mov    ecx,DWORD PTR [eax+0xe8]
  85e512:	52                   	push   edx
  85e513:	ff d1                	call   ecx
  85e515:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  85e518:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e51b:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e51d:	52                   	push   edx
  85e51e:	68 48 d9 b1 00       	push   0xb1d948
  85e523:	6a 00                	push   0x0
  85e525:	50                   	push   eax
  85e526:	8b 41 24             	mov    eax,DWORD PTR [ecx+0x24]
  85e529:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85e52c:	ff d0                	call   eax
  85e52e:	8b 4e 24             	mov    ecx,DWORD PTR [esi+0x24]
  85e531:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85e534:	50                   	push   eax
  85e535:	8b 82 d0 00 00 00    	mov    eax,DWORD PTR [edx+0xd0]
  85e53b:	51                   	push   ecx
  85e53c:	ff d0                	call   eax
  85e53e:	8b 4e 24             	mov    ecx,DWORD PTR [esi+0x24]
  85e541:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e543:	8b c1                	mov    eax,ecx
  85e545:	8b 4e 18             	mov    ecx,DWORD PTR [esi+0x18]
  85e548:	89 55 e4             	mov    DWORD PTR [ebp-0x1c],edx
  85e54b:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85e54e:	e8 9d a8 fd ff       	call   0x838df0
  85e553:	50                   	push   eax
  85e554:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85e557:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e559:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85e55c:	68 38 d9 b1 00       	push   0xb1d938
  85e561:	6a 00                	push   0x0
  85e563:	50                   	push   eax
  85e564:	ff d2                	call   edx
  85e566:	50                   	push   eax
  85e567:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e56a:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
  85e56d:	8b 91 d0 00 00 00    	mov    edx,DWORD PTR [ecx+0xd0]
  85e573:	50                   	push   eax
  85e574:	ff d2                	call   edx
  85e576:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e579:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e57b:	6a 01                	push   0x1
  85e57d:	8d 55 d0             	lea    edx,[ebp-0x30]
  85e580:	52                   	push   edx
  85e581:	50                   	push   eax
  85e582:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85e588:	ff d0                	call   eax
  85e58a:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e58d:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e58f:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85e595:	6a 00                	push   0x0
  85e597:	50                   	push   eax
  85e598:	ff d2                	call   edx
  85e59a:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e59d:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e59f:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85e5a5:	50                   	push   eax
  85e5a6:	ff d2                	call   edx
  85e5a8:	8b 07                	mov    eax,DWORD PTR [edi]
  85e5aa:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  85e5b0:	6a 02                	push   0x2
  85e5b2:	6a 00                	push   0x0
  85e5b4:	6a 04                	push   0x4
  85e5b6:	6a 00                	push   0x0
  85e5b8:	6a 00                	push   0x0
  85e5ba:	6a 04                	push   0x4
  85e5bc:	57                   	push   edi
  85e5bd:	ff d1                	call   ecx
  85e5bf:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e5c2:	8b 10                	mov    edx,DWORD PTR [eax]
  85e5c4:	50                   	push   eax
  85e5c5:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  85e5cb:	ff d0                	call   eax
  85e5cd:	8b 46 24             	mov    eax,DWORD PTR [esi+0x24]
  85e5d0:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e5d2:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85e5d8:	50                   	push   eax
  85e5d9:	ff d2                	call   edx
  85e5db:	d9 e8                	fld1
  85e5dd:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85e5e0:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e5e2:	8b 56 28             	mov    edx,DWORD PTR [esi+0x28]
  85e5e5:	89 4d f8             	mov    DWORD PTR [ebp-0x8],ecx
  85e5e8:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e5eb:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e5ed:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e5f0:	51                   	push   ecx
  85e5f1:	d9 1c 24             	fstp   DWORD PTR [esp]
  85e5f4:	52                   	push   edx
  85e5f5:	33 d2                	xor    edx,edx
  85e5f7:	ff d0                	call   eax
  85e5f9:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  85e5fc:	8b d0                	mov    edx,eax
  85e5fe:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85e601:	8b 80 90 00 00 00    	mov    eax,DWORD PTR [eax+0x90]
  85e607:	ff d0                	call   eax
  85e609:	8b 4e 28             	mov    ecx,DWORD PTR [esi+0x28]
  85e60c:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e60e:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e611:	33 d2                	xor    edx,edx
  85e613:	ff d0                	call   eax
  85e615:	83 7e 20 00          	cmp    DWORD PTR [esi+0x20],0x0
  85e619:	89 46 30             	mov    DWORD PTR [esi+0x30],eax
  85e61c:	76 3d                	jbe    0x85e65b
  85e61e:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  85e621:	d9 e8                	fld1
  85e623:	8b 11                	mov    edx,DWORD PTR [ecx]
  85e625:	8b 4e 28             	mov    ecx,DWORD PTR [esi+0x28]
  85e628:	8b 46 2c             	mov    eax,DWORD PTR [esi+0x2c]
  85e62b:	51                   	push   ecx
  85e62c:	d9 1c 24             	fstp   DWORD PTR [esp]
  85e62f:	50                   	push   eax
  85e630:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e632:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e635:	89 55 f8             	mov    DWORD PTR [ebp-0x8],edx
  85e638:	33 d2                	xor    edx,edx
  85e63a:	ff d0                	call   eax
  85e63c:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  85e63f:	8b d0                	mov    edx,eax
  85e641:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85e644:	8b 80 90 00 00 00    	mov    eax,DWORD PTR [eax+0x90]
  85e64a:	ff d0                	call   eax
  85e64c:	8b 4e 2c             	mov    ecx,DWORD PTR [esi+0x2c]
  85e64f:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e651:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85e654:	33 d2                	xor    edx,edx
  85e656:	ff d0                	call   eax
  85e658:	89 46 30             	mov    DWORD PTR [esi+0x30],eax
  85e65b:	8b 45 d8             	mov    eax,DWORD PTR [ebp-0x28]
  85e65e:	85 c0                	test   eax,eax
  85e660:	74 19                	je     0x85e67b
  85e662:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e664:	8b 91 94 00 00 00    	mov    edx,DWORD PTR [ecx+0x94]
  85e66a:	50                   	push   eax
  85e66b:	6a 00                	push   0x0
  85e66d:	57                   	push   edi
  85e66e:	ff d2                	call   edx
  85e670:	8b 45 d8             	mov    eax,DWORD PTR [ebp-0x28]
  85e673:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e675:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  85e678:	50                   	push   eax
  85e679:	ff d2                	call   edx
  85e67b:	8b 45 dc             	mov    eax,DWORD PTR [ebp-0x24]
  85e67e:	85 c0                	test   eax,eax
  85e680:	74 17                	je     0x85e699
  85e682:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85e684:	8b 91 9c 00 00 00    	mov    edx,DWORD PTR [ecx+0x9c]
  85e68a:	50                   	push   eax
  85e68b:	57                   	push   edi
  85e68c:	ff d2                	call   edx
  85e68e:	8b 45 dc             	mov    eax,DWORD PTR [ebp-0x24]
  85e691:	8b 08                	mov    ecx,DWORD PTR [eax]
  85e693:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  85e696:	50                   	push   eax
  85e697:	ff d2                	call   edx
  85e699:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e69f:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e6a1:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  85e6a7:	33 d2                	xor    edx,edx
  85e6a9:	ff d0                	call   eax
  85e6ab:	85 c0                	test   eax,eax
  85e6ad:	74 19                	je     0x85e6c8
  85e6af:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85e6b5:	8b 01                	mov    eax,DWORD PTR [ecx]
  85e6b7:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  85e6bd:	33 d2                	xor    edx,edx
  85e6bf:	ff d0                	call   eax
  85e6c1:	8b c8                	mov    ecx,eax
  85e6c3:	e8 88 4c ff ff       	call   0x853350
  85e6c8:	5f                   	pop    edi
  85e6c9:	b0 01                	mov    al,0x1
  85e6cb:	5e                   	pop    esi
  85e6cc:	8b e5                	mov    esp,ebp
  85e6ce:	5d                   	pop    ebp
  85e6cf:	8b e3                	mov    esp,ebx
  85e6d1:	5b                   	pop    ebx
  85e6d2:	c3                   	ret
```

### `0x0085f6e0..0x0085f996` — sites `0x0085f920`

```asm
  85f6e0:	55                   	push   ebp
  85f6e1:	8b ec                	mov    ebp,esp
  85f6e3:	83 ec 0c             	sub    esp,0xc
  85f6e6:	56                   	push   esi
  85f6e7:	8b f1                	mov    esi,ecx
  85f6e9:	80 be 80 00 00 00 00 	cmp    BYTE PTR [esi+0x80],0x0
  85f6f0:	75 07                	jne    0x85f6f9
  85f6f2:	b0 01                	mov    al,0x1
  85f6f4:	5e                   	pop    esi
  85f6f5:	8b e5                	mov    esp,ebp
  85f6f7:	5d                   	pop    ebp
  85f6f8:	c3                   	ret
  85f6f9:	53                   	push   ebx
  85f6fa:	8b 1d 58 60 c2 00    	mov    ebx,DWORD PTR ds:0xc26058
  85f700:	57                   	push   edi
  85f701:	8b cb                	mov    ecx,ebx
  85f703:	e8 08 ea fc ff       	call   0x82e110
  85f708:	8b f8                	mov    edi,eax
  85f70a:	8b 03                	mov    eax,DWORD PTR [ebx]
  85f70c:	8b 90 0c 01 00 00    	mov    edx,DWORD PTR [eax+0x10c]
  85f712:	8b cb                	mov    ecx,ebx
  85f714:	ff d2                	call   edx
  85f716:	8b d8                	mov    ebx,eax
  85f718:	85 db                	test   ebx,ebx
  85f71a:	0f 84 66 02 00 00    	je     0x85f986
  85f720:	8b 03                	mov    eax,DWORD PTR [ebx]
  85f722:	8b 10                	mov    edx,DWORD PTR [eax]
  85f724:	8b cb                	mov    ecx,ebx
  85f726:	ff d2                	call   edx
  85f728:	84 c0                	test   al,al
  85f72a:	0f 84 56 02 00 00    	je     0x85f986
  85f730:	8b cb                	mov    ecx,ebx
  85f732:	e8 f9 0b ff ff       	call   0x850330
  85f737:	80 be 82 00 00 00 00 	cmp    BYTE PTR [esi+0x82],0x0
  85f73e:	8b d8                	mov    ebx,eax
  85f740:	89 5d f8             	mov    DWORD PTR [ebp-0x8],ebx
  85f743:	0f 85 09 02 00 00    	jne    0x85f952
  85f749:	8b 07                	mov    eax,DWORD PTR [edi]
  85f74b:	8b 88 94 00 00 00    	mov    ecx,DWORD PTR [eax+0x94]
  85f751:	53                   	push   ebx
  85f752:	6a 00                	push   0x0
  85f754:	57                   	push   edi
  85f755:	ff d1                	call   ecx
  85f757:	8b 17                	mov    edx,DWORD PTR [edi]
  85f759:	8b 82 9c 00 00 00    	mov    eax,DWORD PTR [edx+0x9c]
  85f75f:	6a 00                	push   0x0
  85f761:	57                   	push   edi
  85f762:	ff d0                	call   eax
  85f764:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85f766:	8b 91 a4 00 00 00    	mov    edx,DWORD PTR [ecx+0xa4]
  85f76c:	57                   	push   edi
  85f76d:	ff d2                	call   edx
  85f76f:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f775:	8b 18                	mov    ebx,DWORD PTR [eax]
  85f777:	68 40 da b1 00       	push   0xb1da40
  85f77c:	50                   	push   eax
  85f77d:	8b 43 34             	mov    eax,DWORD PTR [ebx+0x34]
  85f780:	ff d0                	call   eax
  85f782:	8b 8e b8 00 00 00    	mov    ecx,DWORD PTR [esi+0xb8]
  85f788:	8b 93 e8 00 00 00    	mov    edx,DWORD PTR [ebx+0xe8]
  85f78e:	50                   	push   eax
  85f78f:	51                   	push   ecx
  85f790:	ff d2                	call   edx
  85f792:	8b 96 bc 00 00 00    	mov    edx,DWORD PTR [esi+0xbc]
  85f798:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85f79e:	e8 6d ed fc ff       	call   0x82e510
  85f7a3:	8b 8e c0 00 00 00    	mov    ecx,DWORD PTR [esi+0xc0]
  85f7a9:	8b 07                	mov    eax,DWORD PTR [edi]
  85f7ab:	8b 90 90 01 00 00    	mov    edx,DWORD PTR [eax+0x190]
  85f7b1:	6a 14                	push   0x14
  85f7b3:	6a 00                	push   0x0
  85f7b5:	51                   	push   ecx
  85f7b6:	6a 00                	push   0x0
  85f7b8:	57                   	push   edi
  85f7b9:	ff d2                	call   edx
  85f7bb:	8b 8e cc 00 00 00    	mov    ecx,DWORD PTR [esi+0xcc]
  85f7c1:	8b 07                	mov    eax,DWORD PTR [edi]
  85f7c3:	8b 90 a0 01 00 00    	mov    edx,DWORD PTR [eax+0x1a0]
  85f7c9:	51                   	push   ecx
  85f7ca:	57                   	push   edi
  85f7cb:	ff d2                	call   edx
  85f7cd:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f7d3:	8b 08                	mov    ecx,DWORD PTR [eax]
  85f7d5:	89 4d fc             	mov    DWORD PTR [ebp-0x4],ecx
  85f7d8:	8b 8e b4 00 00 00    	mov    ecx,DWORD PTR [esi+0xb4]
  85f7de:	8b d8                	mov    ebx,eax
  85f7e0:	e8 0b 96 fd ff       	call   0x838df0
  85f7e5:	8b 13                	mov    edx,DWORD PTR [ebx]
  85f7e7:	50                   	push   eax
  85f7e8:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85f7eb:	68 30 da b1 00       	push   0xb1da30
  85f7f0:	6a 00                	push   0x0
  85f7f2:	53                   	push   ebx
  85f7f3:	ff d0                	call   eax
  85f7f5:	8b 8e b8 00 00 00    	mov    ecx,DWORD PTR [esi+0xb8]
  85f7fb:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85f7fe:	50                   	push   eax
  85f7ff:	8b 82 d0 00 00 00    	mov    eax,DWORD PTR [edx+0xd0]
  85f805:	51                   	push   ecx
  85f806:	ff d0                	call   eax
  85f808:	d9 86 84 00 00 00    	fld    DWORD PTR [esi+0x84]
  85f80e:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f814:	8b 18                	mov    ebx,DWORD PTR [eax]
  85f816:	51                   	push   ecx
  85f817:	8b 4b 24             	mov    ecx,DWORD PTR [ebx+0x24]
  85f81a:	d9 1c 24             	fstp   DWORD PTR [esp]
  85f81d:	68 20 da b1 00       	push   0xb1da20
  85f822:	6a 00                	push   0x0
  85f824:	50                   	push   eax
  85f825:	ff d1                	call   ecx
  85f827:	8b 96 b8 00 00 00    	mov    edx,DWORD PTR [esi+0xb8]
  85f82d:	50                   	push   eax
  85f82e:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85f831:	52                   	push   edx
  85f832:	ff d0                	call   eax
  85f834:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f83a:	8b 18                	mov    ebx,DWORD PTR [eax]
  85f83c:	51                   	push   ecx
  85f83d:	d9 86 88 00 00 00    	fld    DWORD PTR [esi+0x88]
  85f843:	8b 4b 24             	mov    ecx,DWORD PTR [ebx+0x24]
  85f846:	d9 1c 24             	fstp   DWORD PTR [esp]
  85f849:	68 14 da b1 00       	push   0xb1da14
  85f84e:	6a 00                	push   0x0
  85f850:	50                   	push   eax
  85f851:	ff d1                	call   ecx
  85f853:	8b 96 b8 00 00 00    	mov    edx,DWORD PTR [esi+0xb8]
  85f859:	50                   	push   eax
  85f85a:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85f85d:	52                   	push   edx
  85f85e:	ff d0                	call   eax
  85f860:	d9 86 8c 00 00 00    	fld    DWORD PTR [esi+0x8c]
  85f866:	d9 e8                	fld1
  85f868:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f86e:	de f1                	fdivrp st(1),st
  85f870:	8b 18                	mov    ebx,DWORD PTR [eax]
  85f872:	51                   	push   ecx
  85f873:	8b 4b 24             	mov    ecx,DWORD PTR [ebx+0x24]
  85f876:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  85f879:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85f87c:	d9 1c 24             	fstp   DWORD PTR [esp]
  85f87f:	68 08 da b1 00       	push   0xb1da08
  85f884:	6a 00                	push   0x0
  85f886:	50                   	push   eax
  85f887:	ff d1                	call   ecx
  85f889:	8b 96 b8 00 00 00    	mov    edx,DWORD PTR [esi+0xb8]
  85f88f:	50                   	push   eax
  85f890:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85f893:	52                   	push   edx
  85f894:	ff d0                	call   eax
  85f896:	d9 86 90 00 00 00    	fld    DWORD PTR [esi+0x90]
  85f89c:	d8 b6 8c 00 00 00    	fdiv   DWORD PTR [esi+0x8c]
  85f8a2:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f8a8:	8b 18                	mov    ebx,DWORD PTR [eax]
  85f8aa:	51                   	push   ecx
  85f8ab:	8b 4b 24             	mov    ecx,DWORD PTR [ebx+0x24]
  85f8ae:	d9 e0                	fchs
  85f8b0:	d9 5d fc             	fstp   DWORD PTR [ebp-0x4]
  85f8b3:	d9 45 fc             	fld    DWORD PTR [ebp-0x4]
  85f8b6:	d9 1c 24             	fstp   DWORD PTR [esp]
  85f8b9:	68 f8 d9 b1 00       	push   0xb1d9f8
  85f8be:	6a 00                	push   0x0
  85f8c0:	50                   	push   eax
  85f8c1:	ff d1                	call   ecx
  85f8c3:	8b 96 b8 00 00 00    	mov    edx,DWORD PTR [esi+0xb8]
  85f8c9:	50                   	push   eax
  85f8ca:	8b 43 78             	mov    eax,DWORD PTR [ebx+0x78]
  85f8cd:	52                   	push   edx
  85f8ce:	ff d0                	call   eax
  85f8d0:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f8d6:	8b 08                	mov    ecx,DWORD PTR [eax]
  85f8d8:	6a 01                	push   0x1
  85f8da:	8d 55 f4             	lea    edx,[ebp-0xc]
  85f8dd:	52                   	push   edx
  85f8de:	50                   	push   eax
  85f8df:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85f8e5:	ff d0                	call   eax
  85f8e7:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f8ed:	8b 08                	mov    ecx,DWORD PTR [eax]
  85f8ef:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85f8f5:	6a 00                	push   0x0
  85f8f7:	50                   	push   eax
  85f8f8:	ff d2                	call   edx
  85f8fa:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f900:	8b 08                	mov    ecx,DWORD PTR [eax]
  85f902:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85f908:	50                   	push   eax
  85f909:	ff d2                	call   edx
  85f90b:	8b 07                	mov    eax,DWORD PTR [edi]
  85f90d:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  85f913:	6a 02                	push   0x2
  85f915:	6a 00                	push   0x0
  85f917:	6a 04                	push   0x4
  85f919:	6a 00                	push   0x0
  85f91b:	6a 00                	push   0x0
  85f91d:	6a 05                	push   0x5
  85f91f:	57                   	push   edi
  85f920:	ff d1                	call   ecx
  85f922:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f928:	8b 10                	mov    edx,DWORD PTR [eax]
  85f92a:	50                   	push   eax
  85f92b:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  85f931:	ff d0                	call   eax
  85f933:	8b 86 b8 00 00 00    	mov    eax,DWORD PTR [esi+0xb8]
  85f939:	8b 08                	mov    ecx,DWORD PTR [eax]
  85f93b:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85f941:	50                   	push   eax
  85f942:	ff d2                	call   edx
  85f944:	8b 07                	mov    eax,DWORD PTR [edi]
  85f946:	8b 88 a8 00 00 00    	mov    ecx,DWORD PTR [eax+0xa8]
  85f94c:	57                   	push   edi
  85f94d:	ff d1                	call   ecx
  85f94f:	8b 5d f8             	mov    ebx,DWORD PTR [ebp-0x8]
  85f952:	8b 8e b0 00 00 00    	mov    ecx,DWORD PTR [esi+0xb0]
  85f958:	8d 55 f8             	lea    edx,[ebp-0x8]
  85f95b:	52                   	push   edx
  85f95c:	33 d2                	xor    edx,edx
  85f95e:	e8 6d 36 ff ff       	call   0x852fd0
  85f963:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  85f966:	8b 07                	mov    eax,DWORD PTR [edi]
  85f968:	8b 90 88 00 00 00    	mov    edx,DWORD PTR [eax+0x88]
  85f96e:	6a 00                	push   0x0
  85f970:	6a 00                	push   0x0
  85f972:	51                   	push   ecx
  85f973:	6a 00                	push   0x0
  85f975:	53                   	push   ebx
  85f976:	57                   	push   edi
  85f977:	ff d2                	call   edx
  85f979:	85 c0                	test   eax,eax
  85f97b:	7d 09                	jge    0x85f986
  85f97d:	5f                   	pop    edi
  85f97e:	5b                   	pop    ebx
  85f97f:	32 c0                	xor    al,al
  85f981:	5e                   	pop    esi
  85f982:	8b e5                	mov    esp,ebp
  85f984:	5d                   	pop    ebp
  85f985:	c3                   	ret
  85f986:	5f                   	pop    edi
  85f987:	5b                   	pop    ebx
  85f988:	c6 86 82 00 00 00 00 	mov    BYTE PTR [esi+0x82],0x0
  85f98f:	b0 01                	mov    al,0x1
  85f991:	5e                   	pop    esi
  85f992:	8b e5                	mov    esp,ebp
  85f994:	5d                   	pop    ebp
  85f995:	c3                   	ret
```

### `0x0085fb00..0x00860bed` — sites `0x0085fc9c`, `0x0085fd3c`, `0x00860baf`

```asm
  85fb00:	53                   	push   ebx
  85fb01:	8b dc                	mov    ebx,esp
  85fb03:	83 ec 08             	sub    esp,0x8
  85fb06:	83 e4 f0             	and    esp,0xfffffff0
  85fb09:	83 c4 04             	add    esp,0x4
  85fb0c:	55                   	push   ebp
  85fb0d:	8b 6b 04             	mov    ebp,DWORD PTR [ebx+0x4]
  85fb10:	89 6c 24 04          	mov    DWORD PTR [esp+0x4],ebp
  85fb14:	8b ec                	mov    ebp,esp
  85fb16:	81 ec f8 06 00 00    	sub    esp,0x6f8
  85fb1c:	80 7b 18 00          	cmp    BYTE PTR [ebx+0x18],0x0
  85fb20:	56                   	push   esi
  85fb21:	8b f1                	mov    esi,ecx
  85fb23:	57                   	push   edi
  85fb24:	89 55 ec             	mov    DWORD PTR [ebp-0x14],edx
  85fb27:	89 75 fc             	mov    DWORD PTR [ebp-0x4],esi
  85fb2a:	74 0b                	je     0x85fb37
  85fb2c:	80 be b0 08 00 00 00 	cmp    BYTE PTR [esi+0x8b0],0x0
  85fb33:	75 11                	jne    0x85fb46
  85fb35:	eb 09                	jmp    0x85fb40
  85fb37:	80 be b0 08 00 00 00 	cmp    BYTE PTR [esi+0x8b0],0x0
  85fb3e:	74 06                	je     0x85fb46
  85fb40:	83 7b 0c 00          	cmp    DWORD PTR [ebx+0xc],0x0
  85fb44:	75 0d                	jne    0x85fb53
  85fb46:	32 c0                	xor    al,al
  85fb48:	5f                   	pop    edi
  85fb49:	5e                   	pop    esi
  85fb4a:	8b e5                	mov    esp,ebp
  85fb4c:	5d                   	pop    ebp
  85fb4d:	8b e3                	mov    esp,ebx
  85fb4f:	5b                   	pop    ebx
  85fb50:	c2 28 00             	ret    0x28
  85fb53:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85fb59:	e8 b2 e5 fc ff       	call   0x82e110
  85fb5e:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85fb64:	8b f8                	mov    edi,eax
  85fb66:	8b 01                	mov    eax,DWORD PTR [ecx]
  85fb68:	8b 90 0c 01 00 00    	mov    edx,DWORD PTR [eax+0x10c]
  85fb6e:	89 bd a8 fe ff ff    	mov    DWORD PTR [ebp-0x158],edi
  85fb74:	ff d2                	call   edx
  85fb76:	8b 10                	mov    edx,DWORD PTR [eax]
  85fb78:	8b c8                	mov    ecx,eax
  85fb7a:	8b 02                	mov    eax,DWORD PTR [edx]
  85fb7c:	ff d0                	call   eax
  85fb7e:	84 c0                	test   al,al
  85fb80:	74 c4                	je     0x85fb46
  85fb82:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fb84:	8b 81 98 00 00 00    	mov    eax,DWORD PTR [ecx+0x98]
  85fb8a:	8d 55 8c             	lea    edx,[ebp-0x74]
  85fb8d:	52                   	push   edx
  85fb8e:	6a 00                	push   0x0
  85fb90:	57                   	push   edi
  85fb91:	ff d0                	call   eax
  85fb93:	8b 45 8c             	mov    eax,DWORD PTR [ebp-0x74]
  85fb96:	8b 08                	mov    ecx,DWORD PTR [eax]
  85fb98:	8b 51 08             	mov    edx,DWORD PTR [ecx+0x8]
  85fb9b:	50                   	push   eax
  85fb9c:	ff d2                	call   edx
  85fb9e:	8b 8e 7c 08 00 00    	mov    ecx,DWORD PTR [esi+0x87c]
  85fba4:	8d 85 ac fe ff ff    	lea    eax,[ebp-0x154]
  85fbaa:	50                   	push   eax
  85fbab:	33 d2                	xor    edx,edx
  85fbad:	e8 1e 34 ff ff       	call   0x852fd0
  85fbb2:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fbb4:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  85fbba:	6a 00                	push   0x0
  85fbbc:	68 c2 00 00 00       	push   0xc2
  85fbc1:	57                   	push   edi
  85fbc2:	ff d2                	call   edx
  85fbc4:	e8 87 c4 fc ff       	call   0x82c050
  85fbc9:	8b c8                	mov    ecx,eax
  85fbcb:	e8 90 aa fc ff       	call   0x82a660
  85fbd0:	e8 db c4 fc ff       	call   0x82c0b0
  85fbd5:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85fbd8:	80 b8 b0 08 00 00 00 	cmp    BYTE PTR [eax+0x8b0],0x0
  85fbdf:	8b b6 70 06 00 00    	mov    esi,DWORD PTR [esi+0x670]
  85fbe5:	89 75 dc             	mov    DWORD PTR [ebp-0x24],esi
  85fbe8:	0f 84 87 01 00 00    	je     0x85fd75
  85fbee:	8b 90 c4 00 00 00    	mov    edx,DWORD PTR [eax+0xc4]
  85fbf4:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85fbfa:	e8 11 e9 fc ff       	call   0x82e510
  85fbff:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  85fc02:	8b 91 20 05 00 00    	mov    edx,DWORD PTR [ecx+0x520]
  85fc08:	8b 07                	mov    eax,DWORD PTR [edi]
  85fc0a:	8b 80 90 01 00 00    	mov    eax,DWORD PTR [eax+0x190]
  85fc10:	6a 14                	push   0x14
  85fc12:	6a 00                	push   0x0
  85fc14:	52                   	push   edx
  85fc15:	6a 00                	push   0x0
  85fc17:	57                   	push   edi
  85fc18:	ff d0                	call   eax
  85fc1a:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85fc1d:	8b 82 cc 00 00 00    	mov    eax,DWORD PTR [edx+0xcc]
  85fc23:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fc25:	8b 89 a0 01 00 00    	mov    ecx,DWORD PTR [ecx+0x1a0]
  85fc2b:	50                   	push   eax
  85fc2c:	57                   	push   edi
  85fc2d:	ff d1                	call   ecx
  85fc2f:	8b 17                	mov    edx,DWORD PTR [edi]
  85fc31:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  85fc37:	6a 08                	push   0x8
  85fc39:	68 a8 00 00 00       	push   0xa8
  85fc3e:	57                   	push   edi
  85fc3f:	ff d0                	call   eax
  85fc41:	8b 06                	mov    eax,DWORD PTR [esi]
  85fc43:	8b 48 34             	mov    ecx,DWORD PTR [eax+0x34]
  85fc46:	68 c4 da b1 00       	push   0xb1dac4
  85fc4b:	56                   	push   esi
  85fc4c:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85fc4f:	ff d1                	call   ecx
  85fc51:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  85fc54:	50                   	push   eax
  85fc55:	8b 82 e8 00 00 00    	mov    eax,DWORD PTR [edx+0xe8]
  85fc5b:	56                   	push   esi
  85fc5c:	ff d0                	call   eax
  85fc5e:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fc60:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  85fc66:	6a 01                	push   0x1
  85fc68:	8d 55 e0             	lea    edx,[ebp-0x20]
  85fc6b:	52                   	push   edx
  85fc6c:	56                   	push   esi
  85fc6d:	ff d0                	call   eax
  85fc6f:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fc71:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  85fc77:	6a 00                	push   0x0
  85fc79:	56                   	push   esi
  85fc7a:	ff d2                	call   edx
  85fc7c:	8b 06                	mov    eax,DWORD PTR [esi]
  85fc7e:	8b 88 04 01 00 00    	mov    ecx,DWORD PTR [eax+0x104]
  85fc84:	56                   	push   esi
  85fc85:	ff d1                	call   ecx
  85fc87:	8b 17                	mov    edx,DWORD PTR [edi]
  85fc89:	8b 82 48 01 00 00    	mov    eax,DWORD PTR [edx+0x148]
  85fc8f:	6a 02                	push   0x2
  85fc91:	6a 00                	push   0x0
  85fc93:	6a 04                	push   0x4
  85fc95:	6a 00                	push   0x0
  85fc97:	6a 00                	push   0x0
  85fc99:	6a 05                	push   0x5
  85fc9b:	57                   	push   edi
  85fc9c:	ff d0                	call   eax
  85fc9e:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fca0:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  85fca6:	56                   	push   esi
  85fca7:	ff d2                	call   edx
  85fca9:	8b 06                	mov    eax,DWORD PTR [esi]
  85fcab:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  85fcb1:	56                   	push   esi
  85fcb2:	ff d1                	call   ecx
  85fcb4:	8b 06                	mov    eax,DWORD PTR [esi]
  85fcb6:	8b 50 34             	mov    edx,DWORD PTR [eax+0x34]
  85fcb9:	68 ac da b1 00       	push   0xb1daac
  85fcbe:	56                   	push   esi
  85fcbf:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85fcc2:	ff d2                	call   edx
  85fcc4:	50                   	push   eax
  85fcc5:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85fcc8:	8b 88 e8 00 00 00    	mov    ecx,DWORD PTR [eax+0xe8]
  85fcce:	56                   	push   esi
  85fccf:	ff d1                	call   ecx
  85fcd1:	8b 17                	mov    edx,DWORD PTR [edi]
  85fcd3:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  85fcd9:	6a 01                	push   0x1
  85fcdb:	6a 34                	push   0x34
  85fcdd:	57                   	push   edi
  85fcde:	ff d0                	call   eax
  85fce0:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fce2:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  85fce8:	6a 03                	push   0x3
  85fcea:	6a 38                	push   0x38
  85fcec:	57                   	push   edi
  85fced:	ff d2                	call   edx
  85fcef:	8b 07                	mov    eax,DWORD PTR [edi]
  85fcf1:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  85fcf7:	6a 01                	push   0x1
  85fcf9:	6a 39                	push   0x39
  85fcfb:	57                   	push   edi
  85fcfc:	ff d1                	call   ecx
  85fcfe:	8b 16                	mov    edx,DWORD PTR [esi]
  85fd00:	8b 8a fc 00 00 00    	mov    ecx,DWORD PTR [edx+0xfc]
  85fd06:	6a 01                	push   0x1
  85fd08:	8d 45 e0             	lea    eax,[ebp-0x20]
  85fd0b:	50                   	push   eax
  85fd0c:	56                   	push   esi
  85fd0d:	ff d1                	call   ecx
  85fd0f:	8b 16                	mov    edx,DWORD PTR [esi]
  85fd11:	8b 82 00 01 00 00    	mov    eax,DWORD PTR [edx+0x100]
  85fd17:	6a 00                	push   0x0
  85fd19:	56                   	push   esi
  85fd1a:	ff d0                	call   eax
  85fd1c:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fd1e:	8b 91 04 01 00 00    	mov    edx,DWORD PTR [ecx+0x104]
  85fd24:	56                   	push   esi
  85fd25:	ff d2                	call   edx
  85fd27:	8b 07                	mov    eax,DWORD PTR [edi]
  85fd29:	8b 88 48 01 00 00    	mov    ecx,DWORD PTR [eax+0x148]
  85fd2f:	6a 02                	push   0x2
  85fd31:	6a 00                	push   0x0
  85fd33:	6a 04                	push   0x4
  85fd35:	6a 00                	push   0x0
  85fd37:	6a 00                	push   0x0
  85fd39:	6a 05                	push   0x5
  85fd3b:	57                   	push   edi
  85fd3c:	ff d1                	call   ecx
  85fd3e:	8b 16                	mov    edx,DWORD PTR [esi]
  85fd40:	8b 82 08 01 00 00    	mov    eax,DWORD PTR [edx+0x108]
  85fd46:	56                   	push   esi
  85fd47:	ff d0                	call   eax
  85fd49:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fd4b:	8b 91 0c 01 00 00    	mov    edx,DWORD PTR [ecx+0x10c]
  85fd51:	56                   	push   esi
  85fd52:	ff d2                	call   edx
  85fd54:	8b 07                	mov    eax,DWORD PTR [edi]
  85fd56:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  85fd5c:	6a 0f                	push   0xf
  85fd5e:	68 a8 00 00 00       	push   0xa8
  85fd63:	57                   	push   edi
  85fd64:	ff d1                	call   ecx
  85fd66:	8b 17                	mov    edx,DWORD PTR [edi]
  85fd68:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  85fd6e:	6a 00                	push   0x0
  85fd70:	6a 34                	push   0x34
  85fd72:	57                   	push   edi
  85fd73:	ff d0                	call   eax
  85fd75:	8b 95 ac fe ff ff    	mov    edx,DWORD PTR [ebp-0x154]
  85fd7b:	8b 45 8c             	mov    eax,DWORD PTR [ebp-0x74]
  85fd7e:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fd80:	8b 89 88 00 00 00    	mov    ecx,DWORD PTR [ecx+0x88]
  85fd86:	6a 00                	push   0x0
  85fd88:	6a 00                	push   0x0
  85fd8a:	52                   	push   edx
  85fd8b:	6a 00                	push   0x0
  85fd8d:	50                   	push   eax
  85fd8e:	57                   	push   edi
  85fd8f:	ff d1                	call   ecx
  85fd91:	8b 06                	mov    eax,DWORD PTR [esi]
  85fd93:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85fd96:	80 ba b0 08 00 00 00 	cmp    BYTE PTR [edx+0x8b0],0x0
  85fd9d:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85fda0:	8b 40 34             	mov    eax,DWORD PTR [eax+0x34]
  85fda3:	74 07                	je     0x85fdac
  85fda5:	68 98 da b1 00       	push   0xb1da98
  85fdaa:	eb 05                	jmp    0x85fdb1
  85fdac:	68 2c a7 b1 00       	push   0xb1a72c
  85fdb1:	56                   	push   esi
  85fdb2:	ff d0                	call   eax
  85fdb4:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  85fdb7:	8b 91 e8 00 00 00    	mov    edx,DWORD PTR [ecx+0xe8]
  85fdbd:	50                   	push   eax
  85fdbe:	56                   	push   esi
  85fdbf:	ff d2                	call   edx
  85fdc1:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85fdc4:	8b 90 c4 00 00 00    	mov    edx,DWORD PTR [eax+0xc4]
  85fdca:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  85fdd0:	e8 3b e7 fc ff       	call   0x82e510
  85fdd5:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  85fdd8:	8b 82 20 05 00 00    	mov    eax,DWORD PTR [edx+0x520]
  85fdde:	8b 0f                	mov    ecx,DWORD PTR [edi]
  85fde0:	8b 89 90 01 00 00    	mov    ecx,DWORD PTR [ecx+0x190]
  85fde6:	6a 14                	push   0x14
  85fde8:	6a 00                	push   0x0
  85fdea:	50                   	push   eax
  85fdeb:	6a 00                	push   0x0
  85fded:	57                   	push   edi
  85fdee:	ff d1                	call   ecx
  85fdf0:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  85fdf3:	8b 88 cc 00 00 00    	mov    ecx,DWORD PTR [eax+0xcc]
  85fdf9:	8b 17                	mov    edx,DWORD PTR [edi]
  85fdfb:	8b 92 a0 01 00 00    	mov    edx,DWORD PTR [edx+0x1a0]
  85fe01:	51                   	push   ecx
  85fe02:	57                   	push   edi
  85fe03:	ff d2                	call   edx
  85fe05:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  85fe08:	8b 8f 7c 08 00 00    	mov    ecx,DWORD PTR [edi+0x87c]
  85fe0e:	8b 01                	mov    eax,DWORD PTR [ecx]
  85fe10:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  85fe13:	33 d2                	xor    edx,edx
  85fe15:	ff d0                	call   eax
  85fe17:	8b 16                	mov    edx,DWORD PTR [esi]
  85fe19:	81 c2 d0 00 00 00    	add    edx,0xd0
  85fe1f:	8b c8                	mov    ecx,eax
  85fe21:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
  85fe24:	89 55 f4             	mov    DWORD PTR [ebp-0xc],edx
  85fe27:	e8 c4 8f fd ff       	call   0x838df0
  85fe2c:	8b 0e                	mov    ecx,DWORD PTR [esi]
  85fe2e:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  85fe31:	50                   	push   eax
  85fe32:	68 dc a5 b1 00       	push   0xb1a5dc
  85fe37:	6a 00                	push   0x0
  85fe39:	56                   	push   esi
  85fe3a:	ff d2                	call   edx
  85fe3c:	50                   	push   eax
  85fe3d:	8b 45 f4             	mov    eax,DWORD PTR [ebp-0xc]
  85fe40:	8b 08                	mov    ecx,DWORD PTR [eax]
  85fe42:	56                   	push   esi
  85fe43:	ff d1                	call   ecx
  85fe45:	8b 06                	mov    eax,DWORD PTR [esi]
  85fe47:	05 d0 00 00 00       	add    eax,0xd0
  85fe4c:	8d 8f 50 05 00 00    	lea    ecx,[edi+0x550]
  85fe52:	89 45 f4             	mov    DWORD PTR [ebp-0xc],eax
  85fe55:	e8 e6 fe fd ff       	call   0x83fd40
  85fe5a:	8b c8                	mov    ecx,eax
  85fe5c:	e8 8f 8f fd ff       	call   0x838df0
  85fe61:	8b 16                	mov    edx,DWORD PTR [esi]
  85fe63:	50                   	push   eax
  85fe64:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  85fe67:	68 d0 a5 b1 00       	push   0xb1a5d0
  85fe6c:	6a 00                	push   0x0
  85fe6e:	56                   	push   esi
  85fe6f:	ff d0                	call   eax
  85fe71:	8b 4d f4             	mov    ecx,DWORD PTR [ebp-0xc]
  85fe74:	8b 11                	mov    edx,DWORD PTR [ecx]
  85fe76:	50                   	push   eax
  85fe77:	56                   	push   esi
  85fe78:	ff d2                	call   edx
  85fe7a:	d9 ee                	fldz
  85fe7c:	d9 95 80 fe ff ff    	fst    DWORD PTR [ebp-0x180]
  85fe82:	d9 95 84 fe ff ff    	fst    DWORD PTR [ebp-0x17c]
  85fe88:	d9 95 88 fe ff ff    	fst    DWORD PTR [ebp-0x178]
  85fe8e:	d9 95 8c fe ff ff    	fst    DWORD PTR [ebp-0x174]
  85fe94:	d9 e8                	fld1
  85fe96:	d9 95 70 fe ff ff    	fst    DWORD PTR [ebp-0x190]
  85fe9c:	d9 9d 74 fe ff ff    	fstp   DWORD PTR [ebp-0x18c]
  85fea2:	d9 95 78 fe ff ff    	fst    DWORD PTR [ebp-0x188]
  85fea8:	d9 9d 7c fe ff ff    	fstp   DWORD PTR [ebp-0x184]
  85feae:	8b 06                	mov    eax,DWORD PTR [esi]
  85feb0:	8b 50 24             	mov    edx,DWORD PTR [eax+0x24]
  85feb3:	8d 8d 80 fe ff ff    	lea    ecx,[ebp-0x180]
  85feb9:	51                   	push   ecx
  85feba:	68 08 a6 b1 00       	push   0xb1a608
  85febf:	6a 00                	push   0x0
  85fec1:	56                   	push   esi
  85fec2:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85fec5:	ff d2                	call   edx
  85fec7:	50                   	push   eax
  85fec8:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  85fecb:	8b 88 88 00 00 00    	mov    ecx,DWORD PTR [eax+0x88]
  85fed1:	56                   	push   esi
  85fed2:	ff d1                	call   ecx
  85fed4:	8b 06                	mov    eax,DWORD PTR [esi]
  85fed6:	8d 95 70 fe ff ff    	lea    edx,[ebp-0x190]
  85fedc:	52                   	push   edx
  85fedd:	68 f8 a5 b1 00       	push   0xb1a5f8
  85fee2:	6a 00                	push   0x0
  85fee4:	89 45 f8             	mov    DWORD PTR [ebp-0x8],eax
  85fee7:	8b 40 24             	mov    eax,DWORD PTR [eax+0x24]
  85feea:	56                   	push   esi
  85feeb:	ff d0                	call   eax
  85feed:	8b 4d f8             	mov    ecx,DWORD PTR [ebp-0x8]
  85fef0:	8b 91 88 00 00 00    	mov    edx,DWORD PTR [ecx+0x88]
  85fef6:	50                   	push   eax
  85fef7:	56                   	push   esi
  85fef8:	ff d2                	call   edx
  85fefa:	8b 73 0c             	mov    esi,DWORD PTR [ebx+0xc]
  85fefd:	8b ce                	mov    ecx,esi
  85feff:	e8 bc 49 fe ff       	call   0x8448c0
  85ff04:	50                   	push   eax
  85ff05:	8b ce                	mov    ecx,esi
  85ff07:	e8 14 52 fe ff       	call   0x845120
  85ff0c:	50                   	push   eax
  85ff0d:	8d 85 10 fc ff ff    	lea    eax,[ebp-0x3f0]
  85ff13:	50                   	push   eax
  85ff14:	e8 65 da d1 ff       	call   0x57d97e
  85ff19:	8d 8d 10 fc ff ff    	lea    ecx,[ebp-0x3f0]
  85ff1f:	51                   	push   ecx
  85ff20:	8d b7 90 08 00 00    	lea    esi,[edi+0x890]
  85ff26:	56                   	push   esi
  85ff27:	8d 95 98 fc ff ff    	lea    edx,[ebp-0x368]
  85ff2d:	52                   	push   edx
  85ff2e:	e8 01 37 0c 00       	call   0x923634
  85ff33:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  85ff36:	8b 01                	mov    eax,DWORD PTR [ecx]
  85ff38:	8b 40 1c             	mov    eax,DWORD PTR [eax+0x1c]
  85ff3b:	8d 95 b0 fe ff ff    	lea    edx,[ebp-0x150]
  85ff41:	ff d0                	call   eax
  85ff43:	d9 85 b0 fe ff ff    	fld    DWORD PTR [ebp-0x150]
  85ff49:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  85ff4c:	d9 9f a0 08 00 00    	fstp   DWORD PTR [edi+0x8a0]
  85ff52:	d9 85 b4 fe ff ff    	fld    DWORD PTR [ebp-0x14c]
  85ff58:	8d 95 50 fc ff ff    	lea    edx,[ebp-0x3b0]
  85ff5e:	d9 9f a4 08 00 00    	fstp   DWORD PTR [edi+0x8a4]
  85ff64:	d9 85 b8 fe ff ff    	fld    DWORD PTR [ebp-0x148]
  85ff6a:	d9 9f a8 08 00 00    	fstp   DWORD PTR [edi+0x8a8]
  85ff70:	d9 85 bc fe ff ff    	fld    DWORD PTR [ebp-0x144]
  85ff76:	d9 9f ac 08 00 00    	fstp   DWORD PTR [edi+0x8ac]
  85ff7c:	8b 01                	mov    eax,DWORD PTR [ecx]
  85ff7e:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  85ff81:	ff d0                	call   eax
  85ff83:	d9 85 b0 fe ff ff    	fld    DWORD PTR [ebp-0x150]
  85ff89:	d9 1e                	fstp   DWORD PTR [esi]
  85ff8b:	d9 85 b4 fe ff ff    	fld    DWORD PTR [ebp-0x14c]
  85ff91:	d9 5e 04             	fstp   DWORD PTR [esi+0x4]
  85ff94:	d9 85 b8 fe ff ff    	fld    DWORD PTR [ebp-0x148]
  85ff9a:	d9 5e 08             	fstp   DWORD PTR [esi+0x8]
  85ff9d:	d9 85 bc fe ff ff    	fld    DWORD PTR [ebp-0x144]
  85ffa3:	d9 5e 0c             	fstp   DWORD PTR [esi+0xc]
  85ffa6:	d9 85 70 fc ff ff    	fld    DWORD PTR [ebp-0x390]
  85ffac:	dd 05 68 71 b0 00    	fld    QWORD PTR ds:0xb07168
  85ffb2:	dc c9                	fmul   st(1),st
  85ffb4:	d9 c9                	fxch   st(1)
  85ffb6:	d9 5d a0             	fstp   DWORD PTR [ebp-0x60]
  85ffb9:	d9 85 74 fc ff ff    	fld    DWORD PTR [ebp-0x38c]
  85ffbf:	d8 c9                	fmul   st,st(1)
  85ffc1:	d9 5d a4             	fstp   DWORD PTR [ebp-0x5c]
  85ffc4:	d9 85 78 fc ff ff    	fld    DWORD PTR [ebp-0x388]
  85ffca:	d8 c9                	fmul   st,st(1)
  85ffcc:	d9 5d a8             	fstp   DWORD PTR [ebp-0x58]
  85ffcf:	8d 4d a0             	lea    ecx,[ebp-0x60]
  85ffd2:	d9 ee                	fldz
  85ffd4:	51                   	push   ecx
  85ffd5:	de c9                	fmulp  st(1),st
  85ffd7:	8b ce                	mov    ecx,esi
  85ffd9:	d9 5d ac             	fstp   DWORD PTR [ebp-0x54]
  85ffdc:	e8 af 11 ba ff       	call   0x401190
  85ffe1:	83 c8 ff             	or     eax,0xffffffff
  85ffe4:	39 87 f4 07 00 00    	cmp    DWORD PTR [edi+0x7f4],eax
  85ffea:	75 6f                	jne    0x86005b
  85ffec:	39 87 f8 07 00 00    	cmp    DWORD PTR [edi+0x7f8],eax
  85fff2:	75 67                	jne    0x86005b
  85fff4:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  85fff7:	e8 c4 48 fe ff       	call   0x8448c0
  85fffc:	8b f0                	mov    esi,eax
  85fffe:	81 c7 74 07 00 00    	add    edi,0x774
  860004:	b9 10 00 00 00       	mov    ecx,0x10
  860009:	89 7d e4             	mov    DWORD PTR [ebp-0x1c],edi
  86000c:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86000e:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  860011:	8b 75 fc             	mov    esi,DWORD PTR [ebp-0x4]
  860014:	8b 01                	mov    eax,DWORD PTR [ecx]
  860016:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  860019:	8d 96 f4 06 00 00    	lea    edx,[esi+0x6f4]
  86001f:	89 55 f8             	mov    DWORD PTR [ebp-0x8],edx
  860022:	ff d0                	call   eax
  860024:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
  860027:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  86002a:	83 c0 ff             	add    eax,0xffffffff
  86002d:	89 86 f4 07 00 00    	mov    DWORD PTR [esi+0x7f4],eax
  860033:	8d be b4 07 00 00    	lea    edi,[esi+0x7b4]
  860039:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
  86003c:	b9 10 00 00 00       	mov    ecx,0x10
  860041:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  860043:	8b 75 f8             	mov    esi,DWORD PTR [ebp-0x8]
  860046:	8d ba 34 07 00 00    	lea    edi,[edx+0x734]
  86004c:	b9 10 00 00 00       	mov    ecx,0x10
  860051:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  860053:	89 82 f8 07 00 00    	mov    DWORD PTR [edx+0x7f8],eax
  860059:	8b fa                	mov    edi,edx
  86005b:	80 7b 14 00          	cmp    BYTE PTR [ebx+0x14],0x0
  86005f:	0f 85 ed 01 00 00    	jne    0x860252
  860065:	80 bf b1 08 00 00 00 	cmp    BYTE PTR [edi+0x8b1],0x0
  86006c:	74 18                	je     0x860086
  86006e:	8b 4b 10             	mov    ecx,DWORD PTR [ebx+0x10]
  860071:	2b 8f f4 07 00 00    	sub    ecx,DWORD PTR [edi+0x7f4]
  860077:	c6 87 b1 08 00 00 00 	mov    BYTE PTR [edi+0x8b1],0x0
  86007e:	01 8f f8 07 00 00    	add    DWORD PTR [edi+0x7f8],ecx
  860084:	eb 0c                	jmp    0x860092
  860086:	8b 97 f4 07 00 00    	mov    edx,DWORD PTR [edi+0x7f4]
  86008c:	89 97 f8 07 00 00    	mov    DWORD PTR [edi+0x7f8],edx
  860092:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  860095:	e8 26 48 fe ff       	call   0x8448c0
  86009a:	81 c7 74 07 00 00    	add    edi,0x774
  8600a0:	8b f0                	mov    esi,eax
  8600a2:	89 7d e4             	mov    DWORD PTR [ebp-0x1c],edi
  8600a5:	b9 10 00 00 00       	mov    ecx,0x10
  8600aa:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8600ac:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  8600af:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  8600b2:	8b 01                	mov    eax,DWORD PTR [ecx]
  8600b4:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  8600b7:	8d 97 f4 06 00 00    	lea    edx,[edi+0x6f4]
  8600bd:	89 55 f8             	mov    DWORD PTR [ebp-0x8],edx
  8600c0:	ff d0                	call   eax
  8600c2:	8b 4b 10             	mov    ecx,DWORD PTR [ebx+0x10]
  8600c5:	89 8f f4 07 00 00    	mov    DWORD PTR [edi+0x7f4],ecx
  8600cb:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  8600ce:	e8 ed 47 fe ff       	call   0x8448c0
  8600d3:	81 c7 b4 07 00 00    	add    edi,0x7b4
  8600d9:	8b f0                	mov    esi,eax
  8600db:	b9 10 00 00 00       	mov    ecx,0x10
  8600e0:	89 7d f4             	mov    DWORD PTR [ebp-0xc],edi
  8600e3:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8600e5:	8b 4d ec             	mov    ecx,DWORD PTR [ebp-0x14]
  8600e8:	8b 75 fc             	mov    esi,DWORD PTR [ebp-0x4]
  8600eb:	8b 01                	mov    eax,DWORD PTR [ecx]
  8600ed:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  8600f0:	8d 96 34 07 00 00    	lea    edx,[esi+0x734]
  8600f6:	89 55 d8             	mov    DWORD PTR [ebp-0x28],edx
  8600f9:	ff d0                	call   eax
  8600fb:	8b 43 20             	mov    eax,DWORD PTR [ebx+0x20]
  8600fe:	d9 e8                	fld1
  860100:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
  860103:	d9 95 48 ff ff ff    	fst    DWORD PTR [ebp-0xb8]
  860109:	89 96 f8 07 00 00    	mov    DWORD PTR [esi+0x7f8],edx
  86010f:	d9 ee                	fldz
  860111:	8d be 74 06 00 00    	lea    edi,[esi+0x674]
  860117:	d9 95 4c ff ff ff    	fst    DWORD PTR [ebp-0xb4]
  86011d:	b9 10 00 00 00       	mov    ecx,0x10
  860122:	d9 95 50 ff ff ff    	fst    DWORD PTR [ebp-0xb0]
  860128:	8d b5 48 ff ff ff    	lea    esi,[ebp-0xb8]
  86012e:	d9 95 54 ff ff ff    	fst    DWORD PTR [ebp-0xac]
  860134:	d9 95 58 ff ff ff    	fst    DWORD PTR [ebp-0xa8]
  86013a:	d9 95 60 ff ff ff    	fst    DWORD PTR [ebp-0xa0]
  860140:	d9 95 64 ff ff ff    	fst    DWORD PTR [ebp-0x9c]
  860146:	d9 95 68 ff ff ff    	fst    DWORD PTR [ebp-0x98]
  86014c:	d9 95 6c ff ff ff    	fst    DWORD PTR [ebp-0x94]
  860152:	d9 95 74 ff ff ff    	fst    DWORD PTR [ebp-0x8c]
  860158:	d9 c9                	fxch   st(1)
  86015a:	d9 95 5c ff ff ff    	fst    DWORD PTR [ebp-0xa4]
  860160:	d9 95 70 ff ff ff    	fst    DWORD PTR [ebp-0x90]
  860166:	d9 00                	fld    DWORD PTR [eax]
  860168:	d9 9d 78 ff ff ff    	fstp   DWORD PTR [ebp-0x88]
  86016e:	d9 40 04             	fld    DWORD PTR [eax+0x4]
  860171:	d9 9d 7c ff ff ff    	fstp   DWORD PTR [ebp-0x84]
  860177:	d9 40 08             	fld    DWORD PTR [eax+0x8]
  86017a:	d9 5d 80             	fstp   DWORD PTR [ebp-0x80]
  86017d:	8b 43 1c             	mov    eax,DWORD PTR [ebx+0x1c]
  860180:	d9 55 84             	fst    DWORD PTR [ebp-0x7c]
  860183:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  860185:	d9 95 48 ff ff ff    	fst    DWORD PTR [ebp-0xb8]
  86018b:	d9 95 5c ff ff ff    	fst    DWORD PTR [ebp-0xa4]
  860191:	d9 95 70 ff ff ff    	fst    DWORD PTR [ebp-0x90]
  860197:	d9 c9                	fxch   st(1)
  860199:	d9 95 4c ff ff ff    	fst    DWORD PTR [ebp-0xb4]
  86019f:	d9 95 50 ff ff ff    	fst    DWORD PTR [ebp-0xb0]
  8601a5:	d9 95 54 ff ff ff    	fst    DWORD PTR [ebp-0xac]
  8601ab:	d9 95 58 ff ff ff    	fst    DWORD PTR [ebp-0xa8]
  8601b1:	d9 95 60 ff ff ff    	fst    DWORD PTR [ebp-0xa0]
  8601b7:	d9 95 64 ff ff ff    	fst    DWORD PTR [ebp-0x9c]
  8601bd:	d9 95 68 ff ff ff    	fst    DWORD PTR [ebp-0x98]
  8601c3:	d9 95 6c ff ff ff    	fst    DWORD PTR [ebp-0x94]
  8601c9:	d9 9d 74 ff ff ff    	fstp   DWORD PTR [ebp-0x8c]
  8601cf:	d9 00                	fld    DWORD PTR [eax]
  8601d1:	d9 9d 78 ff ff ff    	fstp   DWORD PTR [ebp-0x88]
  8601d7:	d9 40 04             	fld    DWORD PTR [eax+0x4]
  8601da:	d9 9d 7c ff ff ff    	fstp   DWORD PTR [ebp-0x84]
  8601e0:	d9 40 08             	fld    DWORD PTR [eax+0x8]
  8601e3:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8601e6:	d9 5d 80             	fstp   DWORD PTR [ebp-0x80]
  8601e9:	d9 5d 84             	fstp   DWORD PTR [ebp-0x7c]
  8601ec:	8d b8 b4 06 00 00    	lea    edi,[eax+0x6b4]
  8601f2:	b9 10 00 00 00       	mov    ecx,0x10
  8601f7:	8d b5 48 ff ff ff    	lea    esi,[ebp-0xb8]
  8601fd:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8601ff:	8b 75 f8             	mov    esi,DWORD PTR [ebp-0x8]
  860202:	b9 10 00 00 00       	mov    ecx,0x10
  860207:	8d bd e8 fc ff ff    	lea    edi,[ebp-0x318]
  86020d:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86020f:	8b 75 d8             	mov    esi,DWORD PTR [ebp-0x28]
  860212:	b9 10 00 00 00       	mov    ecx,0x10
  860217:	8d bd 30 fe ff ff    	lea    edi,[ebp-0x1d0]
  86021d:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86021f:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
  860222:	b9 10 00 00 00       	mov    ecx,0x10
  860227:	8d bd 70 fd ff ff    	lea    edi,[ebp-0x290]
  86022d:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86022f:	8b 75 f4             	mov    esi,DWORD PTR [ebp-0xc]
  860232:	b9 10 00 00 00       	mov    ecx,0x10
  860237:	8d bd 48 ff ff ff    	lea    edi,[ebp-0xb8]
  86023d:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86023f:	8b 88 f4 07 00 00    	mov    ecx,DWORD PTR [eax+0x7f4]
  860245:	2b ca                	sub    ecx,edx
  860247:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  86024a:	db 45 ec             	fild   DWORD PTR [ebp-0x14]
  86024d:	e9 96 01 00 00       	jmp    0x8603e8
  860252:	80 bf b1 08 00 00 00 	cmp    BYTE PTR [edi+0x8b1],0x0
  860259:	75 73                	jne    0x8602ce
  86025b:	8d 87 fc 07 00 00    	lea    eax,[edi+0x7fc]
  860261:	50                   	push   eax
  860262:	c6 87 b1 08 00 00 01 	mov    BYTE PTR [edi+0x8b1],0x1
  860269:	8d b7 f4 06 00 00    	lea    esi,[edi+0x6f4]
  86026f:	6a 00                	push   0x0
  860271:	8b f8                	mov    edi,eax
  860273:	b9 10 00 00 00       	mov    ecx,0x10
  860278:	50                   	push   eax
  860279:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  86027c:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  86027e:	e8 f5 d6 d1 ff       	call   0x57d978
  860283:	8b 75 fc             	mov    esi,DWORD PTR [ebp-0x4]
  860286:	8b 45 ec             	mov    eax,DWORD PTR [ebp-0x14]
  860289:	8d 96 34 07 00 00    	lea    edx,[esi+0x734]
  86028f:	52                   	push   edx
  860290:	50                   	push   eax
  860291:	50                   	push   eax
  860292:	e8 e7 d6 d1 ff       	call   0x57d97e
  860297:	8d 86 3c 08 00 00    	lea    eax,[esi+0x83c]
  86029d:	50                   	push   eax
  86029e:	6a 00                	push   0x0
  8602a0:	8b f8                	mov    edi,eax
  8602a2:	81 c6 74 07 00 00    	add    esi,0x774
  8602a8:	b9 10 00 00 00       	mov    ecx,0x10
  8602ad:	50                   	push   eax
  8602ae:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  8602b1:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8602b3:	e8 c0 d6 d1 ff       	call   0x57d978
  8602b8:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  8602bb:	05 b4 07 00 00       	add    eax,0x7b4
  8602c0:	50                   	push   eax
  8602c1:	8b 45 ec             	mov    eax,DWORD PTR [ebp-0x14]
  8602c4:	50                   	push   eax
  8602c5:	50                   	push   eax
  8602c6:	e8 b3 d6 d1 ff       	call   0x57d97e
  8602cb:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  8602ce:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  8602d1:	e8 ea 45 fe ff       	call   0x8448c0
  8602d6:	81 c7 74 07 00 00    	add    edi,0x774
  8602dc:	8b f0                	mov    esi,eax
  8602de:	89 7d e4             	mov    DWORD PTR [ebp-0x1c],edi
  8602e1:	b9 10 00 00 00       	mov    ecx,0x10
  8602e6:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8602e8:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  8602eb:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  8602ee:	8b 01                	mov    eax,DWORD PTR [ecx]
  8602f0:	8b 40 20             	mov    eax,DWORD PTR [eax+0x20]
  8602f3:	8d b7 f4 06 00 00    	lea    esi,[edi+0x6f4]
  8602f9:	8b d6                	mov    edx,esi
  8602fb:	89 75 f8             	mov    DWORD PTR [ebp-0x8],esi
  8602fe:	ff d0                	call   eax
  860300:	80 7b 2c 00          	cmp    BYTE PTR [ebx+0x2c],0x0
  860304:	74 5f                	je     0x860365
  860306:	8d b7 74 06 00 00    	lea    esi,[edi+0x674]
  86030c:	b9 10 00 00 00       	mov    ecx,0x10
  860311:	8d bd 48 ff ff ff    	lea    edi,[ebp-0xb8]
  860317:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  860319:	8d 8d 48 ff ff ff    	lea    ecx,[ebp-0xb8]
  86031f:	51                   	push   ecx
  860320:	6a 00                	push   0x0
  860322:	8b d1                	mov    edx,ecx
  860324:	52                   	push   edx
  860325:	e8 4e d6 d1 ff       	call   0x57d978
  86032a:	8b 75 fc             	mov    esi,DWORD PTR [ebp-0x4]
  86032d:	8d 86 b4 06 00 00    	lea    eax,[esi+0x6b4]
  860333:	50                   	push   eax
  860334:	8d 8d 48 ff ff ff    	lea    ecx,[ebp-0xb8]
  86033a:	51                   	push   ecx
  86033b:	8b d1                	mov    edx,ecx
  86033d:	52                   	push   edx
  86033e:	e8 3b d6 d1 ff       	call   0x57d97e
  860343:	8b 55 f8             	mov    edx,DWORD PTR [ebp-0x8]
  860346:	8d 8d 48 ff ff ff    	lea    ecx,[ebp-0xb8]
  86034c:	51                   	push   ecx
  86034d:	8d 86 34 07 00 00    	lea    eax,[esi+0x734]
  860353:	52                   	push   edx
  860354:	50                   	push   eax
  860355:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  860358:	e8 21 d6 d1 ff       	call   0x57d97e
  86035d:	8b 75 f8             	mov    esi,DWORD PTR [ebp-0x8]
  860360:	8b 7d fc             	mov    edi,DWORD PTR [ebp-0x4]
  860363:	eb 17                	jmp    0x86037c
  860365:	8d 8f fc 07 00 00    	lea    ecx,[edi+0x7fc]
  86036b:	51                   	push   ecx
  86036c:	8d 87 34 07 00 00    	lea    eax,[edi+0x734]
  860372:	56                   	push   esi
  860373:	50                   	push   eax
  860374:	89 45 d8             	mov    DWORD PTR [ebp-0x28],eax
  860377:	e8 02 d6 d1 ff       	call   0x57d97e
  86037c:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
  86037f:	8d 87 b4 07 00 00    	lea    eax,[edi+0x7b4]
  860385:	81 c7 3c 08 00 00    	add    edi,0x83c
  86038b:	57                   	push   edi
  86038c:	52                   	push   edx
  86038d:	50                   	push   eax
  86038e:	89 45 f4             	mov    DWORD PTR [ebp-0xc],eax
  860391:	e8 e8 d5 d1 ff       	call   0x57d97e
  860396:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  860399:	b9 10 00 00 00       	mov    ecx,0x10
  86039e:	8d bd e8 fc ff ff    	lea    edi,[ebp-0x318]
  8603a4:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8603a6:	8b 75 d8             	mov    esi,DWORD PTR [ebp-0x28]
  8603a9:	b9 10 00 00 00       	mov    ecx,0x10
  8603ae:	8d bd 30 fe ff ff    	lea    edi,[ebp-0x1d0]
  8603b4:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8603b6:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
  8603b9:	b9 10 00 00 00       	mov    ecx,0x10
  8603be:	8d bd 70 fd ff ff    	lea    edi,[ebp-0x290]
  8603c4:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8603c6:	8b 75 f4             	mov    esi,DWORD PTR [ebp-0xc]
  8603c9:	b9 10 00 00 00       	mov    ecx,0x10
  8603ce:	8d bd 48 ff ff ff    	lea    edi,[ebp-0xb8]
  8603d4:	f3 a5                	rep movs DWORD PTR es:[edi],DWORD PTR ds:[esi]
  8603d6:	8b 88 f4 07 00 00    	mov    ecx,DWORD PTR [eax+0x7f4]
  8603dc:	2b 88 f8 07 00 00    	sub    ecx,DWORD PTR [eax+0x7f8]
  8603e2:	89 4d ec             	mov    DWORD PTR [ebp-0x14],ecx
  8603e5:	db 45 ec             	fild   DWORD PTR [ebp-0x14]
  8603e8:	85 c9                	test   ecx,ecx
  8603ea:	7d 06                	jge    0x8603f2
  8603ec:	dc 05 d8 56 ab 00    	fadd   QWORD PTR ds:0xab56d8
  8603f2:	dd 5d e8             	fstp   QWORD PTR [ebp-0x18]
  8603f5:	8d 55 90             	lea    edx,[ebp-0x70]
  8603f8:	d9 85 18 fd ff ff    	fld    DWORD PTR [ebp-0x2e8]
  8603fe:	52                   	push   edx
  8603ff:	dd 5d 90             	fstp   QWORD PTR [ebp-0x70]
  860402:	8d 85 e8 fe ff ff    	lea    eax,[ebp-0x118]
  860408:	d9 85 1c fd ff ff    	fld    DWORD PTR [ebp-0x2e4]
  86040e:	50                   	push   eax
  86040f:	dd 5d 98             	fstp   QWORD PTR [ebp-0x68]
  860412:	8d 8d c8 fe ff ff    	lea    ecx,[ebp-0x138]
  860418:	d9 85 20 fd ff ff    	fld    DWORD PTR [ebp-0x2e0]
  86041e:	51                   	push   ecx
  86041f:	dd 5d a0             	fstp   QWORD PTR [ebp-0x60]
  860422:	8d 55 b8             	lea    edx,[ebp-0x48]
  860425:	d9 85 24 fd ff ff    	fld    DWORD PTR [ebp-0x2dc]
  86042b:	52                   	push   edx
  86042c:	dd 5d a8             	fstp   QWORD PTR [ebp-0x58]
  86042f:	8d 8d a8 fc ff ff    	lea    ecx,[ebp-0x358]
  860435:	d9 85 08 fd ff ff    	fld    DWORD PTR [ebp-0x2f8]
  86043b:	dd 9d e8 fe ff ff    	fstp   QWORD PTR [ebp-0x118]
  860441:	d9 85 0c fd ff ff    	fld    DWORD PTR [ebp-0x2f4]
  860447:	dd 9d f0 fe ff ff    	fstp   QWORD PTR [ebp-0x110]
  86044d:	d9 85 10 fd ff ff    	fld    DWORD PTR [ebp-0x2f0]
  860453:	dd 9d f8 fe ff ff    	fstp   QWORD PTR [ebp-0x108]
  860459:	d9 85 14 fd ff ff    	fld    DWORD PTR [ebp-0x2ec]
  86045f:	dd 9d 00 ff ff ff    	fstp   QWORD PTR [ebp-0x100]
  860465:	d9 85 f8 fc ff ff    	fld    DWORD PTR [ebp-0x308]
  86046b:	dd 9d c8 fe ff ff    	fstp   QWORD PTR [ebp-0x138]
  860471:	d9 85 fc fc ff ff    	fld    DWORD PTR [ebp-0x304]
  860477:	dd 9d d0 fe ff ff    	fstp   QWORD PTR [ebp-0x130]
  86047d:	d9 85 00 fd ff ff    	fld    DWORD PTR [ebp-0x300]
  860483:	dd 9d d8 fe ff ff    	fstp   QWORD PTR [ebp-0x128]
  860489:	d9 85 04 fd ff ff    	fld    DWORD PTR [ebp-0x2fc]
  86048f:	dd 9d e0 fe ff ff    	fstp   QWORD PTR [ebp-0x120]
  860495:	d9 85 e8 fc ff ff    	fld    DWORD PTR [ebp-0x318]
  86049b:	dd 5d b8             	fstp   QWORD PTR [ebp-0x48]
  86049e:	d9 85 ec fc ff ff    	fld    DWORD PTR [ebp-0x314]
  8604a4:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  8604a7:	d9 85 f0 fc ff ff    	fld    DWORD PTR [ebp-0x310]
  8604ad:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  8604b0:	d9 85 f4 fc ff ff    	fld    DWORD PTR [ebp-0x30c]
  8604b6:	dd 5d d0             	fstp   QWORD PTR [ebp-0x30]
  8604b9:	e8 72 ec ff ff       	call   0x85f130
  8604be:	d9 85 60 fe ff ff    	fld    DWORD PTR [ebp-0x1a0]
  8604c4:	8d 45 b8             	lea    eax,[ebp-0x48]
  8604c7:	dd 5d b8             	fstp   QWORD PTR [ebp-0x48]
  8604ca:	50                   	push   eax
  8604cb:	d9 85 64 fe ff ff    	fld    DWORD PTR [ebp-0x19c]
  8604d1:	8d 8d c8 fe ff ff    	lea    ecx,[ebp-0x138]
  8604d7:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  8604da:	51                   	push   ecx
  8604db:	d9 85 68 fe ff ff    	fld    DWORD PTR [ebp-0x198]
  8604e1:	8d 95 e8 fe ff ff    	lea    edx,[ebp-0x118]
  8604e7:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  8604ea:	52                   	push   edx
  8604eb:	d9 85 6c fe ff ff    	fld    DWORD PTR [ebp-0x194]
  8604f1:	dd 5d d0             	fstp   QWORD PTR [ebp-0x30]
  8604f4:	d9 85 50 fe ff ff    	fld    DWORD PTR [ebp-0x1b0]
  8604fa:	dd 9d c8 fe ff ff    	fstp   QWORD PTR [ebp-0x138]
  860500:	d9 85 54 fe ff ff    	fld    DWORD PTR [ebp-0x1ac]
  860506:	dd 9d d0 fe ff ff    	fstp   QWORD PTR [ebp-0x130]
  86050c:	d9 85 58 fe ff ff    	fld    DWORD PTR [ebp-0x1a8]
  860512:	dd 9d d8 fe ff ff    	fstp   QWORD PTR [ebp-0x128]
  860518:	d9 85 5c fe ff ff    	fld    DWORD PTR [ebp-0x1a4]
  86051e:	dd 9d e0 fe ff ff    	fstp   QWORD PTR [ebp-0x120]
  860524:	d9 85 40 fe ff ff    	fld    DWORD PTR [ebp-0x1c0]
  86052a:	dd 9d e8 fe ff ff    	fstp   QWORD PTR [ebp-0x118]
  860530:	d9 85 44 fe ff ff    	fld    DWORD PTR [ebp-0x1bc]
  860536:	dd 9d f0 fe ff ff    	fstp   QWORD PTR [ebp-0x110]
  86053c:	d9 85 48 fe ff ff    	fld    DWORD PTR [ebp-0x1b8]
  860542:	dd 9d f8 fe ff ff    	fstp   QWORD PTR [ebp-0x108]
  860548:	d9 85 4c fe ff ff    	fld    DWORD PTR [ebp-0x1b4]
  86054e:	dd 9d 00 ff ff ff    	fstp   QWORD PTR [ebp-0x100]
  860554:	d9 85 30 fe ff ff    	fld    DWORD PTR [ebp-0x1d0]
  86055a:	dd 5d 90             	fstp   QWORD PTR [ebp-0x70]
  86055d:	d9 85 34 fe ff ff    	fld    DWORD PTR [ebp-0x1cc]
  860563:	dd 5d 98             	fstp   QWORD PTR [ebp-0x68]
  860566:	d9 85 38 fe ff ff    	fld    DWORD PTR [ebp-0x1c8]
  86056c:	dd 5d a0             	fstp   QWORD PTR [ebp-0x60]
  86056f:	d9 85 3c fe ff ff    	fld    DWORD PTR [ebp-0x1c4]
  860575:	dd 5d a8             	fstp   QWORD PTR [ebp-0x58]
  860578:	8d 45 90             	lea    eax,[ebp-0x70]
  86057b:	50                   	push   eax
  86057c:	8d 8d 10 fa ff ff    	lea    ecx,[ebp-0x5f0]
  860582:	e8 a9 eb ff ff       	call   0x85f130
  860587:	d9 85 a0 fd ff ff    	fld    DWORD PTR [ebp-0x260]
  86058d:	dd 5d b8             	fstp   QWORD PTR [ebp-0x48]
  860590:	8d 4d b8             	lea    ecx,[ebp-0x48]
  860593:	d9 85 a4 fd ff ff    	fld    DWORD PTR [ebp-0x25c]
  860599:	51                   	push   ecx
  86059a:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  86059d:	8d 95 c8 fe ff ff    	lea    edx,[ebp-0x138]
  8605a3:	d9 85 a8 fd ff ff    	fld    DWORD PTR [ebp-0x258]
  8605a9:	52                   	push   edx
  8605aa:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  8605ad:	8d 85 e8 fe ff ff    	lea    eax,[ebp-0x118]
  8605b3:	d9 85 ac fd ff ff    	fld    DWORD PTR [ebp-0x254]
  8605b9:	50                   	push   eax
  8605ba:	dd 5d d0             	fstp   QWORD PTR [ebp-0x30]
  8605bd:	8d 4d 90             	lea    ecx,[ebp-0x70]
  8605c0:	d9 85 90 fd ff ff    	fld    DWORD PTR [ebp-0x270]
  8605c6:	51                   	push   ecx
  8605c7:	dd 9d c8 fe ff ff    	fstp   QWORD PTR [ebp-0x138]
  8605cd:	8d 8d f0 fd ff ff    	lea    ecx,[ebp-0x210]
  8605d3:	d9 85 94 fd ff ff    	fld    DWORD PTR [ebp-0x26c]
  8605d9:	dd 9d d0 fe ff ff    	fstp   QWORD PTR [ebp-0x130]
  8605df:	d9 85 98 fd ff ff    	fld    DWORD PTR [ebp-0x268]
  8605e5:	dd 9d d8 fe ff ff    	fstp   QWORD PTR [ebp-0x128]
  8605eb:	d9 85 9c fd ff ff    	fld    DWORD PTR [ebp-0x264]
  8605f1:	dd 9d e0 fe ff ff    	fstp   QWORD PTR [ebp-0x120]
  8605f7:	d9 85 80 fd ff ff    	fld    DWORD PTR [ebp-0x280]
  8605fd:	dd 9d e8 fe ff ff    	fstp   QWORD PTR [ebp-0x118]
  860603:	d9 85 84 fd ff ff    	fld    DWORD PTR [ebp-0x27c]
  860609:	dd 9d f0 fe ff ff    	fstp   QWORD PTR [ebp-0x110]
  86060f:	d9 85 88 fd ff ff    	fld    DWORD PTR [ebp-0x278]
  860615:	dd 9d f8 fe ff ff    	fstp   QWORD PTR [ebp-0x108]
  86061b:	d9 85 8c fd ff ff    	fld    DWORD PTR [ebp-0x274]
  860621:	dd 9d 00 ff ff ff    	fstp   QWORD PTR [ebp-0x100]
  860627:	d9 85 70 fd ff ff    	fld    DWORD PTR [ebp-0x290]
  86062d:	dd 5d 90             	fstp   QWORD PTR [ebp-0x70]
  860630:	d9 85 74 fd ff ff    	fld    DWORD PTR [ebp-0x28c]
  860636:	dd 5d 98             	fstp   QWORD PTR [ebp-0x68]
  860639:	d9 85 78 fd ff ff    	fld    DWORD PTR [ebp-0x288]
  86063f:	dd 5d a0             	fstp   QWORD PTR [ebp-0x60]
  860642:	d9 85 7c fd ff ff    	fld    DWORD PTR [ebp-0x284]
  860648:	dd 5d a8             	fstp   QWORD PTR [ebp-0x58]
  86064b:	e8 e0 ea ff ff       	call   0x85f130
  860650:	d9 85 78 ff ff ff    	fld    DWORD PTR [ebp-0x88]
  860656:	8d 55 b8             	lea    edx,[ebp-0x48]
  860659:	dd 5d b8             	fstp   QWORD PTR [ebp-0x48]
  86065c:	52                   	push   edx
  86065d:	d9 85 7c ff ff ff    	fld    DWORD PTR [ebp-0x84]
  860663:	8d 85 c8 fe ff ff    	lea    eax,[ebp-0x138]
  860669:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  86066c:	d9 45 80             	fld    DWORD PTR [ebp-0x80]
  86066f:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  860672:	d9 45 84             	fld    DWORD PTR [ebp-0x7c]
  860675:	dd 5d d0             	fstp   QWORD PTR [ebp-0x30]
  860678:	d9 85 68 ff ff ff    	fld    DWORD PTR [ebp-0x98]
  86067e:	dd 9d c8 fe ff ff    	fstp   QWORD PTR [ebp-0x138]
  860684:	d9 85 6c ff ff ff    	fld    DWORD PTR [ebp-0x94]
  86068a:	dd 9d d0 fe ff ff    	fstp   QWORD PTR [ebp-0x130]
  860690:	d9 85 70 ff ff ff    	fld    DWORD PTR [ebp-0x90]
  860696:	dd 9d d8 fe ff ff    	fstp   QWORD PTR [ebp-0x128]
  86069c:	d9 85 74 ff ff ff    	fld    DWORD PTR [ebp-0x8c]
  8606a2:	dd 9d e0 fe ff ff    	fstp   QWORD PTR [ebp-0x120]
  8606a8:	d9 85 58 ff ff ff    	fld    DWORD PTR [ebp-0xa8]
  8606ae:	dd 9d e8 fe ff ff    	fstp   QWORD PTR [ebp-0x118]
  8606b4:	d9 85 5c ff ff ff    	fld    DWORD PTR [ebp-0xa4]
  8606ba:	dd 9d f0 fe ff ff    	fstp   QWORD PTR [ebp-0x110]
  8606c0:	d9 85 60 ff ff ff    	fld    DWORD PTR [ebp-0xa0]
  8606c6:	dd 9d f8 fe ff ff    	fstp   QWORD PTR [ebp-0x108]
  8606cc:	d9 85 64 ff ff ff    	fld    DWORD PTR [ebp-0x9c]
  8606d2:	dd 9d 00 ff ff ff    	fstp   QWORD PTR [ebp-0x100]
  8606d8:	d9 85 48 ff ff ff    	fld    DWORD PTR [ebp-0xb8]
  8606de:	dd 5d 90             	fstp   QWORD PTR [ebp-0x70]
  8606e1:	d9 85 4c ff ff ff    	fld    DWORD PTR [ebp-0xb4]
  8606e7:	dd 5d 98             	fstp   QWORD PTR [ebp-0x68]
  8606ea:	d9 85 50 ff ff ff    	fld    DWORD PTR [ebp-0xb0]
  8606f0:	dd 5d a0             	fstp   QWORD PTR [ebp-0x60]
  8606f3:	d9 85 54 ff ff ff    	fld    DWORD PTR [ebp-0xac]
  8606f9:	dd 5d a8             	fstp   QWORD PTR [ebp-0x58]
  8606fc:	50                   	push   eax
  8606fd:	8d 8d e8 fe ff ff    	lea    ecx,[ebp-0x118]
  860703:	51                   	push   ecx
  860704:	8d 55 90             	lea    edx,[ebp-0x70]
  860707:	52                   	push   edx
  860708:	8d 8d 90 f9 ff ff    	lea    ecx,[ebp-0x670]
  86070e:	e8 1d ea ff ff       	call   0x85f130
  860713:	8d 85 f0 fd ff ff    	lea    eax,[ebp-0x210]
  860719:	50                   	push   eax
  86071a:	8d 8d 90 fa ff ff    	lea    ecx,[ebp-0x570]
  860720:	e8 7b ea ff ff       	call   0x85f1a0
  860725:	8d 8d 90 fa ff ff    	lea    ecx,[ebp-0x570]
  86072b:	e8 b0 2c 20 00       	call   0xa633e0
  860730:	8d 8d a8 fc ff ff    	lea    ecx,[ebp-0x358]
  860736:	51                   	push   ecx
  860737:	8d 95 90 fa ff ff    	lea    edx,[ebp-0x570]
  86073d:	8d 8d 10 f9 ff ff    	lea    ecx,[ebp-0x6f0]
  860743:	e8 c8 ea ff ff       	call   0x85f210
  860748:	8d 95 a8 fc ff ff    	lea    edx,[ebp-0x358]
  86074e:	52                   	push   edx
  86074f:	8d 8d 10 fb ff ff    	lea    ecx,[ebp-0x4f0]
  860755:	e8 46 ea ff ff       	call   0x85f1a0
  86075a:	8d 8d 10 fb ff ff    	lea    ecx,[ebp-0x4f0]
  860760:	e8 1b 2e 20 00       	call   0xa63580
  860765:	8d 85 f0 fd ff ff    	lea    eax,[ebp-0x210]
  86076b:	50                   	push   eax
  86076c:	8d 95 10 fb ff ff    	lea    edx,[ebp-0x4f0]
  860772:	8d 8d 30 fd ff ff    	lea    ecx,[ebp-0x2d0]
  860778:	e8 93 ea ff ff       	call   0x85f210
  86077d:	8d 8d 10 fa ff ff    	lea    ecx,[ebp-0x5f0]
  860783:	51                   	push   ecx
  860784:	8d 8d 90 fb ff ff    	lea    ecx,[ebp-0x470]
  86078a:	e8 11 ea ff ff       	call   0x85f1a0
  86078f:	8d 8d 90 fb ff ff    	lea    ecx,[ebp-0x470]
  860795:	e8 e6 2d 20 00       	call   0xa63580
  86079a:	8d 95 90 f9 ff ff    	lea    edx,[ebp-0x670]
  8607a0:	52                   	push   edx
  8607a1:	8d 95 90 fb ff ff    	lea    edx,[ebp-0x470]
  8607a7:	8d 8d 08 ff ff ff    	lea    ecx,[ebp-0xf8]
  8607ad:	e8 5e ea ff ff       	call   0x85f210
  8607b2:	d9 ee                	fldz
  8607b4:	dd 45 e8             	fld    QWORD PTR [ebp-0x18]
  8607b7:	dd e1                	fucom  st(1)
  8607b9:	df e0                	fnstsw ax
  8607bb:	dd d9                	fstp   st(1)
  8607bd:	f6 c4 44             	test   ah,0x44
  8607c0:	d9 e8                	fld1
  8607c2:	7a 06                	jp     0x8607ca
  8607c4:	dd d9                	fstp   st(1)
  8607c6:	d9 c0                	fld    st(0)
  8607c8:	d9 c9                	fxch   st(1)
  8607ca:	dd 05 90 da b1 00    	fld    QWORD PTR ds:0xb1da90
  8607d0:	de f2                	fdivrp st(2),st
  8607d2:	d8 e1                	fsub   st,st(1)
  8607d4:	dd 85 08 ff ff ff    	fld    QWORD PTR [ebp-0xf8]
  8607da:	d8 ca                	fmul   st,st(2)
  8607dc:	dd 85 10 ff ff ff    	fld    QWORD PTR [ebp-0xf0]
  8607e2:	d8 cb                	fmul   st,st(3)
  8607e4:	dd 85 18 ff ff ff    	fld    QWORD PTR [ebp-0xe8]
  8607ea:	d8 cc                	fmul   st,st(4)
  8607ec:	dd 85 20 ff ff ff    	fld    QWORD PTR [ebp-0xe0]
  8607f2:	d8 cd                	fmul   st,st(5)
  8607f4:	dd 85 30 fd ff ff    	fld    QWORD PTR [ebp-0x2d0]
  8607fa:	d8 cd                	fmul   st,st(5)
  8607fc:	dd 85 38 fd ff ff    	fld    QWORD PTR [ebp-0x2c8]
  860802:	d8 ce                	fmul   st,st(6)
  860804:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  860807:	dd 85 40 fd ff ff    	fld    QWORD PTR [ebp-0x2c0]
  86080d:	d8 ce                	fmul   st,st(6)
  86080f:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  860812:	dd 85 48 fd ff ff    	fld    QWORD PTR [ebp-0x2b8]
  860818:	d8 ce                	fmul   st,st(6)
  86081a:	d9 c9                	fxch   st(1)
  86081c:	de c5                	faddp  st(5),st
  86081e:	dd 45 c0             	fld    QWORD PTR [ebp-0x40]
  860821:	de c4                	faddp  st(4),st
  860823:	dd 45 c8             	fld    QWORD PTR [ebp-0x38]
  860826:	de c3                	faddp  st(3),st
  860828:	de c1                	faddp  st(1),st
  86082a:	d9 cb                	fxch   st(3)
  86082c:	dd 9d f0 fd ff ff    	fstp   QWORD PTR [ebp-0x210]
  860832:	d9 c9                	fxch   st(1)
  860834:	dd 9d f8 fd ff ff    	fstp   QWORD PTR [ebp-0x208]
  86083a:	dd 9d 00 fe ff ff    	fstp   QWORD PTR [ebp-0x200]
  860840:	dd 9d 08 fe ff ff    	fstp   QWORD PTR [ebp-0x1f8]
  860846:	dd 85 28 ff ff ff    	fld    QWORD PTR [ebp-0xd8]
  86084c:	d8 ca                	fmul   st,st(2)
  86084e:	dd 85 30 ff ff ff    	fld    QWORD PTR [ebp-0xd0]
  860854:	d8 cb                	fmul   st,st(3)
  860856:	dd 85 38 ff ff ff    	fld    QWORD PTR [ebp-0xc8]
  86085c:	d8 cc                	fmul   st,st(4)
  86085e:	dd 85 40 ff ff ff    	fld    QWORD PTR [ebp-0xc0]
  860864:	d8 cd                	fmul   st,st(5)
  860866:	dd 85 50 fd ff ff    	fld    QWORD PTR [ebp-0x2b0]
  86086c:	d8 cd                	fmul   st,st(5)
  86086e:	dd 85 58 fd ff ff    	fld    QWORD PTR [ebp-0x2a8]
  860874:	d8 ce                	fmul   st,st(6)
  860876:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  860879:	dd 85 60 fd ff ff    	fld    QWORD PTR [ebp-0x2a0]
  86087f:	d8 ce                	fmul   st,st(6)
  860881:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  860884:	dd 85 68 fd ff ff    	fld    QWORD PTR [ebp-0x298]
  86088a:	d8 ce                	fmul   st,st(6)
  86088c:	d9 c9                	fxch   st(1)
  86088e:	de c5                	faddp  st(5),st
  860890:	dd 45 c0             	fld    QWORD PTR [ebp-0x40]
  860893:	de c4                	faddp  st(4),st
  860895:	dd 45 c8             	fld    QWORD PTR [ebp-0x38]
  860898:	de c3                	faddp  st(3),st
  86089a:	de c1                	faddp  st(1),st
  86089c:	d9 cb                	fxch   st(3)
  86089e:	dd 9d 10 fe ff ff    	fstp   QWORD PTR [ebp-0x1f0]
  8608a4:	d9 c9                	fxch   st(1)
  8608a6:	dd 9d 18 fe ff ff    	fstp   QWORD PTR [ebp-0x1e8]
  8608ac:	dd 9d 20 fe ff ff    	fstp   QWORD PTR [ebp-0x1e0]
  8608b2:	dd 9d 28 fe ff ff    	fstp   QWORD PTR [ebp-0x1d8]
  8608b8:	dd 85 48 ff ff ff    	fld    QWORD PTR [ebp-0xb8]
  8608be:	d8 ca                	fmul   st,st(2)
  8608c0:	dd 85 50 ff ff ff    	fld    QWORD PTR [ebp-0xb0]
  8608c6:	d8 cb                	fmul   st,st(3)
  8608c8:	dd 85 58 ff ff ff    	fld    QWORD PTR [ebp-0xa8]
  8608ce:	d8 cc                	fmul   st,st(4)
  8608d0:	dd 85 60 ff ff ff    	fld    QWORD PTR [ebp-0xa0]
  8608d6:	d8 cd                	fmul   st,st(5)
  8608d8:	dd 85 70 fd ff ff    	fld    QWORD PTR [ebp-0x290]
  8608de:	d8 cd                	fmul   st,st(5)
  8608e0:	dd 85 78 fd ff ff    	fld    QWORD PTR [ebp-0x288]
  8608e6:	d8 ce                	fmul   st,st(6)
  8608e8:	dd 5d c0             	fstp   QWORD PTR [ebp-0x40]
  8608eb:	dd 85 80 fd ff ff    	fld    QWORD PTR [ebp-0x280]
  8608f1:	d8 ce                	fmul   st,st(6)
  8608f3:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  8608f6:	dd 85 88 fd ff ff    	fld    QWORD PTR [ebp-0x278]
  8608fc:	8d 85 f0 fd ff ff    	lea    eax,[ebp-0x210]
  860902:	d8 ce                	fmul   st,st(6)
  860904:	50                   	push   eax
  860905:	d9 c9                	fxch   st(1)
  860907:	8d 95 10 f9 ff ff    	lea    edx,[ebp-0x6f0]
  86090d:	8d 8d 08 ff ff ff    	lea    ecx,[ebp-0xf8]
  860913:	de c5                	faddp  st(5),st
  860915:	dd 45 c0             	fld    QWORD PTR [ebp-0x40]
  860918:	de c4                	faddp  st(4),st
  86091a:	dd 45 c8             	fld    QWORD PTR [ebp-0x38]
  86091d:	de c3                	faddp  st(3),st
  86091f:	de c1                	faddp  st(1),st
  860921:	d9 cb                	fxch   st(3)
  860923:	dd 9d 30 fe ff ff    	fstp   QWORD PTR [ebp-0x1d0]
  860929:	d9 c9                	fxch   st(1)
  86092b:	dd 9d 38 fe ff ff    	fstp   QWORD PTR [ebp-0x1c8]
  860931:	dd 9d 40 fe ff ff    	fstp   QWORD PTR [ebp-0x1c0]
  860937:	dd 9d 48 fe ff ff    	fstp   QWORD PTR [ebp-0x1b8]
  86093d:	dd 85 68 ff ff ff    	fld    QWORD PTR [ebp-0x98]
  860943:	d8 ca                	fmul   st,st(2)
  860945:	dd 85 70 ff ff ff    	fld    QWORD PTR [ebp-0x90]
  86094b:	d8 cb                	fmul   st,st(3)
  86094d:	dd 85 78 ff ff ff    	fld    QWORD PTR [ebp-0x88]
  860953:	d8 cc                	fmul   st,st(4)
  860955:	dd 45 80             	fld    QWORD PTR [ebp-0x80]
  860958:	de cd                	fmulp  st(5),st
  86095a:	dd 85 90 fd ff ff    	fld    QWORD PTR [ebp-0x270]
  860960:	d8 cc                	fmul   st,st(4)
  860962:	dd 85 98 fd ff ff    	fld    QWORD PTR [ebp-0x268]
  860968:	d8 cd                	fmul   st,st(5)
  86096a:	dd 85 a0 fd ff ff    	fld    QWORD PTR [ebp-0x260]
  860970:	d8 ce                	fmul   st,st(6)
  860972:	dd 5d c8             	fstp   QWORD PTR [ebp-0x38]
  860975:	dd 85 a8 fd ff ff    	fld    QWORD PTR [ebp-0x258]
  86097b:	de ce                	fmulp  st(6),st
  86097d:	d9 c9                	fxch   st(1)
  86097f:	de c4                	faddp  st(4),st
  860981:	de c2                	faddp  st(2),st
  860983:	dc 45 c8             	fadd   QWORD PTR [ebp-0x38]
  860986:	d9 cb                	fxch   st(3)
  860988:	de c4                	faddp  st(4),st
  86098a:	d9 c9                	fxch   st(1)
  86098c:	dd 9d 50 fe ff ff    	fstp   QWORD PTR [ebp-0x1b0]
  860992:	dd 9d 58 fe ff ff    	fstp   QWORD PTR [ebp-0x1a8]
  860998:	dd 9d 60 fe ff ff    	fstp   QWORD PTR [ebp-0x1a0]
  86099e:	dd 9d 68 fe ff ff    	fstp   QWORD PTR [ebp-0x198]
  8609a4:	e8 67 e8 ff ff       	call   0x85f210
  8609a9:	dd 85 08 ff ff ff    	fld    QWORD PTR [ebp-0xf8]
  8609af:	8b 75 dc             	mov    esi,DWORD PTR [ebp-0x24]
  8609b2:	d9 9d b0 fd ff ff    	fstp   DWORD PTR [ebp-0x250]
  8609b8:	dd 85 10 ff ff ff    	fld    QWORD PTR [ebp-0xf0]
  8609be:	d9 9d b4 fd ff ff    	fstp   DWORD PTR [ebp-0x24c]
  8609c4:	dd 85 18 ff ff ff    	fld    QWORD PTR [ebp-0xe8]
  8609ca:	d9 9d b8 fd ff ff    	fstp   DWORD PTR [ebp-0x248]
  8609d0:	dd 85 20 ff ff ff    	fld    QWORD PTR [ebp-0xe0]
  8609d6:	d9 9d bc fd ff ff    	fstp   DWORD PTR [ebp-0x244]
  8609dc:	dd 85 28 ff ff ff    	fld    QWORD PTR [ebp-0xd8]
  8609e2:	d9 9d c0 fd ff ff    	fstp   DWORD PTR [ebp-0x240]
  8609e8:	dd 85 30 ff ff ff    	fld    QWORD PTR [ebp-0xd0]
  8609ee:	d9 9d c4 fd ff ff    	fstp   DWORD PTR [ebp-0x23c]
  8609f4:	dd 85 38 ff ff ff    	fld    QWORD PTR [ebp-0xc8]
  8609fa:	d9 9d c8 fd ff ff    	fstp   DWORD PTR [ebp-0x238]
  860a00:	dd 85 40 ff ff ff    	fld    QWORD PTR [ebp-0xc0]
  860a06:	d9 9d cc fd ff ff    	fstp   DWORD PTR [ebp-0x234]
  860a0c:	dd 85 48 ff ff ff    	fld    QWORD PTR [ebp-0xb8]
  860a12:	d9 9d d0 fd ff ff    	fstp   DWORD PTR [ebp-0x230]
  860a18:	dd 85 50 ff ff ff    	fld    QWORD PTR [ebp-0xb0]
  860a1e:	d9 9d d4 fd ff ff    	fstp   DWORD PTR [ebp-0x22c]
  860a24:	dd 85 58 ff ff ff    	fld    QWORD PTR [ebp-0xa8]
  860a2a:	d9 9d d8 fd ff ff    	fstp   DWORD PTR [ebp-0x228]
  860a30:	dd 85 60 ff ff ff    	fld    QWORD PTR [ebp-0xa0]
  860a36:	d9 9d dc fd ff ff    	fstp   DWORD PTR [ebp-0x224]
  860a3c:	dd 85 68 ff ff ff    	fld    QWORD PTR [ebp-0x98]
  860a42:	d9 9d e0 fd ff ff    	fstp   DWORD PTR [ebp-0x220]
  860a48:	dd 85 70 ff ff ff    	fld    QWORD PTR [ebp-0x90]
  860a4e:	d9 9d e4 fd ff ff    	fstp   DWORD PTR [ebp-0x21c]
  860a54:	dd 85 78 ff ff ff    	fld    QWORD PTR [ebp-0x88]
  860a5a:	d9 9d e8 fd ff ff    	fstp   DWORD PTR [ebp-0x218]
  860a60:	dd 45 80             	fld    QWORD PTR [ebp-0x80]
  860a63:	d9 9d ec fd ff ff    	fstp   DWORD PTR [ebp-0x214]
  860a69:	8b 3e                	mov    edi,DWORD PTR [esi]
  860a6b:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  860a6e:	8d 8d b0 fd ff ff    	lea    ecx,[ebp-0x250]
  860a74:	51                   	push   ecx
  860a75:	68 80 da b1 00       	push   0xb1da80
  860a7a:	6a 00                	push   0x0
  860a7c:	56                   	push   esi
  860a7d:	ff d2                	call   edx
  860a7f:	50                   	push   eax
  860a80:	8b 87 98 00 00 00    	mov    eax,DWORD PTR [edi+0x98]
  860a86:	56                   	push   esi
  860a87:	ff d0                	call   eax
  860a89:	8b 3e                	mov    edi,DWORD PTR [esi]
  860a8b:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  860a8e:	8d 8d d0 fd ff ff    	lea    ecx,[ebp-0x230]
  860a94:	51                   	push   ecx
  860a95:	68 68 da b1 00       	push   0xb1da68
  860a9a:	6a 00                	push   0x0
  860a9c:	56                   	push   esi
  860a9d:	ff d2                	call   edx
  860a9f:	50                   	push   eax
  860aa0:	8b 87 88 00 00 00    	mov    eax,DWORD PTR [edi+0x88]
  860aa6:	56                   	push   esi
  860aa7:	ff d0                	call   eax
  860aa9:	8b 7d e0             	mov    edi,DWORD PTR [ebp-0x20]
  860aac:	8b 17                	mov    edx,DWORD PTR [edi]
  860aae:	8b 42 14             	mov    eax,DWORD PTR [edx+0x14]
  860ab1:	8b cf                	mov    ecx,edi
  860ab3:	ff d0                	call   eax
  860ab5:	85 c0                	test   eax,eax
  860ab7:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
  860aba:	db 45 e0             	fild   DWORD PTR [ebp-0x20]
  860abd:	7d 06                	jge    0x860ac5
  860abf:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  860ac5:	8b 17                	mov    edx,DWORD PTR [edi]
  860ac7:	d9 5d e0             	fstp   DWORD PTR [ebp-0x20]
  860aca:	8b 42 18             	mov    eax,DWORD PTR [edx+0x18]
  860acd:	8b cf                	mov    ecx,edi
  860acf:	ff d0                	call   eax
  860ad1:	85 c0                	test   eax,eax
  860ad3:	89 45 dc             	mov    DWORD PTR [ebp-0x24],eax
  860ad6:	db 45 dc             	fild   DWORD PTR [ebp-0x24]
  860ad9:	7d 06                	jge    0x860ae1
  860adb:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  860ae1:	8b 17                	mov    edx,DWORD PTR [edi]
  860ae3:	d9 5d dc             	fstp   DWORD PTR [ebp-0x24]
  860ae6:	8b 42 14             	mov    eax,DWORD PTR [edx+0x14]
  860ae9:	8b cf                	mov    ecx,edi
  860aeb:	ff d0                	call   eax
  860aed:	85 c0                	test   eax,eax
  860aef:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  860af2:	db 45 ec             	fild   DWORD PTR [ebp-0x14]
  860af5:	7d 06                	jge    0x860afd
  860af7:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  860afd:	d9 e8                	fld1
  860aff:	8b 17                	mov    edx,DWORD PTR [edi]
  860b01:	de f1                	fdivrp st(1),st
  860b03:	8b 42 18             	mov    eax,DWORD PTR [edx+0x18]
  860b06:	8b cf                	mov    ecx,edi
  860b08:	d9 5d ec             	fstp   DWORD PTR [ebp-0x14]
  860b0b:	ff d0                	call   eax
  860b0d:	85 c0                	test   eax,eax
  860b0f:	89 45 f4             	mov    DWORD PTR [ebp-0xc],eax
  860b12:	db 45 f4             	fild   DWORD PTR [ebp-0xc]
  860b15:	7d 06                	jge    0x860b1d
  860b17:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  860b1d:	d9 e8                	fld1
  860b1f:	8d 8d 90 fe ff ff    	lea    ecx,[ebp-0x170]
  860b25:	de f1                	fdivrp st(1),st
  860b27:	51                   	push   ecx
  860b28:	68 50 da b1 00       	push   0xb1da50
  860b2d:	6a 00                	push   0x0
  860b2f:	56                   	push   esi
  860b30:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  860b33:	d9 45 e0             	fld    DWORD PTR [ebp-0x20]
  860b36:	d9 9d 90 fe ff ff    	fstp   DWORD PTR [ebp-0x170]
  860b3c:	d9 45 dc             	fld    DWORD PTR [ebp-0x24]
  860b3f:	d9 9d 94 fe ff ff    	fstp   DWORD PTR [ebp-0x16c]
  860b45:	d9 45 ec             	fld    DWORD PTR [ebp-0x14]
  860b48:	d9 9d 98 fe ff ff    	fstp   DWORD PTR [ebp-0x168]
  860b4e:	d9 45 f4             	fld    DWORD PTR [ebp-0xc]
  860b51:	d9 9d 9c fe ff ff    	fstp   DWORD PTR [ebp-0x164]
  860b57:	8b 3e                	mov    edi,DWORD PTR [esi]
  860b59:	8b 57 24             	mov    edx,DWORD PTR [edi+0x24]
  860b5c:	ff d2                	call   edx
  860b5e:	50                   	push   eax
  860b5f:	8b 87 88 00 00 00    	mov    eax,DWORD PTR [edi+0x88]
  860b65:	56                   	push   esi
  860b66:	ff d0                	call   eax
  860b68:	8b 0e                	mov    ecx,DWORD PTR [esi]
  860b6a:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  860b70:	6a 01                	push   0x1
  860b72:	8d 95 2c fd ff ff    	lea    edx,[ebp-0x2d4]
  860b78:	52                   	push   edx
  860b79:	56                   	push   esi
  860b7a:	ff d0                	call   eax
  860b7c:	8b 0e                	mov    ecx,DWORD PTR [esi]
  860b7e:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  860b84:	6a 00                	push   0x0
  860b86:	56                   	push   esi
  860b87:	ff d2                	call   edx
  860b89:	8b 06                	mov    eax,DWORD PTR [esi]
  860b8b:	8b 88 04 01 00 00    	mov    ecx,DWORD PTR [eax+0x104]
  860b91:	56                   	push   esi
  860b92:	ff d1                	call   ecx
  860b94:	8b 85 a8 fe ff ff    	mov    eax,DWORD PTR [ebp-0x158]
  860b9a:	8b 10                	mov    edx,DWORD PTR [eax]
  860b9c:	6a 02                	push   0x2
  860b9e:	6a 00                	push   0x0
  860ba0:	6a 04                	push   0x4
  860ba2:	6a 00                	push   0x0
  860ba4:	6a 00                	push   0x0
  860ba6:	6a 05                	push   0x5
  860ba8:	50                   	push   eax
  860ba9:	8b 82 48 01 00 00    	mov    eax,DWORD PTR [edx+0x148]
  860baf:	ff d0                	call   eax
  860bb1:	8b 0e                	mov    ecx,DWORD PTR [esi]
  860bb3:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  860bb9:	56                   	push   esi
  860bba:	ff d2                	call   edx
  860bbc:	8b 06                	mov    eax,DWORD PTR [esi]
  860bbe:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  860bc4:	56                   	push   esi
  860bc5:	ff d1                	call   ecx
  860bc7:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  860bcd:	8b 01                	mov    eax,DWORD PTR [ecx]
  860bcf:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  860bd5:	33 d2                	xor    edx,edx
  860bd7:	ff d0                	call   eax
  860bd9:	8b c8                	mov    ecx,eax
  860bdb:	e8 70 27 ff ff       	call   0x853350
  860be0:	5f                   	pop    edi
  860be1:	b0 01                	mov    al,0x1
  860be3:	5e                   	pop    esi
  860be4:	8b e5                	mov    esp,ebp
  860be6:	5d                   	pop    ebp
  860be7:	8b e3                	mov    esp,ebx
  860be9:	5b                   	pop    ebx
  860bea:	c2 28 00             	ret    0x28
```

### `0x00860e60..0x008614b3` — sites `0x00861372`

```asm
  860e60:	55                   	push   ebp
  860e61:	8b ec                	mov    ebp,esp
  860e63:	83 ec 38             	sub    esp,0x38
  860e66:	53                   	push   ebx
  860e67:	8b d9                	mov    ebx,ecx
  860e69:	83 bb 38 05 00 00 00 	cmp    DWORD PTR [ebx+0x538],0x0
  860e70:	89 55 f0             	mov    DWORD PTR [ebp-0x10],edx
  860e73:	89 5d fc             	mov    DWORD PTR [ebp-0x4],ebx
  860e76:	0f 84 46 05 00 00    	je     0x8613c2
  860e7c:	83 bb 34 05 00 00 00 	cmp    DWORD PTR [ebx+0x534],0x0
  860e83:	0f 84 39 05 00 00    	je     0x8613c2
  860e89:	85 d2                	test   edx,edx
  860e8b:	75 0e                	jne    0x860e9b
  860e8d:	39 55 08             	cmp    DWORD PTR [ebp+0x8],edx
  860e90:	75 09                	jne    0x860e9b
  860e92:	b0 01                	mov    al,0x1
  860e94:	5b                   	pop    ebx
  860e95:	8b e5                	mov    esp,ebp
  860e97:	5d                   	pop    ebp
  860e98:	c2 08 00             	ret    0x8
  860e9b:	56                   	push   esi
  860e9c:	8b 35 58 60 c2 00    	mov    esi,DWORD PTR ds:0xc26058
  860ea2:	57                   	push   edi
  860ea3:	8b ce                	mov    ecx,esi
  860ea5:	e8 66 d2 fc ff       	call   0x82e110
  860eaa:	8b f8                	mov    edi,eax
  860eac:	8b 07                	mov    eax,DWORD PTR [edi]
  860eae:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  860eb4:	6a 00                	push   0x0
  860eb6:	68 c2 00 00 00       	push   0xc2
  860ebb:	57                   	push   edi
  860ebc:	ff d1                	call   ecx
  860ebe:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  860ec1:	8b 55 08             	mov    edx,DWORD PTR [ebp+0x8]
  860ec4:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  860ec7:	51                   	push   ecx
  860ec8:	d9 1c 24             	fstp   DWORD PTR [esp]
  860ecb:	52                   	push   edx
  860ecc:	50                   	push   eax
  860ecd:	8b cb                	mov    ecx,ebx
  860ecf:	e8 7c e1 ff ff       	call   0x85f050
  860ed4:	84 c0                	test   al,al
  860ed6:	74 4a                	je     0x860f22
  860ed8:	8b 16                	mov    edx,DWORD PTR [esi]
  860eda:	8b 82 1c 01 00 00    	mov    eax,DWORD PTR [edx+0x11c]
  860ee0:	8d 4d e8             	lea    ecx,[ebp-0x18]
  860ee3:	51                   	push   ecx
  860ee4:	8b ce                	mov    ecx,esi
  860ee6:	ff d0                	call   eax
  860ee8:	33 d2                	xor    edx,edx
  860eea:	8b c8                	mov    ecx,eax
  860eec:	e8 df 20 ff ff       	call   0x852fd0
  860ef1:	8d 4d 0c             	lea    ecx,[ebp+0xc]
  860ef4:	51                   	push   ecx
  860ef5:	8b 8b 38 05 00 00    	mov    ecx,DWORD PTR [ebx+0x538]
  860efb:	33 d2                	xor    edx,edx
  860efd:	e8 ce 20 ff ff       	call   0x852fd0
  860f02:	8b ce                	mov    ecx,esi
  860f04:	e8 07 d2 fc ff       	call   0x82e110
  860f09:	8b 4d 0c             	mov    ecx,DWORD PTR [ebp+0xc]
  860f0c:	8b 10                	mov    edx,DWORD PTR [eax]
  860f0e:	8b 92 88 00 00 00    	mov    edx,DWORD PTR [edx+0x88]
  860f14:	6a 00                	push   0x0
  860f16:	6a 00                	push   0x0
  860f18:	51                   	push   ecx
  860f19:	8b 4d e8             	mov    ecx,DWORD PTR [ebp-0x18]
  860f1c:	6a 00                	push   0x0
  860f1e:	51                   	push   ecx
  860f1f:	50                   	push   eax
  860f20:	ff d2                	call   edx
  860f22:	d9 e8                	fld1
  860f24:	c7 45 f8 02 00 00 00 	mov    DWORD PTR [ebp-0x8],0x2
  860f2b:	d8 9b 2c 05 00 00    	fcomp  DWORD PTR [ebx+0x52c]
  860f31:	df e0                	fnstsw ax
  860f33:	f6 c4 41             	test   ah,0x41
  860f36:	74 07                	je     0x860f3f
  860f38:	c7 45 f8 01 00 00 00 	mov    DWORD PTR [ebp-0x8],0x1
  860f3f:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  860f42:	33 db                	xor    ebx,ebx
  860f44:	85 c0                	test   eax,eax
  860f46:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  860f49:	0f 86 4f 04 00 00    	jbe    0x86139e
  860f4f:	90                   	nop
  860f50:	85 db                	test   ebx,ebx
  860f52:	75 08                	jne    0x860f5c
  860f54:	83 f8 02             	cmp    eax,0x2
  860f57:	8b 45 f0             	mov    eax,DWORD PTR [ebp-0x10]
  860f5a:	74 03                	je     0x860f5f
  860f5c:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  860f5f:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  860f62:	8b 91 34 05 00 00    	mov    edx,DWORD PTR [ecx+0x534]
  860f68:	8d 04 80             	lea    eax,[eax+eax*4]
  860f6b:	03 c0                	add    eax,eax
  860f6d:	03 c0                	add    eax,eax
  860f6f:	03 c0                	add    eax,eax
  860f71:	8b 74 10 04          	mov    esi,DWORD PTR [eax+edx*1+0x4]
  860f75:	85 f6                	test   esi,esi
  860f77:	89 45 ec             	mov    DWORD PTR [ebp-0x14],eax
  860f7a:	0f 84 0d 04 00 00    	je     0x86138d
  860f80:	e8 cb b0 fc ff       	call   0x82c050
  860f85:	8b c8                	mov    ecx,eax
  860f87:	e8 d4 96 fc ff       	call   0x82a660
  860f8c:	e8 1f b1 fc ff       	call   0x82c0b0
  860f91:	8b 06                	mov    eax,DWORD PTR [esi]
  860f93:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  860f96:	68 e8 db b1 00       	push   0xb1dbe8
  860f9b:	6a 00                	push   0x0
  860f9d:	56                   	push   esi
  860f9e:	ff d1                	call   ecx
  860fa0:	85 c0                	test   eax,eax
  860fa2:	0f 95 c0             	setne  al
  860fa5:	84 c0                	test   al,al
  860fa7:	74 08                	je     0x860fb1
  860fa9:	85 db                	test   ebx,ebx
  860fab:	0f 84 dc 03 00 00    	je     0x86138d
  860fb1:	8b 1e                	mov    ebx,DWORD PTR [esi]
  860fb3:	8b 53 34             	mov    edx,DWORD PTR [ebx+0x34]
  860fb6:	68 d0 db b1 00       	push   0xb1dbd0
  860fbb:	56                   	push   esi
  860fbc:	ff d2                	call   edx
  860fbe:	50                   	push   eax
  860fbf:	8b 83 e8 00 00 00    	mov    eax,DWORD PTR [ebx+0xe8]
  860fc5:	56                   	push   esi
  860fc6:	ff d0                	call   eax
  860fc8:	8b 5d fc             	mov    ebx,DWORD PTR [ebp-0x4]
  860fcb:	8b 93 c4 00 00 00    	mov    edx,DWORD PTR [ebx+0xc4]
  860fd1:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  860fd7:	e8 34 d5 fc ff       	call   0x82e510
  860fdc:	8b 93 20 05 00 00    	mov    edx,DWORD PTR [ebx+0x520]
  860fe2:	8b 0f                	mov    ecx,DWORD PTR [edi]
  860fe4:	8b 81 90 01 00 00    	mov    eax,DWORD PTR [ecx+0x190]
  860fea:	6a 14                	push   0x14
  860fec:	6a 00                	push   0x0
  860fee:	52                   	push   edx
  860fef:	6a 00                	push   0x0
  860ff1:	57                   	push   edi
  860ff2:	ff d0                	call   eax
  860ff4:	8b 93 cc 00 00 00    	mov    edx,DWORD PTR [ebx+0xcc]
  860ffa:	8b 0f                	mov    ecx,DWORD PTR [edi]
  860ffc:	8b 81 a0 01 00 00    	mov    eax,DWORD PTR [ecx+0x1a0]
  861002:	52                   	push   edx
  861003:	57                   	push   edi
  861004:	ff d0                	call   eax
  861006:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  861009:	8b 89 38 05 00 00    	mov    ecx,DWORD PTR [ecx+0x538]
  86100f:	8b 01                	mov    eax,DWORD PTR [ecx]
  861011:	8b 1e                	mov    ebx,DWORD PTR [esi]
  861013:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
  861016:	33 d2                	xor    edx,edx
  861018:	81 c3 d0 00 00 00    	add    ebx,0xd0
  86101e:	ff d0                	call   eax
  861020:	8b c8                	mov    ecx,eax
  861022:	e8 c9 7d fd ff       	call   0x838df0
  861027:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861029:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  86102c:	50                   	push   eax
  86102d:	68 c0 db b1 00       	push   0xb1dbc0
  861032:	6a 00                	push   0x0
  861034:	56                   	push   esi
  861035:	ff d2                	call   edx
  861037:	50                   	push   eax
  861038:	8b 03                	mov    eax,DWORD PTR [ebx]
  86103a:	56                   	push   esi
  86103b:	ff d0                	call   eax
  86103d:	8b 0e                	mov    ecx,DWORD PTR [esi]
  86103f:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  861042:	68 a8 db b1 00       	push   0xb1dba8
  861047:	6a 00                	push   0x0
  861049:	56                   	push   esi
  86104a:	ff d2                	call   edx
  86104c:	8b d8                	mov    ebx,eax
  86104e:	85 db                	test   ebx,ebx
  861050:	74 56                	je     0x8610a8
  861052:	8b 45 fc             	mov    eax,DWORD PTR [ebp-0x4]
  861055:	8b 88 38 05 00 00    	mov    ecx,DWORD PTR [eax+0x538]
  86105b:	8b 11                	mov    edx,DWORD PTR [ecx]
  86105d:	8b 42 04             	mov    eax,DWORD PTR [edx+0x4]
  861060:	ff d0                	call   eax
  861062:	85 c0                	test   eax,eax
  861064:	89 45 0c             	mov    DWORD PTR [ebp+0xc],eax
  861067:	db 45 0c             	fild   DWORD PTR [ebp+0xc]
  86106a:	7d 06                	jge    0x861072
  86106c:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  861072:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  861075:	d9 5d c8             	fstp   DWORD PTR [ebp-0x38]
  861078:	8b 89 38 05 00 00    	mov    ecx,DWORD PTR [ecx+0x538]
  86107e:	8b 11                	mov    edx,DWORD PTR [ecx]
  861080:	8b 42 08             	mov    eax,DWORD PTR [edx+0x8]
  861083:	ff d0                	call   eax
  861085:	85 c0                	test   eax,eax
  861087:	89 45 0c             	mov    DWORD PTR [ebp+0xc],eax
  86108a:	db 45 0c             	fild   DWORD PTR [ebp+0xc]
  86108d:	7d 06                	jge    0x861095
  86108f:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  861095:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861097:	d9 5d cc             	fstp   DWORD PTR [ebp-0x34]
  86109a:	8b 81 88 00 00 00    	mov    eax,DWORD PTR [ecx+0x88]
  8610a0:	8d 55 c8             	lea    edx,[ebp-0x38]
  8610a3:	52                   	push   edx
  8610a4:	53                   	push   ebx
  8610a5:	56                   	push   esi
  8610a6:	ff d0                	call   eax
  8610a8:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8610ae:	8b 16                	mov    edx,DWORD PTR [esi]
  8610b0:	d9 81 08 07 00 00    	fld    DWORD PTR [ecx+0x708]
  8610b6:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  8610b9:	d9 5d 0c             	fstp   DWORD PTR [ebp+0xc]
  8610bc:	68 9c db b1 00       	push   0xb1db9c
  8610c1:	6a 00                	push   0x0
  8610c3:	56                   	push   esi
  8610c4:	ff d0                	call   eax
  8610c6:	85 c0                	test   eax,eax
  8610c8:	74 10                	je     0x8610da
  8610ca:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8610cc:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  8610cf:	8b 51 78             	mov    edx,DWORD PTR [ecx+0x78]
  8610d2:	51                   	push   ecx
  8610d3:	d9 1c 24             	fstp   DWORD PTR [esp]
  8610d6:	50                   	push   eax
  8610d7:	56                   	push   esi
  8610d8:	ff d2                	call   edx
  8610da:	8b 06                	mov    eax,DWORD PTR [esi]
  8610dc:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  8610df:	68 90 db b1 00       	push   0xb1db90
  8610e4:	6a 00                	push   0x0
  8610e6:	56                   	push   esi
  8610e7:	ff d1                	call   ecx
  8610e9:	8b c8                	mov    ecx,eax
  8610eb:	85 c9                	test   ecx,ecx
  8610ed:	74 44                	je     0x861133
  8610ef:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  8610f2:	d9 7d 0e             	fnstcw WORD PTR [ebp+0xe]
  8610f5:	0f b7 45 0e          	movzx  eax,WORD PTR [ebp+0xe]
  8610f9:	0d 00 0c 00 00       	or     eax,0xc00
  8610fe:	d9 c0                	fld    st(0)
  861100:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
  861103:	d9 c9                	fxch   st(1)
  861105:	d9 6d e4             	fldcw  WORD PTR [ebp-0x1c]
  861108:	df 7d e0             	fistp  QWORD PTR [ebp-0x20]
  86110b:	8b 55 e0             	mov    edx,DWORD PTR [ebp-0x20]
  86110e:	85 d2                	test   edx,edx
  861110:	d9 6d 0e             	fldcw  WORD PTR [ebp+0xe]
  861113:	db 45 e0             	fild   DWORD PTR [ebp-0x20]
  861116:	7d 06                	jge    0x86111e
  861118:	d8 05 18 ad aa 00    	fadd   DWORD PTR ds:0xaaad18
  86111e:	8b 06                	mov    eax,DWORD PTR [esi]
  861120:	de e9                	fsubp  st(1),st
  861122:	51                   	push   ecx
  861123:	d9 5d 0c             	fstp   DWORD PTR [ebp+0xc]
  861126:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  861129:	d9 1c 24             	fstp   DWORD PTR [esp]
  86112c:	51                   	push   ecx
  86112d:	8b 48 78             	mov    ecx,DWORD PTR [eax+0x78]
  861130:	56                   	push   esi
  861131:	ff d1                	call   ecx
  861133:	8b 16                	mov    edx,DWORD PTR [esi]
  861135:	8b 42 24             	mov    eax,DWORD PTR [edx+0x24]
  861138:	68 e8 d9 b1 00       	push   0xb1d9e8
  86113d:	6a 00                	push   0x0
  86113f:	56                   	push   esi
  861140:	ff d0                	call   eax
  861142:	85 c0                	test   eax,eax
  861144:	0f 95 c3             	setne  bl
  861147:	83 7d f4 00          	cmp    DWORD PTR [ebp-0xc],0x0
  86114b:	75 7e                	jne    0x8611cb
  86114d:	8b 0f                	mov    ecx,DWORD PTR [edi]
  86114f:	8b 81 e4 00 00 00    	mov    eax,DWORD PTR [ecx+0xe4]
  861155:	33 d2                	xor    edx,edx
  861157:	84 db                	test   bl,bl
  861159:	0f 95 c2             	setne  dl
  86115c:	52                   	push   edx
  86115d:	6a 1b                	push   0x1b
  86115f:	57                   	push   edi
  861160:	ff d0                	call   eax
  861162:	8b 0f                	mov    ecx,DWORD PTR [edi]
  861164:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  86116a:	6a 00                	push   0x0
  86116c:	68 ce 00 00 00       	push   0xce
  861171:	57                   	push   edi
  861172:	ff d2                	call   edx
  861174:	8b 06                	mov    eax,DWORD PTR [esi]
  861176:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  861179:	68 80 db b1 00       	push   0xb1db80
  86117e:	6a 00                	push   0x0
  861180:	56                   	push   esi
  861181:	ff d1                	call   ecx
  861183:	85 c0                	test   eax,eax
  861185:	0f 84 ba 00 00 00    	je     0x861245
  86118b:	84 db                	test   bl,bl
  86118d:	74 2b                	je     0x8611ba
  86118f:	83 7d f8 01          	cmp    DWORD PTR [ebp-0x8],0x1
  861193:	76 25                	jbe    0x8611ba
  861195:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  861198:	d9 81 2c 05 00 00    	fld    DWORD PTR [ecx+0x52c]
  86119e:	8b 16                	mov    edx,DWORD PTR [esi]
  8611a0:	d9 e8                	fld1
  8611a2:	8b 52 78             	mov    edx,DWORD PTR [edx+0x78]
  8611a5:	de e1                	fsubrp st(1),st
  8611a7:	51                   	push   ecx
  8611a8:	d9 5d 0c             	fstp   DWORD PTR [ebp+0xc]
  8611ab:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  8611ae:	d9 1c 24             	fstp   DWORD PTR [esp]
  8611b1:	50                   	push   eax
  8611b2:	56                   	push   esi
  8611b3:	ff d2                	call   edx
  8611b5:	e9 8b 00 00 00       	jmp    0x861245
  8611ba:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8611bc:	d9 e8                	fld1
  8611be:	8b 51 78             	mov    edx,DWORD PTR [ecx+0x78]
  8611c1:	51                   	push   ecx
  8611c2:	d9 1c 24             	fstp   DWORD PTR [esp]
  8611c5:	50                   	push   eax
  8611c6:	56                   	push   esi
  8611c7:	ff d2                	call   edx
  8611c9:	eb 7a                	jmp    0x861245
  8611cb:	8b 07                	mov    eax,DWORD PTR [edi]
  8611cd:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  8611d3:	6a 01                	push   0x1
  8611d5:	6a 1b                	push   0x1b
  8611d7:	57                   	push   edi
  8611d8:	ff d1                	call   ecx
  8611da:	8b 17                	mov    edx,DWORD PTR [edi]
  8611dc:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  8611e2:	6a 01                	push   0x1
  8611e4:	68 ab 00 00 00       	push   0xab
  8611e9:	57                   	push   edi
  8611ea:	ff d0                	call   eax
  8611ec:	8b 0f                	mov    ecx,DWORD PTR [edi]
  8611ee:	8b 91 e4 00 00 00    	mov    edx,DWORD PTR [ecx+0xe4]
  8611f4:	6a 05                	push   0x5
  8611f6:	6a 13                	push   0x13
  8611f8:	57                   	push   edi
  8611f9:	ff d2                	call   edx
  8611fb:	8b 07                	mov    eax,DWORD PTR [edi]
  8611fd:	8b 88 e4 00 00 00    	mov    ecx,DWORD PTR [eax+0xe4]
  861203:	6a 06                	push   0x6
  861205:	6a 14                	push   0x14
  861207:	57                   	push   edi
  861208:	ff d1                	call   ecx
  86120a:	8b 17                	mov    edx,DWORD PTR [edi]
  86120c:	8b 82 e4 00 00 00    	mov    eax,DWORD PTR [edx+0xe4]
  861212:	6a 00                	push   0x0
  861214:	68 ce 00 00 00       	push   0xce
  861219:	57                   	push   edi
  86121a:	ff d0                	call   eax
  86121c:	8b 0e                	mov    ecx,DWORD PTR [esi]
  86121e:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  861221:	68 80 db b1 00       	push   0xb1db80
  861226:	6a 00                	push   0x0
  861228:	56                   	push   esi
  861229:	ff d2                	call   edx
  86122b:	85 c0                	test   eax,eax
  86122d:	74 16                	je     0x861245
  86122f:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861231:	8b 55 fc             	mov    edx,DWORD PTR [ebp-0x4]
  861234:	d9 82 2c 05 00 00    	fld    DWORD PTR [edx+0x52c]
  86123a:	51                   	push   ecx
  86123b:	d9 1c 24             	fstp   DWORD PTR [esp]
  86123e:	50                   	push   eax
  86123f:	8b 41 78             	mov    eax,DWORD PTR [ecx+0x78]
  861242:	56                   	push   esi
  861243:	ff d0                	call   eax
  861245:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  861248:	8b 91 34 05 00 00    	mov    edx,DWORD PTR [ecx+0x534]
  86124e:	8b 45 ec             	mov    eax,DWORD PTR [ebp-0x14]
  861251:	8d 5c 10 08          	lea    ebx,[eax+edx*1+0x8]
  861255:	8d 55 e8             	lea    edx,[ebp-0x18]
  861258:	8b cb                	mov    ecx,ebx
  86125a:	e8 21 c9 e1 ff       	call   0x67db80
  86125f:	8d 55 dc             	lea    edx,[ebp-0x24]
  861262:	8b cb                	mov    ecx,ebx
  861264:	e8 47 4c c9 ff       	call   0x4f5eb0
  861269:	8b 5d e8             	mov    ebx,DWORD PTR [ebp-0x18]
  86126c:	3b 18                	cmp    ebx,DWORD PTR [eax]
  86126e:	0f 95 c0             	setne  al
  861271:	84 c0                	test   al,al
  861273:	0f 84 bb 00 00 00    	je     0x861334
  861279:	8d a4 24 00 00 00 00 	lea    esp,[esp+0x0]
  861280:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
  861283:	8b 00                	mov    eax,DWORD PTR [eax]
  861285:	85 c0                	test   eax,eax
  861287:	75 05                	jne    0x86128e
  861289:	b8 60 9b aa 00       	mov    eax,0xaa9b60
  86128e:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861290:	8b 51 24             	mov    edx,DWORD PTR [ecx+0x24]
  861293:	50                   	push   eax
  861294:	6a 00                	push   0x0
  861296:	56                   	push   esi
  861297:	ff d2                	call   edx
  861299:	85 c0                	test   eax,eax
  86129b:	89 45 0c             	mov    DWORD PTR [ebp+0xc],eax
  86129e:	74 64                	je     0x861304
  8612a0:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  8612a3:	8b 49 04             	mov    ecx,DWORD PTR [ecx+0x4]
  8612a6:	83 c1 ff             	add    ecx,0xffffffff
  8612a9:	83 f9 04             	cmp    ecx,0x4
  8612ac:	77 56                	ja     0x861304
  8612ae:	ff 24 8d cc 13 86 00 	jmp    DWORD PTR [ecx*4+0x8613cc]
  8612b5:	8b 06                	mov    eax,DWORD PTR [esi]
  8612b7:	8b 53 0c             	mov    edx,DWORD PTR [ebx+0xc]
  8612ba:	8b 4a 08             	mov    ecx,DWORD PTR [edx+0x8]
  8612bd:	05 d0 00 00 00       	add    eax,0xd0
  8612c2:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
  8612c5:	e8 26 7b fd ff       	call   0x838df0
  8612ca:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
  8612cd:	8b 11                	mov    edx,DWORD PTR [ecx]
  8612cf:	50                   	push   eax
  8612d0:	8b 45 0c             	mov    eax,DWORD PTR [ebp+0xc]
  8612d3:	50                   	push   eax
  8612d4:	56                   	push   esi
  8612d5:	ff d2                	call   edx
  8612d7:	eb 2b                	jmp    0x861304
  8612d9:	8b 4b 0c             	mov    ecx,DWORD PTR [ebx+0xc]
  8612dc:	d9 41 10             	fld    DWORD PTR [ecx+0x10]
  8612df:	8b 16                	mov    edx,DWORD PTR [esi]
  8612e1:	d9 5d 0c             	fstp   DWORD PTR [ebp+0xc]
  8612e4:	51                   	push   ecx
  8612e5:	d9 45 0c             	fld    DWORD PTR [ebp+0xc]
  8612e8:	d9 1c 24             	fstp   DWORD PTR [esp]
  8612eb:	50                   	push   eax
  8612ec:	8b 42 78             	mov    eax,DWORD PTR [edx+0x78]
  8612ef:	eb 10                	jmp    0x861301
  8612f1:	8b 53 0c             	mov    edx,DWORD PTR [ebx+0xc]
  8612f4:	8b 0e                	mov    ecx,DWORD PTR [esi]
  8612f6:	83 c2 10             	add    edx,0x10
  8612f9:	52                   	push   edx
  8612fa:	50                   	push   eax
  8612fb:	8b 81 88 00 00 00    	mov    eax,DWORD PTR [ecx+0x88]
  861301:	56                   	push   esi
  861302:	ff d0                	call   eax
  861304:	85 db                	test   ebx,ebx
  861306:	74 09                	je     0x861311
  861308:	8b 43 04             	mov    eax,DWORD PTR [ebx+0x4]
  86130b:	85 c0                	test   eax,eax
  86130d:	74 02                	je     0x861311
  86130f:	8b d8                	mov    ebx,eax
  861311:	8b 4d fc             	mov    ecx,DWORD PTR [ebp-0x4]
  861314:	8b 91 34 05 00 00    	mov    edx,DWORD PTR [ecx+0x534]
  86131a:	8b 45 ec             	mov    eax,DWORD PTR [ebp-0x14]
  86131d:	8d 4c 10 08          	lea    ecx,[eax+edx*1+0x8]
  861321:	8d 55 dc             	lea    edx,[ebp-0x24]
  861324:	e8 87 4b c9 ff       	call   0x4f5eb0
  861329:	3b 18                	cmp    ebx,DWORD PTR [eax]
  86132b:	0f 85 4f ff ff ff    	jne    0x861280
  861331:	89 5d e8             	mov    DWORD PTR [ebp-0x18],ebx
  861334:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861336:	8b 81 fc 00 00 00    	mov    eax,DWORD PTR [ecx+0xfc]
  86133c:	6a 01                	push   0x1
  86133e:	8d 55 d8             	lea    edx,[ebp-0x28]
  861341:	52                   	push   edx
  861342:	56                   	push   esi
  861343:	ff d0                	call   eax
  861345:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861347:	8b 91 00 01 00 00    	mov    edx,DWORD PTR [ecx+0x100]
  86134d:	6a 00                	push   0x0
  86134f:	56                   	push   esi
  861350:	ff d2                	call   edx
  861352:	8b 06                	mov    eax,DWORD PTR [esi]
  861354:	8b 88 04 01 00 00    	mov    ecx,DWORD PTR [eax+0x104]
  86135a:	56                   	push   esi
  86135b:	ff d1                	call   ecx
  86135d:	8b 17                	mov    edx,DWORD PTR [edi]
  86135f:	8b 82 48 01 00 00    	mov    eax,DWORD PTR [edx+0x148]
  861365:	6a 02                	push   0x2
  861367:	6a 00                	push   0x0
  861369:	6a 04                	push   0x4
  86136b:	6a 00                	push   0x0
  86136d:	6a 00                	push   0x0
  86136f:	6a 05                	push   0x5
  861371:	57                   	push   edi
  861372:	ff d0                	call   eax
  861374:	8b 0e                	mov    ecx,DWORD PTR [esi]
  861376:	8b 91 08 01 00 00    	mov    edx,DWORD PTR [ecx+0x108]
  86137c:	56                   	push   esi
  86137d:	ff d2                	call   edx
  86137f:	8b 06                	mov    eax,DWORD PTR [esi]
  861381:	8b 88 0c 01 00 00    	mov    ecx,DWORD PTR [eax+0x10c]
  861387:	56                   	push   esi
  861388:	ff d1                	call   ecx
  86138a:	8b 5d f4             	mov    ebx,DWORD PTR [ebp-0xc]
  86138d:	8b 45 f8             	mov    eax,DWORD PTR [ebp-0x8]
  861390:	83 c3 01             	add    ebx,0x1
  861393:	3b d8                	cmp    ebx,eax
  861395:	89 5d f4             	mov    DWORD PTR [ebp-0xc],ebx
  861398:	0f 82 b2 fb ff ff    	jb     0x860f50
  86139e:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  8613a4:	8b 01                	mov    eax,DWORD PTR [ecx]
  8613a6:	8b 80 00 01 00 00    	mov    eax,DWORD PTR [eax+0x100]
  8613ac:	33 d2                	xor    edx,edx
  8613ae:	ff d0                	call   eax
  8613b0:	8b c8                	mov    ecx,eax
  8613b2:	e8 99 1f ff ff       	call   0x853350
  8613b7:	5f                   	pop    edi
  8613b8:	5e                   	pop    esi
  8613b9:	b0 01                	mov    al,0x1
  8613bb:	5b                   	pop    ebx
  8613bc:	8b e5                	mov    esp,ebp
  8613be:	5d                   	pop    ebp
  8613bf:	c2 08 00             	ret    0x8
  8613c2:	32 c0                	xor    al,al
  8613c4:	5b                   	pop    ebx
  8613c5:	8b e5                	mov    esp,ebp
  8613c7:	5d                   	pop    ebp
  8613c8:	c2 08 00             	ret    0x8
  8613cb:	90                   	nop
  8613cc:	b5 12                	mov    ch,0x12
  8613ce:	86 00                	xchg   BYTE PTR [eax],al
  8613d0:	d9 12                	fst    DWORD PTR [edx]
  8613d2:	86 00                	xchg   BYTE PTR [eax],al
  8613d4:	f1                   	int1
  8613d5:	12 86 00 f1 12 86    	adc    al,BYTE PTR [esi-0x79ed0f00]
  8613db:	00 f1                	add    cl,dh
  8613dd:	12 86 00 55 8b ec    	adc    al,BYTE PTR [esi-0x1374ab00]
  8613e3:	83 ec 0c             	sub    esp,0xc
  8613e6:	53                   	push   ebx
  8613e7:	56                   	push   esi
  8613e8:	57                   	push   edi
  8613e9:	8b f9                	mov    edi,ecx
  8613eb:	8d 5f 08             	lea    ebx,[edi+0x8]
  8613ee:	8d 55 fc             	lea    edx,[ebp-0x4]
  8613f1:	8b cb                	mov    ecx,ebx
  8613f3:	89 7d f4             	mov    DWORD PTR [ebp-0xc],edi
  8613f6:	e8 85 c7 e1 ff       	call   0x67db80
  8613fb:	8d 55 f8             	lea    edx,[ebp-0x8]
  8613fe:	8b cb                	mov    ecx,ebx
  861400:	e8 ab 4a c9 ff       	call   0x4f5eb0
  861405:	8b 75 fc             	mov    esi,DWORD PTR [ebp-0x4]
  861408:	3b 30                	cmp    esi,DWORD PTR [eax]
  86140a:	0f 95 c0             	setne  al
  86140d:	84 c0                	test   al,al
  86140f:	74 55                	je     0x861466
  861411:	8b 46 0c             	mov    eax,DWORD PTR [esi+0xc]
  861414:	8b 50 08             	mov    edx,DWORD PTR [eax+0x8]
  861417:	85 d2                	test   edx,edx
  861419:	74 1a                	je     0x861435
  86141b:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  861421:	8b 01                	mov    eax,DWORD PTR [ecx]
  861423:	8b 80 38 02 00 00    	mov    eax,DWORD PTR [eax+0x238]
  861429:	ff d0                	call   eax
  86142b:	8b 4e 0c             	mov    ecx,DWORD PTR [esi+0xc]
  86142e:	c7 41 08 00 00 00 00 	mov    DWORD PTR [ecx+0x8],0x0
  861435:	8b 7e 0c             	mov    edi,DWORD PTR [esi+0xc]
  861438:	85 ff                	test   edi,edi
  86143a:	74 10                	je     0x86144c
  86143c:	8b cf                	mov    ecx,edi
  86143e:	e8 7d fc dc ff       	call   0x6310c0
  861443:	57                   	push   edi
  861444:	e8 e7 54 02 00       	call   0x886930
  861449:	83 c4 04             	add    esp,0x4
  86144c:	8b 46 04             	mov    eax,DWORD PTR [esi+0x4]
  86144f:	85 c0                	test   eax,eax
  861451:	74 02                	je     0x861455
  861453:	8b f0                	mov    esi,eax
  861455:	8d 55 f8             	lea    edx,[ebp-0x8]
  861458:	8b cb                	mov    ecx,ebx
  86145a:	e8 51 4a c9 ff       	call   0x4f5eb0
  86145f:	3b 30                	cmp    esi,DWORD PTR [eax]
  861461:	75 ae                	jne    0x861411
  861463:	8b 7d f4             	mov    edi,DWORD PTR [ebp-0xc]
  861466:	8b cb                	mov    ecx,ebx
  861468:	e8 b3 5f e3 ff       	call   0x697420
  86146d:	8b 47 04             	mov    eax,DWORD PTR [edi+0x4]
  861470:	85 c0                	test   eax,eax
  861472:	74 23                	je     0x861497
  861474:	8b 0d 58 60 c2 00    	mov    ecx,DWORD PTR ds:0xc26058
  86147a:	50                   	push   eax
  86147b:	ba 01 00 00 00       	mov    edx,0x1
  861480:	e8 6b 3e fd ff       	call   0x8352f0
  861485:	8b 47 04             	mov    eax,DWORD PTR [edi+0x4]
  861488:	8b 10                	mov    edx,DWORD PTR [eax]
  86148a:	50                   	push   eax
  86148b:	8b 42 08             	mov    eax,DWORD PTR [edx+0x8]
  86148e:	ff d0                	call   eax
  861490:	c7 47 04 00 00 00 00 	mov    DWORD PTR [edi+0x4],0x0
  861497:	8b cb                	mov    ecx,ebx
  861499:	e8 62 95 01 00       	call   0x87aa00
  86149e:	8b cb                	mov    ecx,ebx
  8614a0:	e8 4b 29 09 00       	call   0x8f3df0
  8614a5:	8b cf                	mov    ecx,edi
  8614a7:	e8 14 fc dc ff       	call   0x6310c0
  8614ac:	5f                   	pop    edi
  8614ad:	5e                   	pop    esi
  8614ae:	5b                   	pop    ebx
  8614af:	8b e5                	mov    esp,ebp
  8614b1:	5d                   	pop    ebp
  8614b2:	c3                   	ret
```

## P1 exact queue consumer snippet (verified)

```asm
  831380:	83 79 24 00          	cmp    DWORD PTR [ecx+0x24],0x0
  831384:	75 03                	jne    0x831389
  831386:	32 c0                	xor    al,al
  831388:	c3                   	ret
  831389:	8b 41 1c             	mov    eax,DWORD PTR [ecx+0x1c]
  83138c:	83 78 14 00          	cmp    DWORD PTR [eax+0x14],0x0
  831390:	74 f4                	je     0x831386
  831392:	56                   	push   esi
  831393:	8b f0                	mov    esi,eax
  831395:	8b 46 14             	mov    eax,DWORD PTR [esi+0x14]
  831398:	83 e8 01             	sub    eax,0x1
  83139b:	0f af 01             	imul   eax,DWORD PTR [ecx]
  83139e:	03 46 04             	add    eax,DWORD PTR [esi+0x4]
  8313a1:	8b 00                	mov    eax,DWORD PTR [eax]
  8313a3:	89 02                	mov    DWORD PTR [edx],eax
  8313a5:	e8 46 b3 c6 ff       	call   0x49c6f0
  8313aa:	b0 01                	mov    al,0x1
  8313ac:	5e                   	pop    esi
  8313ad:	c3                   	ret
```

```asm
  835590:	55                   	push   ebp
  835591:	8b ec                	mov    ebp,esp
  835593:	83 ec 08             	sub    esp,0x8
  835596:	53                   	push   ebx
  835597:	8b d9                	mov    ebx,ecx
  835599:	56                   	push   esi
  83559a:	57                   	push   edi
  83559b:	8d bb d8 1a 00 00    	lea    edi,[ebx+0x1ad8]
  8355a1:	8b cf                	mov    ecx,edi
  8355a3:	89 5d fc             	mov    DWORD PTR [ebp-0x4],ebx
  8355a6:	e8 15 9e ff ff       	call   0x82f3c0
  8355ab:	84 c0                	test   al,al
  8355ad:	75 43                	jne    0x8355f2
  8355af:	90                   	nop
  8355b0:	8d 55 f8             	lea    edx,[ebp-0x8]
  8355b3:	8b cf                	mov    ecx,edi
  8355b5:	e8 c6 bd ff ff       	call   0x831380
  8355ba:	8b 75 f8             	mov    esi,DWORD PTR [ebp-0x8]
  8355bd:	8d 4e 04             	lea    ecx,[esi+0x4]
  8355c0:	e8 8b c7 da ff       	call   0x5e1d50
  8355c5:	83 f8 01             	cmp    eax,0x1
  8355c8:	75 1d                	jne    0x8355e7
  8355ca:	56                   	push   esi
  8355cb:	8d 50 05             	lea    edx,[eax+0x5]
  8355ce:	8b cb                	mov    ecx,ebx
  8355d0:	e8 1b fd ff ff       	call   0x8352f0
  8355d5:	85 f6                	test   esi,esi
  8355d7:	74 0e                	je     0x8355e7
  8355d9:	8b 06                	mov    eax,DWORD PTR [esi]
  8355db:	8b 90 88 00 00 00    	mov    edx,DWORD PTR [eax+0x88]
  8355e1:	6a 01                	push   0x1
  8355e3:	8b ce                	mov    ecx,esi
  8355e5:	ff d2                	call   edx
  8355e7:	8b cf                	mov    ecx,edi
  8355e9:	e8 d2 9d ff ff       	call   0x82f3c0
  8355ee:	84 c0                	test   al,al
  8355f0:	74 be                	je     0x8355b0
```
