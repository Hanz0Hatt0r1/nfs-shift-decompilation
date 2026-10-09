# Process 1A / P1.3A — first deeper direct HDVehicle-root tranche

## Scope

After the direct-depth<=4 scalar, string, x87 and SSE/vector surfaces are bounded, the remaining direct frontier must not be widened blindly. This tranche starts from one exact boundary receiver already proven by merged P1A evidence: `FUN_0076f030` receives the selected HDVehicle root and has minimum direct-call depth four from the common P1.3 roots.

The Drive Ghidra index gives six direct callees. Two (`FUN_0076eb60`, `FUN_0090328a`) already have a shallower minimum path and were part of the existing depth<=4 surface. Exactly four are novel depth-five functions.

## Retail result

All four novel callees are rejected as selected slot0 `HDVehicle+0x938` / slot1 `HDVehicle+0x13b8` writers:

- `FUN_007534b0` — receives the exact HDVehicle root, but is a 0x35-byte read-only predicate. It reads `+0x3e58`, `+0x248`, `+0x3cd2`, and `+0x3da0` and performs no memory store.
- `FUN_0076ea70` — receives the exact HDVehicle root. Its direct HDVehicle writes are only byte `+0x3cd2` and qword `+0x3da8`. Other writes target a separate service record returned through the object loaded from `FUN_0070fe90()+0x288`.
- `FUN_00901310` — x87-to-integer runtime helper; it spills the incoming x87 value only to `[ESP]` and has no object destination.
- `FUN_0075bdc0` — receives the exact HDVehicle root but is read-only with respect to that receiver (`+0x3cd2`, `+0x248`); all x87 stores are EBP-relative stack locals.

The verifier pins the retail executable and Ghidra SQLite hashes, the exact six-callee surface, the four min-depth-five identities, exact byte windows, and rel32 targets.

## Gate

```text
FUN_0076f030 novel depth-5 callees complete = true
novel candidates                            = 4
rejected                                    = 4
selected slot0/slot1 writer found           = false
all deeper direct aliases ruled out         = false
indirect/callback aliases ruled out          = false
slot0 complete                              = false
slot1 complete                              = false
P1.3 complete                               = false
provider count                              = 7
```

## Next step

Enumerate the next exact HDVehicle/wheel receiver carriers at the shallow boundary and close only their novel deeper direct callees. Unrelated depth-five nodes remain navigation noise and are not promoted into the semantic frontier.
