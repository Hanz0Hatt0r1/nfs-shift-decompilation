# Process 1A / P1.3A — shallow x87 zero-init frontier

## Scope

The ordinary-MOV zero-init class is separate from x87 zero stores. This frontier scans `FLDZ` followed by `FST`/`FSTP` to non-stack destinations, excludes backward-branch loop bodies, and follows the four recovered wheel/physics roots to direct-call depth four.

A retained cluster must cover at least eight contiguous destination bytes. This is navigation evidence only: a zero store is not promoted to selected-HDVehicle identity from reachability or offset coincidence.

## Retail result

Authoritative PC retail 1.02 and the Drive Ghidra index produce exactly **18 candidate functions**:

`FUN_00763570`, `FUN_00770e80`, `FUN_00755a60`, `FUN_00760b50`, `FUN_00766510`, `FUN_0076e560`, `FUN_0075c0d0`, `FUN_007aa940`, `FUN_007b8630`, `FUN_0075ada0`, `FUN_00647a10`, `FUN_0070fae0`, `FUN_0075afc0`, `FUN_0076f030`, `FUN_007876e0`, `FUN_007ade70`, `FUN_007b7840`, `FUN_0088f110`.

The evidence records shortest paths plus exact `FST/FSTP` sites and destination bases for each candidate. Several are directly HDVehicle-rooted but write far fields; others use child/output/singleton receivers. Those semantics are intentionally adjudicated in the next slice rather than inferred by this inventory.

## Gate

```text
shallow x87 zero-init frontier captured = true
candidate functions                     = 18
x87 semantics complete                  = false
SSE/vector copy-init complete           = false
deeper direct aliases ruled out         = false
indirect/callback aliases ruled out      = false
slot0 complete                          = false
slot1 complete                          = false
P1.3 complete                           = false
provider count                          = 7
```

## Next step

Adjudicate all 18 x87 candidates by exact receiver/destination provenance. Then bound shallow SSE/vector copy-init before widening to deeper direct or indirect/callback aliases.
