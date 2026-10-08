# Process 1D — mode-2 camera runtime-argument identity

## Result

Phase 651 request 1 is closed negatively with exact PC-retail machine-code value flow.

The argument passed to the mode-2 source virtual call at `source.vtable+0x90` is **not** the selected BMW/player vehicle and is not a vehicle world matrix. It is the selected camera object returned by the CameraManager camera-id lookup and accepted by the type-chain test against descriptor `0x00c25fb8`.

This means the remaining vehicle/current-pose dependency must be found inside the concrete mode-2 source object/vtable logic, not by treating `FUN_0080e0d0::param_1` as a vehicle pointer.

## Retail authority

Executable:

```text
SHIFT.exe PC retail 1.02
sha256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
```

The Ghidra SQLite database was used only to bound direct callers. It reports one direct retail caller of `FUN_0080e0d0`: `FUN_0080e1b0` at `0x0080e236`. The semantic result below comes from the executable machine body, not from callgraph adjacency.

## Caller value flow

In `FUN_0080e1b0`:

```text
0x0080e200  mov ecx,[esi+0x2564]
0x0080e207  call FUN_0080b8e0
0x0080e20c  mov edx,[eax+0x10]
0x0080e20f  lea ecx,[eax+0x10]
0x0080e212  mov eax,[edx+0x08]
0x0080e215  push edi
0x0080e216  call eax
0x0080e218  mov ebx,eax
...
0x0080e222  push 0x00c25fb8
0x0080e227  mov ecx,ebx
0x0080e229  call FUN_004b71f0
0x0080e22e  test eax,eax
0x0080e230  push edi
0x0080e231  mov ecx,esi
0x0080e233  je 0x0080e2a7
0x0080e235  push eax
0x0080e236  call FUN_0080e0d0
```

`EDI` is the requested camera id. The lookup/virtual-call chain produces the selected camera object in `EBX`. That object is then passed as the receiver to `FUN_004b71f0` with descriptor `0x00c25fb8`.

## Type-chain helper behavior

`FUN_004b71f0` does not manufacture a different object pointer. Its relevant behavior is:

```text
0x004b71f4  mov esi,ecx
0x004b71f6  mov eax,[esi]
0x004b71f8  mov edx,[eax+0x04]
0x004b71fb  call edx
...
0x004b7204  cmp eax,ecx
0x004b7206  je 0x004b721c
0x004b7208  mov eax,[eax+0x08]
...
0x004b721c  mov eax,1
...
0x004b7225  and eax,esi
```

It walks an object type-chain and returns the original receiver `ESI` on match, otherwise zero. Therefore the non-null `EAX` pushed at `0x0080e235` is the same selected camera object held in `EBX`.

## Callee value flow

Inside `FUN_0080e0d0`:

```text
0x0080e0e9  mov edx,[esi+0x2560]
0x0080e0ef  imul edx,edx,0x460
0x0080e0f5  mov eax,[edx+esi+0x1ca0]
0x0080e0fc  mov eax,[eax+0x90]
0x0080e102  lea ecx,[edx+esi+0x1ca0]
0x0080e109  mov edx,[ebp+0x08]
0x0080e10c  push edx
0x0080e10d  call eax
```

`[ebp+0x08]` is `FUN_0080e0d0::param_1`, so the exact runtime argument reaching the mode-2 source `+0x90` virtual call is the selected camera object proven above.

## Adjudication

Positive:

- direct retail caller surface of `FUN_0080e0d0`: bounded to one callsite;
- `FUN_0080e0d0::param_1` source: proven;
- `source.vtable+0x90` runtime argument identity: proven as selected camera object;
- equality with selected retail vehicle: rejected;
- equality with vehicle world matrix: rejected.

Still open:

- concrete mode-2 source object/vtable identity;
- exact `+0x90` and `+0x64` callees;
- vehicle/current-pose dependency inside those source methods;
- retail vehicle-update -> camera-source update ordering/freshness.

No native camera-follow gate is promoted, and the external provider count remains **7**.

## Next step

Resolve the concrete vtable installed at `CameraManager + 0x1ca0 + current_index * 0x460`, then inspect its `+0x90` and `+0x64` targets. The vehicle pose must now enter through that tracking-source logic or one of its dependencies; repeating the hypothesis that `FUN_0080e0d0::param_1` is a vehicle pointer is no longer productive.
