# Process 1 — UI readiness guard and count provenance, v787–v788

## Run identity and scope

These were controlled executions of the original retail PE32 image through the P-code guest runtime, not native Windows/Wine launches and not a recompiled game. Both used retail SHIFT.exe 1.02 (SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`), runtime `native_runtime/build/shift_runtime` (SHA-256 `4d5e118b93567f9e31f076edcb5c1e1d97f3543222d703d2b26fca8056346ee8`), the v659 startup supplement manifest, and game-data set `pcode-game-data-v661`. The probe was bounded to 120 host frames with Vulkan validation.

| Run | Frames | Dispatches | Unique guest functions | Validation errors | Trace | Log SHA-256 | Summary JSON SHA-256 |
|---|---:|---:|---:|---:|---|---|---|
| v787 | 120 | 815,088 | 3,934 | 0 | 23 selected events; not truncated | `98626e3698901525436a46ecf7ada4f817fccee9a2a7f9995a1f0dc7cfce2dbb` | `a969e1bf23c92235e0ee928dc80053f8b8b84f117864de89eef73f006551c255` |
| v788 | 120 | 815,451 | 3,934 | 0 | 23 selected events; not truncated; exact-address provenance enabled | `647e1a3ee2d586c3b038d715694821d57bc9fab8ad74ef444f8f0bea7b8b24bb` | `7cbe31be3c050bb794f90ff4c3eec86df22d5382a5ab556eb88ee1b42d7d39fb` |

Both summaries report the host-frame-loop checkpoint, `guest_draw_translation=false`, and `retail_rendering_proven=false`. Dispatch counts are not a gameplay or rendering milestone.

## Observed object and guard input

The selected original writer `0x005092F0` ran for object `O=0x27DFA5FC`. It passed `ECX=O+8=0x27DFA604` to `0x00554050`. The guard read `DWORD[ECX+0x0C]`, which is exactly `DWORD[O+0x14]`.

In v787 and v788, the single recorded call to `0x00554050` saw `DWORD[O+0x14]=9`. It returned `EAX=0x00509200`, so the returned low byte was `AL=0`. The caller tests only `AL`; therefore the original writer took its nonzero-field branch and executed the byte-zero store at `0x00509314`, `BYTE[O+0x2D]=0`.

In v788, exact-address provenance for `0x27DFA610` (`O+0x14`) names the immediately preceding write:

- writer `0x004F5E60`, dispatch 461055;
- write address `0x27DFA610`, size 4, value `9`;
- writer ECX `0x27DFA604` (`O+8`);
- reported caller thunk `0x005092E0`, return address `0x0054BABF`;
- same guest thread `0x00177D80` as the guard event.

The next recorded guard event is dispatch 461057. The address-level sequence, object base, writer and value agree with the original PE instructions below.

## Original PE instructions tied to the observation

The short entry thunk at `0x005092E0` adjusts ECX to the embedded object at `O+8` and tail-jumps to the insertion routine:

~~~asm
005092e0: 83 c1 08              add    ecx,0x8
005092e3: e9 78 cb fe ff        jmp    0x4f5e60
~~~

Complete `0x004F5E60` block, independently disassembled from the SHA-verified PE:

~~~asm
004f5e60: 56                    push   esi
004f5e61: 8b f1                 mov    esi,ecx
004f5e63: 83 3e 00              cmp    DWORD PTR [esi],0x0
004f5e66: 57                    push   edi
004f5e67: 8b fa                 mov    edi,edx
004f5e69: 75 14                 jne    0x4f5e7f
004f5e6b: 8b 46 18              mov    eax,DWORD PTR [esi+0x18]
004f5e6e: 8b 4e 08              mov    ecx,DWORD PTR [esi+0x8]
004f5e71: 8b 56 04              mov    edx,DWORD PTR [esi+0x4]
004f5e74: 50                    push   eax
004f5e75: 6a 1f                 push   0x1f
004f5e77: 51                    push   ecx
004f5e78: 8b ce                 mov    ecx,esi
004f5e7a: e8 91 ff ff ff        call   0x4f5e10
004f5e7f: 8b ce                 mov    ecx,esi
004f5e81: e8 9a 14 f3 ff        call   0x427320
004f5e86: 8b 56 14              mov    edx,DWORD PTR [esi+0x14]
004f5e89: 8b 0a                 mov    ecx,DWORD PTR [edx]
004f5e8b: 89 08                 mov    DWORD PTR [eax],ecx
004f5e8d: 8b 56 14              mov    edx,DWORD PTR [esi+0x14]
004f5e90: 89 50 04              mov    DWORD PTR [eax+0x4],edx
004f5e93: 8b 4e 14              mov    ecx,DWORD PTR [esi+0x14]
004f5e96: 8b 11                 mov    edx,DWORD PTR [ecx]
004f5e98: 89 42 04              mov    DWORD PTR [edx+0x4],eax
004f5e9b: 8b 4e 14              mov    ecx,DWORD PTR [esi+0x14]
004f5e9e: 89 01                 mov    DWORD PTR [ecx],eax
004f5ea0: 83 c0 0c              add    eax,0xc
004f5ea3: 89 38                 mov    DWORD PTR [eax],edi
004f5ea5: 83 46 0c 01           add    DWORD PTR [esi+0xc],0x1
004f5ea9: 5f                    pop    edi
004f5eaa: 5e                    pop    esi
004f5eab: c3                    ret
~~~

The byte facts show the function receives the container in ECX and another DWORD in EDX; it calls `0x00427320`, links a node using the pointer at `container+0x14`, stores the incoming EDX at `newNode+0x0C`, increments `DWORD[container+0x0C]`, and returns. The block does not establish the allocator's requested node size or public structure type. For this observed container `container=O+8`, so the incremented field is `O+0x14`. The trace records the increment's post-write value as 9 immediately before the guard read it. The meaning or completion status of the queued item(s) is not established here.

## Bounded conclusion and remaining uncertainty

The zero readiness-byte write in this replay is consistent with the original predicate's behavior when this collection field is nonzero: the guard sees 9, sets AL to zero, and the updater clears `O+0x2D` before traversing the linked items. This is not evidence of a bad P-code translation, a missing compatibility stub, or an incorrect retail instruction. It also does not show why the collection remains nonzero, whether any item completion callback later changes the count or readiness byte, or whether this predicate caused the progress plateau. No state was forced. No menu, retail draw, or race was proven.

The next bounded static/runtime target is the lifecycle of the queued item inserted by `0x004F5E60`: first identify the exact incoming EDX object at the observed call site and the semantics of the direct item callback already reached by the updater. Keep the current owner readiness byte and count unchanged while tracing.
