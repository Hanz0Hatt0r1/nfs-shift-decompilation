# Process 1D — slot3 exact local `+0x538` handoff

## Purpose

P1.3D owns selected `HDVehicle+0x28b8` writer provenance. The retail consumer topology is slot-parametric:

```text
FUN_00758b50 -> FUN_00755950
this = HDVehicle + 0x400 + slot*0xa80
FUN_00755950 reads f64 [this + 0x538]
```

For slot 3:

```text
HDVehicle + 0x400 + 3*0xa80 = HDVehicle + 0x2380
HDVehicle + 0x2380 + 0x538 = HDVehicle + 0x28b8
```

Two merged P1A whole-image machine contracts operate on this same local byte range and are reusable without transferring P1A shard ownership:

- `SHIFT.P1A.P13ASlot01Wheel538ForwardingFrontier/1`
- `SHIFT.P1A.P13ASlot01OverlapStoreClosure/1`

## Exact `+0x538` materializer surface

The retail whole-image scan contains 43 exact `+0x538` scalar uses and exactly four positive address materializers:

```text
0x006c1b8a  lea ebx,[ecx+0x538]
0x008fe259  lea ecx,[esi+0x538]
0x008fe2c4  lea ebx,[esi+0x538]
0x00958c28  lea eax,[ebx+0x538]
```

Merged machine provenance rejects all four as selected wheel-runtime f64 producers: internal cursor, teardown reader, separately allocated pool-object initializer, and `FMOD IT Codec` callback buffer respectively.

The positive qword literal store is:

```text
0x00761b67  fstp qword [esi+0x538]
```

Its proven base is `HDVehicle+0x748+slot*0xa80`; slot 3 therefore normalizes to `HDVehicle+0x2c00`, not `HDVehicle+0x28b8`.

## Exact literal store overlap surface

P1A #1723 additionally scans by byte-range overlap, not just exact `+0x538` operands. For local f64 bytes `[+0x538,+0x540)` it finds:

```text
overlapping stores     25
partial-width stores   24
qword-or-wider stores   1
functions              13
unowned instructions    0
```

This includes low-DWORD, high-DWORD (`+0x53c`) and wider overlapping writes. The 12 partial-writer functions are:

```text
FUN_00481e20  FUN_004876f0  FUN_004dbdb0  FUN_0051f4b0
FUN_005cb010  FUN_00748280  FUN_007a1fc0  FUN_007a25d0
FUN_007c0db0  FUN_00860bf0  FUN_008614c0  FUN_008620b0
```

Every partial-store receiver is rejected by exact merged provenance as a different object domain; the one qword store is the already-rejected `FUN_007618f0` path. Because the local range is slot-parametric, these receiver-domain rejections also remove them as selected slot3 writers.

## Closed sub-surfaces

```text
slot3 exact local +0x538 materializer/callee subset = complete
slot3 exact literal overlap-store surface           = complete
slot3 direct positive qword +0x538 store             = rejected
```

## Remaining frontier

```text
computed-address stores without literal overlap      = open
escaped aliases                                      = open
base-plus-delta aliases                              = open
bulk-copy / memory-init destinations                 = open
indirect dispatch                                    = open
selected-root slot3 writer provenance                = false
P1.3D complete                                       = false
provider count                                       = 7
```

Numeric offset equality is never object identity. A future candidate must prove selected-HDVehicle root provenance and exact target-byte coverage.

## Reproduction

```bash
python3 tools/ghidra/build_p1d_slot3_wheel538_handoff.py \
  evidence/p1a_p13a_slot01_wheel538_forwarding_frontier.json \
  evidence/p1a_p13a_slot01_overlap_store_closure.json \
  evidence/fun_00755950_absolute_consumed_field_machine_proof.json \
  --output out/p1d_slot3_wheel538_materializer_handoff.json
```

The builder fails closed on drift in the consumer slot map, local field width, 43-use/four-materializer surface, qword normalization, 25-store overlap inventory, or upstream rejection gates.

## Next step

Trace computed destinations and escaped/base-plus-delta aliases, then overlapping copy/init and indirect-dispatch paths capable of covering selected `HDVehicle+0x28b8..+0x28bf`.
