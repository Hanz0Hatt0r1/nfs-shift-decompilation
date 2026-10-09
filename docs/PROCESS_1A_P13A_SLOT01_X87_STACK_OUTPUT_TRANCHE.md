# Process 1A / P1.3A — second x87 semantic tranche

After the merged first x87 tranche, nine `FLDZ -> FST/FSTP` candidates remained. This tranche closes five more using direct PC-retail machine transfer.

## HDVehicle far-offset case

`FUN_0076d100` carries the selected HDVehicle receiver in `ESI` and invokes `FUN_00766510` with `ECX=ESI` at `0x0076d137/0x0076d139`. The callee captures entry `ECX` in `ESI`; its frontier zero stores target only:

```text
+0x40a0
+0x40a8
+0x40b0
+0x42b0
+0x4300
```

These ranges are disjoint from selected slot0 `+0x938` and slot1 `+0x13b8`.

## Stack-output cases

The remaining four candidates in this tranche write caller stack locals rather than persistent HDVehicle state:

- `FUN_007aa940`: `FUN_007aa9b0` passes `EBP-0x18`; the callee zeroes output `+0/+4/+8`.
- `FUN_0075afc0`: `FUN_0076a200` passes `EBP-0x4c`, `EBP-0x34`, and `EBP-0x28` as callee arguments 4/5/6; the zero branch writes exactly those three output vectors.
- `FUN_007876e0`: `FUN_00787730` passes `EBP-0xc`; the callee zeroes output `+0/+4`.
- `FUN_007ade70`: the only bounded direct calls from `FUN_00759210` pass either `EBP-0x38` or `EBP-0x2c`; the frontier zero stores are output `+4/+8`.

## Gate

This brings shallow x87 semantic resolution to 14/18 candidates. Four pointer-chain candidates remain open:

```text
FUN_0075c0d0
FUN_007b8630
FUN_0075ada0
FUN_007b7840
```

Accordingly `x87_zero_init_semantics_complete`, SSE/vector copy-init, deeper direct aliases, indirect/callback aliases, slot0, slot1, aggregate P1.3 and provider removal all remain fail-closed. Provider count remains 7.
