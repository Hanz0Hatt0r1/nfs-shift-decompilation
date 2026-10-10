# Process 1D — corrected 16-carrier call-target composition

## Correction

`SHIFT.P1D.Slot3CarrierCallTargetComposition/2` supersedes `/1` because `/1` inherited the old `aa60b4` interpretation and described on-disk value `0x00778052` as a static game-code target.

The corrected upstream contract `SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/2` proves that `0x00778052` is instead an `IMAGE_IMPORT_BY_NAME` RVA and that IAT slot `0x00aa60b4` is loader-resolved to `KERNEL32!InterlockedExchange`.

## Complete carrier-body CALL surface

Across the 16 exact-root carrier bodies:

```text
total machine CALL sites       = 216
immediate direct CALL sites     = 214
call-through-memory sites       = 2
runtime-unknown targets         = 0
```

The two non-immediate sites are:

```text
0x00770ec4  call DWORD PTR ds:0xaa60b4
0x00770f41  call DWORD PTR ds:0xaa60b4
```

Both resolve by PE import/IAT semantics to `KERNEL32!InterlockedExchange`.

Their bounded caller arguments are:

```text
0x00770ec4  InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)
0x00770f41  InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)
```

Therefore the carrier-body call-target count remains complete and the runtime-unknown target count remains zero, but **not** because `0x00778052` is executable game code. The corrected composition records zero `aa60b4` static game-code targets and two import-resolved callsites.

## Reproduce

```bash
python3 tools/ghidra/build_p1d_slot3_carrier_call_target_composition.py \
  evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json \
  evidence/p1d_slot3_static_indirect_aa60b4_closure.json \
  --output evidence/p1d_slot3_carrier_call_target_composition.json
```

The builder fails closed if:

- the 16-carrier direct-call count changes from 214;
- the two indirect site identities drift;
- the corrected `/2` import contract is missing;
- the import target stops being `KERNEL32!InterlockedExchange`;
- the on-disk import-name RVA is again treated as a code target.

## Gate

```text
16-carrier machine call-target surface complete       = true
runtime-unknown carrier-body target found             = false
runtime-unknown carrier-body target count             = 0
import-resolved carrier-body callsite count           = 2
aa60b4 static game-code target count                  = 0

other indirect entry ruled out                        = false
callbacks outside carriers ruled out                  = false
callee-created aliases ruled out                      = false
runtime-generated pointer stores ruled out            = false
stored-or-escaped aliases ruled out                   = false
slot3 writer provenance proven                        = false
P1.3D complete                                        = false
aggregate P1.3 complete                               = false
provider count                                        = 7
```

## Boundary

This is still a carrier-body closure only. It does not rule out callbacks, external indirect entry into carriers/callees, deeper callee indirection, reconstructed pointers, or runtime-generated/copied aliases.

Semantic ownership remains **Process 1D / P1.3D**. The `/2` composition exists to remove the stale `/1` import misinterpretation from the canonical proof graph.
