# Process 1 — correction: BMW `offset33b` additional-mass object frontier

## Correction to PR #1247

The original `SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1` contract is
**retracted**. It confused two distinct objects:

1. a PhysicsParticipant **manager record** with stride `0x1fa0`; and
2. the separately allocated **actual PhysicsParticipant object** stored in
   `record[0]`.

`FUN_00714360 -> FUN_00552dd0` does clear state inside the manager record, but
that does **not** prove the value consumed by HighDetailVehicle initialization.
The old `ready=true` bootstrap-zero claim must not be used.

The historical analyzer path is retained only so existing invocations fail
closed and emit the corrected frontier:

```text
SHIFT.BMWOffset33bAdditionalMassActualObjectFrontier/1
```

## Correct object chain

The source-backed allocation/construction sequence is:

```text
manager record
  |
  | FUN_007125e0
  |   allocate 0x2b90 bytes
  |   FUN_0072ed20(actual PhysicsParticipant)
  |   record[0] = actual PhysicsParticipant
  v
actual PhysicsParticipant
  |
  | FUN_0072ed20
  |   FUN_0079c1c0(actual_participant + 0x340)
  v
embedded Vehicle @ actual_participant+0x340
```

HighDetailVehicle initialization then copies:

```text
HDVehicle+0x3428 = (double)*(float *)(*record + 0xba0)
```

Therefore the real additional-mass source is:

```text
actual PhysicsParticipant+0xba0
== embedded Vehicle+0x860
```

It is **not** manager-record `+0xba0`.

## What remains proven

The existing `SHIFT.BMWOffset33bStoreProvenance/1` store frontier remains valid:
`FUN_0076b280` is still the source-backed producer of
`HDVehicle+0x33b0/+0x33b8/+0x33c0`.

Only the #1247 zero-value proof is withdrawn.

The corrected analyzer now reports:

```text
ready = false
status = additional-mass-actual-object-producer-unresolved
offset33b_additional_mass_bootstrap_zero_ready = false
offset33b_additional_mass_term_can_be_elided_for_first_bootstrap = false
BMW_numeric_offset33b_ready = false
```

## Next exact proof target

Trace the last writer/value reaching:

```text
embedded Vehicle+0x860
```

between construction of the actual `0x2b90` PhysicsParticipant object and the
HighDetailVehicle initialization read. The relevant constructor frontier is now
finite:

```text
FUN_007125e0
  -> FUN_0072ed20
       -> FUN_0079c1c0(actual_participant+0x340)
            -> FUN_0079bfd0(...)
```

A separate constructor fact has also been observed in the retail decompiler:
`FUN_0079bfd0` initializes embedded `Vehicle+0x1c0` to zero. That concerns the
`reference_point.y` side of the `FUN_0076b280` formula and does not establish
`Vehicle+0x860`; it must be promoted through its own fail-closed proof before a
numeric evaluator consumes it.

## Usage

```bash
python3 tools/ghidra/analyze_bmw_offset33b_additional_mass_bootstrap_zero.py \
  out/shift_ghidra_database \
  --json-out out/bmw_offset33b_additional_mass_actual_object_frontier.json
```

No original-game execution is required for this correction. The purpose of this
step is to restore soundness: no numeric BODY0/Vehicle bind gate is allowed to
consume the retracted manager-record zero assumption.
