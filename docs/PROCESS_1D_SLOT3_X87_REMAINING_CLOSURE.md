# Process 1D / P1.3D — remaining shallow x87 zero-init closure

## Scope

Merged P1A #1738 bounded 18 direct-depth<=4 `FLDZ -> FST/FSTP` candidates. Merged #1740 machine-rejected the first 9. This P1D slice adjudicates the remaining 9 only for selected slot3 `HDVehicle+0x28b8..+0x28bf`.

The proof is fail-closed. Reachability and numeric offset equality never establish selected-HDVehicle identity. Machine receiver/argument flow, exact disjoint destinations, or existing merged BODY ownership contracts are required.

## Retail result

The hash-locked verifier pins 71 exact retail machine anchors.

- `FUN_00766510` receives the exact HDVehicle root from `FUN_0076d100`, but zeroes only `+0x40a0/+0x40a8/+0x40b0/+0x42b0/+0x4300`.
- `FUN_0075c0d0` is path-infeasible on its only shallow root path: `FUN_00770e80` passes literal zero as `FUN_007b1790` arg2, while `FUN_007b1790` calls `FUN_0075c0d0` only when that argument is nonzero.
- `FUN_007aa940`, `FUN_0075ada0`, `FUN_0075afc0`, and `FUN_007876e0` receive exact caller stack-local output objects.
- Both shallow `FUN_007ade70` calls are exact stack-local outputs: `EBP-0x38` at `0x007592b4` and `EBP-0x2c` at `0x007593eb`.
- `FUN_007b8630` and `FUN_007b7840` operate on the separate BODY owner/lifecycle domain. `SHIFT.GlobalVehicleBodyOwnerIdentity/1` proves `HDVehicle+0x339c` contains a pointer to a BODY-array owner that is not the vehicle base. `SHIFT.BodyFrameIntegrationStatic/1` independently classifies these functions as BODY recovery/state writers.

Together with merged #1740, all 18 shallow x87 zero-init candidates are negative for selected slot3.

## Gate

```text
slot3 shallow x87 depth<=4 complete = true
x87 candidates                       = 18
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

The verifier fails closed on retail SHA-256 drift or any of the 71 exact receiver/call/store anchors changing.

## Next step

Bound the shallow SSE/vector copy/zero-init surface. After that, widen only deeper direct or indirect/callback paths that carry an exact selected-wheel-derived alias; do not expand from callgraph reachability alone.
