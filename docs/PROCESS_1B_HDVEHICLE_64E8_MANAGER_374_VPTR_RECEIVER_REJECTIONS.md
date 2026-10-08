# Process 1B — manager `+0x374` vptr receiver rejections

## Scope

The corrected `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` worklist leaves 20 actionable literal `[base+0x374]` stores after inheriting three already-merged negative sites. Receiver identity must be proven rather than inferred from the numeric displacement.

Retail constructor `FUN_00488dc0` distinguishes two object levels explicitly:

- root manager vptr `0x00ab9190` at `0x00488df5 mov [esi],0x00ab9190`;
- embedded Participants Manager subobject vptr `0x00ab916c` at `0x00488dfb mov [esi+0x20],0x00ab916c`.

Literal `[manager+0x374]` uses the root manager receiver, so receiver-vptr rejection in this contract compares against `0x00ab9190`. Site `0x005ded7e` remains excluded because corrected inventory PR #1670 already inherits its separate allocation-size rejection.

## Same-body receiver vptr rejections

Six sites are rejected because retail machine code captures the entry receiver and assigns a non-manager-root vptr to the same destination base before its `+0x374` write:

- `0x0074874b` / `FUN_00748280`: `ESI=ECX`; vptr `0x00b07938`.
- `0x008169c3` / `FUN_008167f0`: `ESI=ECX`; construction vptrs `0x00b1e270`, `0x00aaa9a0`, `0x00b16158`.
- `0x00833972` / `FUN_00833760`: `EBX=ECX`; vptrs `0x00b18bc8` then `0x00b190a8`.
- `0x00844343` / `FUN_00844320`: `ESI=ECX`; vptr `0x00b190a8`.
- `0x00844b67` / `FUN_00844a20`: `ESI=ECX`; vptr `0x00b190a8`.
- `0x00d7f104` / `FUN_00d7f040`: `ESI=ECX`; vptr `0x00ac1fc4`.

Every listed vptr is distinct from root manager `0x00ab9190`.

## Unique vtable-dispatch rejection

`FUN_008446a0` contains three literal `+0x374` stores at `0x008446cb`, `0x008446e3`, and `0x008446f8`, all through `ESI` after `0x008446a9 mov esi,ecx`.

Its machine address `0x008446a0` has exactly one function-pointer occurrence in the entire retail PE: `.rdata` address `0x00b19144`, which is vtable `0x00b190a8 + 0x9c`. There are zero direct CALL references to `FUN_008446a0`. Therefore its statically registered receiver domain is vtable `0x00b190a8`, not root manager `0x00ab9190`, and all three stores are rejected.

## Exact owner+0x56c child rejection

`0x00816c9c` in `FUN_00816c70` writes `add [ecx+0x374],1`. Its receiver is joined exactly through a constructed child:

```text
0x0080bb2c  push 0x390
0x0080bb37  call FUN_008868c0
0x0080bb43  mov ecx,eax
0x0080bb45  call FUN_008167f0
0x0080bb4a  mov [esi+0x56c],eax
```

`FUN_008167f0` installs final receiver vptr `0x00b16158`. Getter `FUN_0080b8f0` is exactly `mov eax,[ecx+0x56c]; ret`. The consumer path calls the owner getter, calls `FUN_0080b8f0`, saves the returned child in `EDI`, then at `0x00572f49 mov ecx,edi` calls `FUN_00816c70` at `0x00572f4d`.

Thus `0x00816c9c` operates on the exact `owner+0x56c` child with vptr `0x00b16158`, not manager root `0x00ab9190`.

## Boundary

The ten newly rejected sites reduce the corrected actionable literal writer worklist from 20 to 10. The remaining ten require owner/caller provenance, including embedded-receiver and runtime-object/copy families. Computed-address writes remain outside this contract.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
