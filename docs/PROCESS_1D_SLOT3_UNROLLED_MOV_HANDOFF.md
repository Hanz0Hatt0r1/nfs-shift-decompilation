# Process 1D — slot3 shallow unrolled MOV handoff

## Scope

P1A #1734 machine-adjudicated all 11 straight-line ordinary-MOV copy candidates from direct depth <=4. This P1D handoff consumes only the receiver/destination conclusions that are independent of slot0/slot1 ownership and applies them to selected slot3 `HDVehicle+0x28b8`.

The P1A contract remains owned by Process 1A. No P1A gate is changed here.

## Authority

```text
PC retail 1.02 SHIFT.exe SHA-256
  eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1

upstream
  SHIFT.P1A.P13ASlot01UnrolledMovCopyMachineClosure/1
```

Retail machine transfer is semantic authority. The upstream direct-call frontier is navigation only.

## Result

All 11 bounded candidates are rejected as selected slot3 writers:

| Function | Proven destination domain |
| --- | --- |
| `FUN_0076e560` | service/message record returned by a separate service object |
| `FUN_007b0710` | fixed `0x00c1bae0` collision-provider surface-record ring |
| `FUN_00403d00` | service-owned output record |
| `FUN_004e9380` | fixed-global `0x00c1b9e0` hash-table entry |
| `FUN_00633290` | service record allocation/lookup result |
| `FUN_006333f0` | separate service linked-list maintenance |
| `FUN_0075a8d0` | genuine HDVehicle output at exactly `+0x40c8..+0x40d7` |
| `FUN_007b0580` | caller stack-local output structure |
| `FUN_0064fef0` | allocator/service-owned returned record |
| `FUN_007b0450` | bounded static edge is path-infeasible because the controlling optional output argument is literal zero |
| `_LocaleUpdate` | CRT locale state |

The one candidate whose destination is genuinely HDVehicle-rooted is especially useful for the slot3 decision: `FUN_0075a8d0` writes `HDVehicle+0x40c8..+0x40d7`, which cannot overlap selected slot3 `HDVehicle+0x28b8..+0x28bf`.

Therefore:

```text
slot3 shallow straight-line unrolled MOV depth<=4 = complete negative
candidate count                                  = 11
rejected count                                   = 11
selected slot3 writer found                      = false
```

## Fail-closed boundary

This does **not** close the full slot3 producer frontier. The following remain open:

```text
straight-line zero initialization   = open
SSE/vector/custom copy-init          = open
non-entry alias loops                = open
deeper direct aliases               = open
indirect/callback carriers           = open
slot3 writer provenance              = false
P1.3D complete                       = false
provider count                       = 7
```

Callgraph reachability and numeric offset equality are never treated as selected-HDVehicle identity.

## Reproduction

The handoff is regenerated from the merged P1A machine contract:

```bash
python3 tools/ghidra/build_p1d_slot3_unrolled_mov_handoff.py \
  evidence/p1a_p13a_slot01_unrolled_mov_copy_machine_closure.json \
  --output out/p1d_slot3_unrolled_mov_handoff.json
```

The builder fails closed on format/hash/candidate/rejection drift and pins the exact HDVehicle `+0x40c8` non-target case before emitting the P1D contract.

## Next step

Bound straight-line zero-init and shallow SSE/vector/custom transfer candidates. Trace non-entry aliases and deeper/indirect carriers only when an exact selected-wheel-derived destination survives receiver provenance.
