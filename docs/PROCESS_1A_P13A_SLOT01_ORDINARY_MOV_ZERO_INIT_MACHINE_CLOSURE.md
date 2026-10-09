# Process 1A / P1.3A — shallow ordinary-MOV zero-init closure

## Scope

After unrolled copy semantics closed, the next bounded class for slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` is straight-line ordinary `MOV` zero initialization outside backward-branch loops.

The analyzer follows the four recovered wheel/physics roots to direct-call depth four, tracks immediate-zero and zero-register stores, groups non-stack destinations by base expression, and keeps clusters with at least eight contiguous destination bytes. x87 `FLDZ/FST*` and SSE/vector zero stores are intentionally separate follow-up classes.

## Retail result

Authoritative PC retail 1.02 plus the Drive Ghidra index produce exactly six functions. All six reject by exact receiver provenance:

- `FUN_00887580` — fixed singleton `0x00c29640`, already pinned by the inline-REP closure.
- `FUN_00647a10` — called immediately on that same singleton receiver; detected zero stores stay within local `+0x20..+0x150`.
- `FUN_0070fae0` — constructor for singleton `DAT_00c104e0`, explicitly identified as **Physics Manager**, vtable `0x00b04524`.
- `FUN_0087aa00` — clears record containers under the separately proven `HDVehicle+0x6730` service subobject: `+0x24 + i*0x30` and final `+0xe4`.
- `FUN_00886e10` — fixed singleton nested receiver `0x00c29d4c` (`0x00c29640+0x70c`).
- `FUN_0088f110` — fixed singleton nested receiver `0x00c29b98` (`0x00c29640+0x558`).

None is selected HDVehicle slot0/slot1 storage.

## Gate

```text
shallow ordinary MOV zero-init depth<=4 complete = true
candidate functions                              = 6
rejected candidates                              = 6
selected slot0/slot1 writer found                = false
x87 zero-init complete                           = false
SSE/vector zero-init complete                    = false
deeper direct aliases ruled out                  = false
indirect/callback aliases ruled out               = false
slot0 complete                                   = false
slot1 complete                                   = false
P1.3 complete                                    = false
provider count                                   = 7
```

## Next step

Bound shallow x87 `FLDZ/FST*` zero-initialization and SSE/vector copy-init surfaces. Only then widen to deeper direct or indirect/callback aliases, and only from exact selected-HDVehicle-derived destinations.
