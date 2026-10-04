# Process 1 — BMW `offset33b` Vehicle reference-Y bootstrap-zero proof

## Blocker reduced

The BMW `offset33b` producer builds one reference-point component from a field
reached through the actual PhysicsParticipant.  The exact pointer arithmetic is:

```text
actual PhysicsParticipant + 0x500
== embedded Vehicle + 0x1c0
```

The base Vehicle constructor writes this field to zero before the first
`Vehicle::InitVehicle` / HighDetailVehicle transaction.  This removes another
anonymous runtime scalar from the first numeric `offset33b` evaluation.

Contract:

```text
SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_vehicle_reference_y_bootstrap_zero.py
```

## Exact constructor chain

The proof fingerprints and validates:

```text
FUN_007125e0(manager_record)
  -> FUN_0072ed20(actual_participant)
       -> FUN_0079c1c0(actual_participant + 0x340)
            -> FUN_0079bfd0(Vehicle)
```

In retail `FUN_0079bfd0`:

```text
Vehicle dword[0x70] = 0
```

and `0x70 * 4 == 0x1c0`.  Therefore:

```text
actual_participant+0x500
= Vehicle+0x1c0
= float32-compatible zero dword
```

for the first constructed Vehicle.

## Join to `FUN_0076b280`

The first Restart/InitVehicle path is frozen through exact function fingerprints
and direct-call sites:

```text
PhysicsParticipant::Restart
  -> FUN_0074d640
  -> FUN_00797fd0(Vehicle, ...)
  -> Vehicle::InitVehicle
       -> FUN_00a62690
       -> FUN_0076df50
            retains manager record at HDVehicle+0x3fe8
            -> FUN_0076b280
```

`FUN_0076b280` resolves `**(HDVehicle+0x3fe8)` back to the actual participant and
uses the float at `actual+0x500` in the Y reference expression.  The reviewed
retail expression is therefore reduced from:

```text
Vehicle_reference_y - effective_graphical_offset_y
```

to:

```text
-effective_graphical_offset_y
```

The effective graphical-offset value is deliberately **not** assigned a number
by this contract.  That is a resource/init root for the next numeric evaluator.

## Usage

```bash
python3 tools/ghidra/analyze_bmw_offset33b_vehicle_reference_y_bootstrap_zero.py \
  out/shift_ghidra_database \
  --json-out out/bmw_offset33b_vehicle_reference_y_bootstrap_zero.json
```

The analyzer consumes only the canonical retail Ghidra `binary.json`,
`functions.jsonl`, and `callgraph.jsonl` and fails closed on executable,
fingerprint, calling-convention, constructor-chain or InitVehicle/HDVehicle join
drift.

## Deliberate non-claims

This contract does not prove the independent `Vehicle+0x860` additional-mass
root; that has its own actual-object allocator proof.  It does not assign the
loaded graphical offset, remaining masses/geometry, the final three
`HDVehicle+0x33b*` doubles, BODY0 numeric bind matrix, bind frame, or world
transform.

These gates remain false:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

## Next step

The Y reference is now reduced to a single resource-backed value.  The next
numeric `offset33b` work should join `effective_graphical_offset_y` and the
remaining mass/geometry roots to the already materialized BMW HDV/VDF/SDF/tire
inputs rather than introduce another runtime-state assumption.
