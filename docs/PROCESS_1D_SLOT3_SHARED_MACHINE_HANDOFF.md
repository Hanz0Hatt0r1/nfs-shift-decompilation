# Process 1D — slot3 shared machine handoff

## Result

P1.3D slot3 consumes the same per-wheel local f64 field as slot0/slot1:

```text
wheel receiver = HDVehicle + 0x400 + slot*0xa80
local field    = +0x538..+0x53f
slot3          = HDVehicle + 0x28b8..+0x28bf
```

Several merged P1A contracts analyze machine surfaces whose rejection is independent of whether the selected wheel is slot0, slot1 or slot3. P1D consumes those proofs without transferring P1A ownership.

## Closed shared subsets

The whole-image exact-literal overlap-store inventory contains 25 stores in 13 functions. Every partial-width receiver is proven outside selected HDVehicle storage, and the single qword `FUN_007618f0` store is already normalized to slot3 `HDVehicle+0x2c00`, not `+0x28b8`. Therefore the exact-literal overlap-store class is closed negative for slot3.

The common direct-call roots are:

```text
FUN_00758b50
FUN_0076d100
FUN_00763570
FUN_00770e80
```

Merged named-memory navigation proves no named memcpy/memmove/memset-family target exists within depth 4 of any root. This is navigation evidence only.

Within the same shallow frontier, all five `REP MOVS/STOS` candidates are rejected by exact machine destination provenance (stack, fixed global, or fixed non-HDVehicle singleton), and both canonical bare MOVS/STOS candidates are rejected as stack/global copies. These receiver rejections are slot-agnostic.

## Gate

```text
slot3 exact-literal overlap-store subset       = complete
slot3 shallow named copy/set depth<=4          = empty (navigation only)
slot3 shallow REP MOVS/STOS depth<=4            = complete negative
slot3 shallow bare MOVS/STOS depth<=4           = complete negative
computed-address stores                         = open
escaped aliases                                 = open
ordinary MOV / custom unrolled copy/init        = open
deeper direct copy/init                         = open
indirect/callback dispatch                      = open
slot3 writer provenance                         = false
P1.3D complete                                  = false
provider count                                  = 7
```

## Ownership boundary

This handoff consumes these merged P1A contracts as retail machine proof:

- `SHIFT.P1A.P13ASlot01OverlapStoreClosure/1`
- `SHIFT.P1A.P13ASlot01InlineRepMachineClosure/1`
- `SHIFT.P1A.P13ASlot01BareStringMachineClosure/1`
- `SHIFT.P1A.P13ASlot01NamedMemoryFrontierEvidence/1`

P1A ownership is unchanged. Numeric offset or callgraph reachability is never promoted to selected-HDVehicle identity.

## Next step

Trace computed-address and escaped aliases derived from the proven selected wheel receiver. Only after such an alias is carried should P1D inspect ordinary MOV/unrolled custom copy/init ranges or deeper/indirect carriers. Promotion requires exact selected-root provenance and exact target-byte coverage.
