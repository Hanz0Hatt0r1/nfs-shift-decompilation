# Process 1A / P1.3A — carrier-surface composition

## Scope

This handoff composes already-merged machine contracts for the current slot0/slot1 alias frontier. It does not introduce a new physical class identity or infer semantics from callgraph adjacency.

The bounded surface now includes:

- known `FUN_00765c40` wheel-derived aliases (`wheel+0x678`, `wheel+0x7a8`) and post-derived identity inventory;
- callee-facing lifetimes of `HDVehicle+0x3430/+0x35c8/+0x35f8/+0x36e0`;
- x86 REP/string bulk-opcode scans inside all 16 exact-root carrier bodies;
- the same opcode class across their 82 unique immediate direct callees;
- every CALL instruction physically present in the 16 carriers, including the two call-through-memory sites in `FUN_00770e80`.

## Composed result

`FUN_00765c40` remains negative for selected slot0/slot1 identity across the known derived families. The four HDVehicle-local arrays terminate without pointer escape or wheel-root reconstruction. The positive runtime-created-node backpointers under the distinct `HDVehicle+0x6730` manager/subobject remain explicitly preserved and therefore do **not** authorize a global runtime-pointer closure.

The exact carrier machine surface is:

```text
exact-root carriers                         16
carrier instructions                       5178
REP/MOVS/STOS/LODS/SCAS/CMPS hits          0
immediate direct callsites                 214
unique immediate direct callees             82
direct-callee instructions                 9159
direct-callee bulk-opcode hits                0
call-through-memory sites                     2
total machine callsites                    216
runtime-unknown call targets                  0
```

The two `FUN_00770e80` call-through-memory sites are not unknown callbacks:

- `0x00770ec4` resolves through IAT slot `0x00aa60b4` to `KERNEL32!InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 1)`;
- `0x00770f41` resolves through the same IAT slot to `KERNEL32!InterlockedExchange((LONG volatile*)(HDVehicle+0x4020), 2)`.

Both operate on scalar `HDVehicle+0x4020`. They do not materialize or persist selected wheel roots and are disjoint from slot0 `HDVehicle+0x938..+0x93f` and slot1 `HDVehicle+0x13b8..+0x13bf`.

## Gate

```text
FUN_00765c40 known derived/local-array subset complete = true
known selected-slot writer                              = false
known selected-wheel pointer escape                     = false
non-wheel +0x6730 runtime backpointer                  = true
16-carrier direct bulk-opcode subset                    = true
82 immediate-direct-callee bulk-opcode subset           = true
16-carrier machine call-target surface                  = true
FUN_00770e80 aa60b4 import-indirect subset             = true
runtime-unknown call target in 16 carriers              = false
aggregate/bulk alias stores globally ruled out          = false
runtime-generated/copied selected-wheel pointers        = false
callbacks/indirect entry globally ruled out             = false
stored-or-escaped aliases globally ruled out            = false
slot0 complete                                          = false
slot1 complete                                          = false
P1.3 complete                                           = false
provider count                                          = 7
```

## Limits

Zero string-opcode hits cover only the 16 exact-root carrier bodies and their immediate direct callees. Hand-unrolled scalar/SIMD copies, deeper descendants, reconstructed pointers, callbacks/indirect entry outside the bounded carrier callsites, and runtime-generated/copied selected-wheel aliases remain open.

The positive `HDVehicle+0x6730` runtime-created-node backpointers remain part of the evidence as a distinct non-wheel pointer-persistence family; they are not silently discarded to make the global gate pass.

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_carrier_surface_composition.py \
  --output evidence/p1a_p13a_slot01_carrier_surface_composition.json
```

## Next step

Trace runtime-generated/copied selected-wheel pointers and callback/indirect-entry surfaces outside the bounded 16-carrier callsites. Do not promote the global stored-or-escaped-alias gate, slot0/slot1 completion, or aggregate P1.3 until those remaining surfaces are exhausted.
