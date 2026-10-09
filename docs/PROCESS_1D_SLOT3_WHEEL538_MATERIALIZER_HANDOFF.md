# Process 1D — slot3 exact local `+0x538` handoff

## Purpose

P1.3D owns selected `HDVehicle+0x28b8` (slot3) writer provenance. The same retail helper topology used by P1A is slot-parametric:

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

The merged P1A contract `SHIFT.P1A.P13ASlot01Wheel538ForwardingFrontier/1` is therefore reusable as whole-image machine evidence for the **exact local `+0x538` use/materializer surface**. Consuming that evidence does not transfer P1A shard ownership.

## Reused retail result

The authoritative whole-image scan contains:

```text
exact +0x538 scalar uses            43
positive LEA/address materializers   4
```

The four materializers are:

```text
0x006c1b8a  lea ebx,[ecx+0x538]
0x008fe259  lea ecx,[esi+0x538]
0x008fe2c4  lea ebx,[esi+0x538]
0x00958c28  lea eax,[ebx+0x538]
```

The merged machine proof rejects all four as selected wheel-runtime f64 producers:

- `FUN_006c1b80`: internal cursor; reconstructs the containing object and does not write qword at the materialized base.
- `FUN_008fe230`: teardown reader/releaser; callee has no receiver stores.
- `FUN_008fe2a0`: real initializer, but receiver is a separately allocated pool object with vptr `0x00b35e6c`, not selected HDVehicle wheel runtime.
- `FUN_0095883f`: `FMOD IT Codec` callback buffer, not HDVehicle wheel runtime.

## Direct positive qword store

The same whole-image contract identifies:

```text
0x00761b67  fstp qword [esi+0x538]
```

Its proven base is:

```text
HDVehicle + 0x748 + slot*0xa80
```

Therefore slot 3 normalizes to:

```text
HDVehicle + 0x748 + 3*0xa80 + 0x538
= HDVehicle + 0x2c00
```

This is not selected `HDVehicle+0x28b8`.

## What is now closed

```text
slot3 exact local +0x538 materializer/callee subset = complete
slot3 direct positive qword +0x538 store             = rejected
```

## What remains open

```text
base-plus-delta aliases without literal +0x538       = open
overlapping bulk-copy / memory-init destinations     = open
selected-root slot3 writer provenance                = false
retail input/control provenance                      = false
P1.3D complete                                       = false
provider count                                       = 7
```

Numeric offset equality is never object identity. A future candidate must prove exact selected-HDVehicle root provenance and f64/qword target-byte coverage.

## Reproduction

```bash
python3 tools/ghidra/build_p1d_slot3_wheel538_handoff.py \
  evidence/p1a_p13a_slot01_wheel538_forwarding_frontier.json \
  evidence/fun_00755950_absolute_consumed_field_machine_proof.json \
  --output out/p1d_slot3_wheel538_materializer_handoff.json
```

The builder fails closed if the consumer slot map, local field width, whole-image use count, materializer count, rejection status, or direct qword-store normalization changes.

## Next step

Trace only aliases that reach the selected slot3 bytes without embedding literal `+0x538`, plus overlapping copy/init destinations covering `HDVehicle+0x28b8`. Promote nothing without exact selected-root provenance.
