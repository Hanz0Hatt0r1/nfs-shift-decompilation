# Process 1A / P1.3A — final shallow x87 zero-init closure

## Scope

The P1.3A slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` search had 18 direct-depth<=4 `FLDZ -> FST/FSTP` candidates. Merged P1A tranches #1740 and #1742 rejected 14. Merged P1D #1743 independently machine-adjudicated the same four remaining pointer-chain candidates while closing the slot3 surface.

The four #1743 conclusions are receiver/destination facts rather than slot3-specific arithmetic, so this P1A composition consumes them without re-owning the P1D contract.

## Final four

- `FUN_0075c0d0` — the only bounded root path is infeasible: `FUN_00770e80` passes literal zero as the `FUN_007b1790` argument that gates the call to `FUN_0075c0d0`.
- `FUN_0075ada0` — `FUN_007682c0` passes four exact stack-local output pointers (`EBP-0x8/-0xc/-0x18/-0x24`); the x87 zero branch writes only those outputs.
- `FUN_007b8630` — the path starts from the proven BODY-owner pointer at `HDVehicle+0x339c`, follows `owner+0x5c` and nested record pointers, then clears BODY motion/accumulator lanes `+0x48..+0x88`.
- `FUN_007b7840` — the only bounded non-recursive direct path descends through `FUN_007b8810 -> FUN_007b8630 -> FUN_007b8260`; the zero cluster clears the same BODY-domain `+0x48..+0x70` lanes.

The BODY classification is backed by `SHIFT.GlobalVehicleBodyOwnerIdentity/1`, `SHIFT.BodyFrameIntegrationStatic/1`, and the independent direct-role proof for `FUN_007b7840`. No conclusion is derived from numeric offset equality alone.

## Gate

```text
shallow x87 candidates                 = 18
shallow x87 rejected                   = 18
shallow x87 selected slot0/1 writer    = false
x87 zero-init semantics complete       = true
SSE/vector copy-init complete          = false
deeper direct aliases ruled out        = false
indirect/callback aliases ruled out    = false
slot0 complete                         = false
slot1 complete                         = false
P1.3 complete                          = false
provider count                         = 7
```

## Next step

Remove x87 zero-init from the P1.3A frontier. Bound shallow SSE/vector copy and zero-initialization paths next, then widen only exact selected-HDVehicle-derived deeper direct or indirect/callback aliases.
