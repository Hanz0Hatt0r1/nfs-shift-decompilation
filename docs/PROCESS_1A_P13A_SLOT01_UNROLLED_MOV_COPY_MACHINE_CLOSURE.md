# Process 1A / P1.3A — shallow unrolled MOV semantic closure

## Scope

`SHIFT.P1A.P13ASlot01UnrolledMovCopyFrontier/1` bounds straight-line ordinary `MOV` copy sequences reachable within four direct-call edges from the P1.3A wheel/physics roots. It reports 11 functions. This closure adjudicates all 11 by exact PC-retail receiver/destination provenance.

## Result

All 11 candidates are negative for selected `HDVehicle+0x938` / `HDVehicle+0x13b8`:

- `FUN_0076e560` writes a service/message record returned through `FUN_0070ab90`, not the HDVehicle receiver.
- `FUN_007b0710` writes `+0x48/+0x4c` in the collision-provider `0x00c1bae0` surface-record ring proven by `SHIFT.Fun0074f560CollisionProviderMachineProof/1`.
- `FUN_00403d00` copies into a service-produced output record returned through a local out pointer.
- `FUN_004e9380` writes entries owned by fixed global table `0x00c1b9e0`.
- `FUN_00633290` initializes a service record obtained by lookup/allocation and returns its payload.
- `FUN_006333f0` maintains the already-proven separate service object's linked-list nodes.
- `FUN_0075a8d0` is genuinely HDVehicle-rooted, but its explicit output pointer is exactly `HDVehicle+0x40c8`; the 16-byte cluster lands at `+0x40c8..+0x40d7`.
- `FUN_007b0580` receives `EDX=EBP-0x58`; its destination is stack-local.
- `FUN_0064fef0` populates an allocator/service-owned record returned by `FUN_0062f6f0`.
- `FUN_007b0450` is a static callgraph edge that is infeasible on the bounded P1A path: the caller passes the controlling optional argument as literal zero.
- `_LocaleUpdate` is reached only through `_wprintf -> FUN_0090db22` and updates CRT locale state.

The verifier pins the retail SHA-256, all 11 frontier names, 76 exact byte windows, and 16 rel32 transfers.

## Gate

```text
shallow unrolled MOV candidates           = 11
semantically rejected                     = 11
shallow unrolled MOV semantics complete   = true
selected-HDVehicle slot writer found      = false
straight-line zero-init complete          = false
SSE/vector custom-copy complete           = false
deeper direct alias paths complete        = false
indirect/callback alias paths complete    = false
slot0 complete                            = false
slot1 complete                            = false
P1.3 complete                             = false
provider count                            = 7
```

## Next step

Inventory straight-line zero-init ranges and shallow SSE/vector copy-init sequences. Only after those bounded classes close should P1A widen to deeper or indirect carriers, and only from concrete selected-HDVehicle-derived destinations.
