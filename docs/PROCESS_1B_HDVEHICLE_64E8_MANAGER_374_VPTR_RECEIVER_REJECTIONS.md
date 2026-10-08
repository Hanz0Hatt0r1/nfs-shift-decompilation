# Process 1B — manager `+0x374` receiver rejections

## Scope

The corrected `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` worklist leaves 20 actionable literal `[base+0x374]` stores after inheriting three already-merged negative sites. Receiver identity must be proven rather than inferred from the numeric displacement.

Retail constructor `FUN_00488dc0` distinguishes two object levels explicitly:

- root manager vptr `0x00ab9190` at `0x00488df5 mov [esi],0x00ab9190`;
- embedded Participants Manager subobject vptr `0x00ab916c` at `0x00488dfb mov [esi+0x20],0x00ab916c`.

Literal `[manager+0x374]` uses the root manager receiver. The exact root singleton address is `0x00bc9fc0`.

## Same-body receiver vptr rejections

Six sites are rejected because retail machine code captures the entry receiver and assigns a non-manager-root vptr to the same destination base before its `+0x374` write:

- `0x0074874b` / `FUN_00748280`: vptr `0x00b07938`.
- `0x008169c3` / `FUN_008167f0`: final vptr `0x00b16158`.
- `0x00833972` / `FUN_00833760`: final vptr `0x00b190a8`.
- `0x00844343` / `FUN_00844320`: vptr `0x00b190a8`.
- `0x00844b67` / `FUN_00844a20`: vptr `0x00b190a8`.
- `0x00d7f104` / `FUN_00d7f040`: vptr `0x00ac1fc4`.

Every listed vptr is distinct from root manager `0x00ab9190`.

## Unique vtable-dispatch rejection

`FUN_008446a0` contains three target stores at `0x008446cb`, `0x008446e3`, and `0x008446f8`, using the entry `ECX` receiver captured in `ESI`.

Its address has exactly one function-pointer occurrence in the whole retail PE: `0x00b19144 = vtable 0x00b190a8 + 0x9c`, and there are zero direct CALL references. Its receiver domain is therefore exact vtable `0x00b190a8`, not manager root `0x00ab9190`.

## Exact owner+0x56c child rejection

Site `0x00816c9c` in `FUN_00816c70` is joined through an exact child lifecycle:

```text
0x0080bb2c  push 0x390
0x0080bb37  call FUN_008868c0
0x0080bb43  mov ecx,eax
0x0080bb45  call FUN_008167f0
0x0080bb4a  mov [esi+0x56c],eax
```

`FUN_008167f0` installs final vptr `0x00b16158`. `FUN_0080b8f0` is exactly `mov eax,[ecx+0x56c]; ret`; the consumer saves that returned pointer in `EDI` and calls `FUN_00816c70` with `ECX=EDI`. Therefore the `+0x374` base is the constructed owner+0x56c child, not manager root.

## Embedded-owner address rejections

Sites `0x007c0fa0` and `0x007c1ace` belong to child constructors called only from common owner constructor `FUN_007c3170`:

```text
0x007c31a3  lea ecx,[esi+0x8]
0x007c31aa  call FUN_007c0db0
...
0x007c320b  lea ecx,[esi+0xfe8]
0x007c3215  call FUN_007c19c0
```

The entire direct caller surface of `FUN_007c3170` is three sites. Two create a fresh `0x3848` allocation and immediately construct it (`0x0076dfcc`, `0x00798e74`); the third passes fixed static receiver `0x00c1c568` (`0x00a8ca65`). Thus the target receivers are either fresh-object `outer+0x8` / `outer+0xfe8` or fixed `0x00c1c570` / `0x00c1d550`. None is fixed manager singleton `0x00bc9fc0`.

## Boundary

Twelve newly rejected sites reduce the corrected actionable literal writer worklist from 20 to 8. The remaining eight require exact owner/caller provenance in runtime-object and copy/state families. Computed-address writes remain outside this contract.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
