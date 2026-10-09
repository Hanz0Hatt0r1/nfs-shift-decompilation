# Process 1A / P1.3A — shallow receiver-loop custom init closure

## Scope

After the REP and canonical bare-string closures, ordinary `MOV`/x87 store loops remain a separate custom copy/init class. This bounded pass scans functions reachable within four direct-call edges from the four P1.3A wheel/physics roots. A candidate must capture entry `ECX` in `ESI`, `EDI`, or `EBX`, contain a machine-level backward branch, and issue a `MOV`/`FST`/`FSTP` store through that syntactic receiver alias inside the loop.

The detector deliberately over-approximates alias lifetime. Exact retail transfer, not the syntactic match, decides identity.

## Result

Eight functions match. All eight are rejected as writers of selected `HDVehicle+0x938` or `HDVehicle+0x13b8`:

- `FUN_00765c40` — already exhausted by `SHIFT.Fun00765c40DirectMachineWriteSurface/1`; detected receiver-loop stores are `+0x407c/+0x3660/+0x3678`.
- `FUN_0075bf60` — receives the HDVehicle root, but the loop writes only bytes `HDVehicle+0xea..+0xf9`.
- `FUN_007b0710` — receives stack local `EBP-0xe0`; its detected `+0x30` store remains stack-local.
- `FUN_006333f0` — receives the separate service object loaded from `FUN_0070fe90()+0x288`; it maintains linked-list fields `+0x18/+0x1c/+0xb4/+0xb8`.
- `FUN_007b0600` — receiver is fixed image-global `0x00c1b9e0`.
- `FUN_00a62780` — entered through `HDVehicle+0x6730`, but the detector's `EDI` alias is killed by `mov edi,[esi+0xc]` before the matched store; the store is node cleanup, not an HDVehicle write.
- `FUN_00638020` — receiver comes from `[FUN_0065b130()+0x5c]`, an allocator/service domain reached through the separate `FUN_0070fe90()+0x288` object.
- `FUN_0076f030` — receives the HDVehicle root, but the detected loop state write is `HDVehicle+0x3fe0`.

The analyzer hash-locks both authority files and pins 47 exact byte windows plus 15 rel32 transfers supporting these receiver joins.

## Gate

```text
shallow receiver-loop depth<=4 surface complete = true
candidate functions                              = 8
candidates rejected                              = 8
selected-HDVehicle writer found                  = false
all ordinary/custom copy-init ruled out          = false
indirect dispatch ruled out                      = false
deeper direct paths ruled out                    = false
slot0 complete                                   = false
slot1 complete                                   = false
P1.3 complete                                    = false
provider count                                   = 7
```

## Next step

Continue with acyclic unrolled `MOV`/`FST` sequences and loops whose destination alias is not the entry receiver alias. Only then widen to deeper or indirect carriers, and only from a concrete selected-HDVehicle-derived destination.
