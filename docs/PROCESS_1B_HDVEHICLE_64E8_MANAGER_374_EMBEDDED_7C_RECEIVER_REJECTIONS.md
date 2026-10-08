# Process 1B — embedded `0x7c...` manager+0x374 receiver rejections

## Scope

The corrected literal `+0x374` inventory still contains stores in `FUN_007c0db0` and `FUN_007c19c0`. Numeric displacement equality is not enough to identify either receiver with Participants Manager.

This slice follows the physical receivers back through their shared parent constructor `FUN_007c3170` using PC retail 1.02 machine code.

## Embedded receiver identities

`FUN_007c3170` constructs the first target as an embedded child at parent `+0x8`:

```text
0x007c31a3 lea ecx,[esi+0x8]
0x007c31aa call 0x007c0db0
```

The second target is an embedded child at parent `+0xfe8`:

```text
0x007c320b lea ecx,[esi+0xfe8]
0x007c3215 call 0x007c19c0
```

Inside those children, the literal stores are `0x007c0fa0` and `0x007c1ace`; both callees capture entry ECX in ESI.

## Parent ownership

The complete known machine entry surface to `FUN_007c3170` is two fresh `0x3848` allocations and one fixed-global parent:

```text
0x0076dfb4 call 0x008868d0
0x0076dfca mov ecx,eax
0x0076dfcc call 0x007c3170

0x00798e60 call 0x008868d0
0x00798e72 mov ecx,eax
0x00798e74 call 0x007c3170

0x00a8ca60 mov ecx,0x00c1c568
0x00a8ca65 call 0x007c3170
```

The fixed children are `0x00c1c570` and `0x00c1d550`, distinct from Participants Manager singleton `0x00bc9fc0`; fresh heap children likewise do not alias that mapped static singleton.

## Adjudication

Both literal `+0x374` sites are closed-negative as Participants Manager writes. With the upstream ten-site vptr/owner batch, the remaining literal receiver-provenance worklist shrinks from 10 to 8 sites.

Computed-address stores and the final manager+0x374 -> HDVehicle+0x4330 identity join remain open. `0x004b86cf`, P1.3 and provider removal remain fail-closed; provider count remains 7.
