# Process 1D — slot3 ordinary MOV zero-init handoff

## Scope

P1A #1735 bounded straight-line ordinary `MOV` zero stores outside backward loops within direct depth <=4. This P1D handoff consumes only the exact receiver/destination rejections that are independent of slot0/slot1 ownership and applies them to selected slot3 `HDVehicle+0x28b8`.

## Authority

```text
PC retail 1.02 SHIFT.exe SHA-256
  eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1

upstream
  SHIFT.P1A.P13ASlot01OrdinaryMovZeroInitMachineClosure/1
```

Retail machine transfer is semantic authority; reachability is navigation only.

## Result

All six bounded candidates are rejected as selected slot3 writers:

| Function | Proven receiver/destination domain |
| --- | --- |
| `FUN_00887580` | fixed singleton `0x00c29640` constructor |
| `FUN_00647a10` | base constructor on the same fixed singleton |
| `FUN_0070fae0` | distinct Physics Manager singleton `DAT_00c104e0` |
| `FUN_0087aa00` | records under exact `HDVehicle+0x6730` service subobject |
| `FUN_00886e10` | nested fixed singleton object at `0x00c29d4c` |
| `FUN_0088f110` | fixed singleton `+0x558` nested subobject |

The only HDVehicle-derived candidate operates under `HDVehicle+0x6730`, clearing fields in service records at `+0x24+i*0x30` and `+0xe4`. This receiver/range is disjoint from selected slot3 `HDVehicle+0x28b8..+0x28bf`.

```text
slot3 shallow ordinary-MOV zero-init depth<=4 = complete negative
candidate count                                = 6
rejected count                                 = 6
selected slot3 writer found                    = false
```

## Fail-closed boundary

Still open:

```text
x87 FLDZ/FST zero stores       = open
SSE/vector zero stores         = open
deeper direct aliases          = open
indirect/callback aliases      = open
slot3 writer provenance        = false
P1.3D complete                 = false
provider count                 = 7
```

No identity is inferred from numeric offset coincidence.

## Reproduction

```bash
python3 tools/ghidra/build_p1d_slot3_ordinary_mov_zero_init_handoff.py \
  evidence/p1a_p13a_slot01_ordinary_mov_zero_init_machine_closure.json \
  --output out/p1d_slot3_ordinary_mov_zero_init_handoff.json
```

The builder fails closed on format/hash/candidate/rejection drift and explicitly requires the merged `HDVehicle+0x6730` service-subobject proof.

## Next step

Bound shallow x87 `FLDZ/FST` and SSE/vector zero/copy-init surfaces. Widen to deeper or indirect paths only when exact selected-wheel-derived destination provenance survives machine-flow adjudication.
