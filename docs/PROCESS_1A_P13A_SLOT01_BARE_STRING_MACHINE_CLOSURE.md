# Process 1A / P1.3A — canonical bare MOVS/STOS closure

## Scope

After closing shallow `REP MOVS/STOS`, the next bounded compiler-copy class is canonical x86 string instructions without a REP prefix: `A4/A5`, `AA/AB`, and the operand-size forms `66 A5/66 AB`.

The retail scan finds 594 such instruction sites; 369 map into 76 sized Ghidra functions. Only two functions are reachable within four direct edges of the four P1.3A wheel/physics roots.

## Result

`FUN_009108ca` is a CRT stack-copy path. It uses sources `EBP+0x8` / `EBP+0x10` and destinations `EBP-0x86` / `EBP-0x7e`; all four bare `MOVSD` string instructions therefore copy stack arguments into stack locals.

`FUN_00634240` contains two bare tail copies after its already-bounded REP copies. `EDI` remains a cursor inside the fixed image-global buffer rooted at `0x00bf9b30`; the sources are fixed image addresses `0x00aebefc` or `0x00aebee0`. These operations are not selected-HDVehicle writes.

## Gate

```text
canonical bare string depth<=4 surface complete = true
candidate functions                              = 2
candidates rejected                              = 2
selected-HDVehicle writer found                  = false
all non-REP custom copies ruled out              = false
indirect copy dispatch ruled out                 = false
deep direct paths ruled out                      = false
slot0 complete                                   = false
slot1 complete                                   = false
P1.3 complete                                    = false
provider count                                   = 7
```

## Next step

Continue with ordinary MOV/unrolled/custom copy or initialization loops and deeper/indirect aliases. Exact selected-HDVehicle-derived destination provenance remains mandatory before any slot gate changes.
