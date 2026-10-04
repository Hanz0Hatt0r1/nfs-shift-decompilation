# Process 1 — actual BMW `offset33b` additional-mass bootstrap-zero proof

## Blocker reduced

The BMW `offset33b` producer reads an extra scalar through the current manager
record, but the storage is **not** manager-record `+0xba0`.  The manager record
holds a pointer at offset zero to a separately allocated PhysicsParticipant.
The real read is:

```text
actual PhysicsParticipant + 0xba0
== embedded Vehicle + 0x860
```

The earlier manager-record zero proof was retracted by
`SHIFT.BMWOffset33bAdditionalMassActualObjectFrontier/1`.  This contract closes
the real fresh-bootstrap value through the allocator path instead of reusing that
invalid object-base argument.

Contract:

```text
SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_actual_additional_mass_bootstrap_zero.py
```

## Static proof chain

The exact retail Ghidra database proves/fingerprints this chain:

```text
FUN_007125e0(manager_record)
  |
  |-- FUN_00886900(0x2b90, pool, 0x20)
  |      |-- FUN_00638020(..., flags)
  |      |      |-- FUN_00657ab0(..., flags)
  |      |      `-- fallback FUN_00637f50 -> FUN_00657ab0
  |      `-- default pool FUN_006382b0 -> FUN_00638020
  |
  |   FUN_00657ab0: if (flags & 0x20) memset(allocation, 0, requested_size)
  |
  `-- FUN_0072ed20(actual_participant)
          `-- FUN_0079c1c0(actual_participant + 0x340)
                  `-- FUN_0079bfd0(Vehicle)
```

Therefore the complete fresh `0x2b90` PhysicsParticipant allocation starts at
zero, including byte range `+0xba0..+0xba3`.

The same retail fingerprints and direct callsites freeze the first Restart path:

```text
FUN_0074ddc3 PhysicsParticipant::Restart
  -> FUN_0074d640(participant)        # reviewed target non-writer
  -> FUN_00797fd0(Vehicle, ...)       # reviewed target non-writer
  -> FUN_00798df0 Vehicle::InitVehicle
       -> FUN_00a62690(Vehicle, ...)  # reviewed target non-writer
       -> FUN_0076df50(...)
            reads actual_participant+0xba0
            converts float32 to double
            stores HDVehicle+0x3428
            -> FUN_0076b280 offset33b producer
```

No reviewed instruction before the `FUN_0076df50` read overwrites the target
four-byte storage.  Thus for a freshly allocated first-bootstrap participant:

```text
actual_participant+0xba0 = Vehicle+0x860 = float32 +0.0
```

and the corresponding additional-mass term can be omitted when evaluating the
first BMW `offset33b` vector.

## Usage

```bash
python3 tools/ghidra/analyze_bmw_offset33b_actual_additional_mass_bootstrap_zero.py \
  out/shift_ghidra_database \
  --json-out out/bmw_offset33b_actual_additional_mass_bootstrap_zero.json
```

The analyzer requires `binary.json`, `functions.jsonl`, and `callgraph.jsonl` from
the canonical retail Ghidra export.  It fails closed on executable identity,
function fingerprint, calling-convention, direct-call, or callsite drift.

## Deliberate non-claims

This proof is intentionally limited to a **fresh actual PhysicsParticipant first
bootstrap**.  It does not prove that a reused/reinitialized actual participant is
zeroed again after a later lifetime transition.  It also does not evaluate the
remaining HDV/VDF/SDF/tire geometry and mass roots.

These gates remain false:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

The correction contract for the historical manager-record mistake remains
fail-closed and is not replaced or reinterpreted by this proof.

## Next numeric target

With the real additional-mass scalar removed for first bootstrap, the next
`offset33b` work should evaluate only the source-backed resource/geometry roots.
An independent constructor fact also shows `Vehicle+0x1c0` begins at zero; that
should be promoted in its own narrow contract before reducing the Y reference
point to the loaded graphical-offset term.
