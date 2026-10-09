# Process 1D / P1.3D — final shallow x87 pointer-chain closure

## Scope

Merged P1A #1738 bounded 18 direct-depth<=4 `FLDZ -> FST/FSTP` candidates. Merged #1740 rejected 9 and merged #1742 rejected 5 more. This P1D slice consumes those 14 results without changing P1A ownership and adjudicates only the final four pointer-chain candidates for selected slot3 `HDVehicle+0x28b8..+0x28bf`:

- `FUN_0075c0d0`
- `FUN_007b8630`
- `FUN_0075ada0`
- `FUN_007b7840`

The proof is fail-closed. Reachability and numeric offset equality never establish selected-HDVehicle identity.

## Retail result

The hash-locked verifier pins 37 exact retail machine anchors for the four final candidates.

- `FUN_0075c0d0` is path-infeasible on its only shallow root path: `FUN_00770e80` passes literal zero as `FUN_007b1790` arg2, while `FUN_007b1790` calls `FUN_0075c0d0` only when that argument is nonzero.
- `FUN_0075ada0` receives four exact caller stack-local output pointers: `EBP-0x8`, `EBP-0xc`, `EBP-0x18`, and `EBP-0x24`.
- `FUN_007b8630` operates in the BODY recovery domain. The shallow path begins from vehicle `+0x339c`; `SHIFT.GlobalVehicleBodyOwnerIdentity/1` proves that field contains a pointer to a separate BODY-array owner rather than the vehicle base. The callee then follows nested pointers before clearing BODY motion/accumulator lanes.
- `FUN_007b7840` is reached by the proven relation-refresh BODY chain `FUN_00770e80 -> FUN_007b8810 -> FUN_007b8630 -> FUN_007b8260 -> FUN_007b7840`. Existing BODY contracts classify it as a broader BODY lifecycle/state writer and the bounded call forwards BODY storage, not an inline wheel target.

Together with merged #1740 and #1742, all 18 shallow x87 zero-init candidates are negative for selected slot3.

## Gate

```text
slot3 shallow x87 depth<=4 complete = true
x87 candidates                       = 18
resolved by merged P1A              = 14
resolved here                        = 4
x87 candidates rejected              = 18
selected slot3 x87 writer found       = false
SSE/vector copy-init complete         = false
deeper direct aliases complete        = false
indirect/callback aliases complete    = false
slot3 writer provenance proven        = false
P1.3D complete                        = false
provider count                        = 7
```

## Verify

```bash
python3 tools/ghidra/verify_p1d_slot3_x87_remaining.py /path/to/SHIFT.exe
```

The verifier fails closed on retail SHA-256 drift or any of the 37 exact receiver/call/store anchors changing.

## Next step

Bound the shallow SSE/vector copy/zero-init surface. After that, widen only deeper direct or indirect/callback paths that carry an exact selected-wheel-derived alias; do not expand from callgraph reachability alone.
