# Process 1 — reduced BMW `offset33b` static-proof runner

## Playable-slice blocker reduced

The numeric BMW BODY0 bind translation depends on three `offset33b` doubles. The
canonical reduced chain now composes only sound current proofs:

```text
SHIFT.BMWOffset33bStaticProofBundle/1
  -> one read-only/noanalysis FUN_0076b280 export
  -> exact HDVehicle STORE/value-root frontier

SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1
  -> actual PhysicsParticipant+0xba0 / embedded Vehicle+0x860 = +0.0f
     for fresh first bootstrap

SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1
  -> actual PhysicsParticipant+0x500 / Vehicle+0x1c0 = +0.0f
  -> Y reference reduces to -effective_graphical_offset_y

SHIFT.BMWOffset33bMemoryLoadProvenance/1
  -> exact memory LOAD base-origin/displacement/width worklist
```

The historical manager-record zero contract retracted by #1250 is not consumed.

Contract:

```text
SHIFT.BMWOffset33bReducedStaticProofBundle/1
```

Implementation:

```text
tools/ghidra/run_bmw_offset33b_reduced_static_proof.py
```

## One-command chain

```text
existing analyzed retail Ghidra project
        |
        v
run_bmw_offset33b_static_proof.py
        |
        +-> 01_fun_0076b280_instructions.jsonl
        +-> 02_bmw_offset33b_store_provenance.json
        |
        +-> analyze_bmw_offset33b_actual_additional_mass_bootstrap_zero.py
        |     +-> 03_bmw_offset33b_actual_additional_mass_bootstrap_zero.json
        |
        +-> analyze_bmw_offset33b_vehicle_reference_y_bootstrap_zero.py
        |     +-> 04_bmw_offset33b_vehicle_reference_y_bootstrap_zero.json
        |
        v
analyze_bmw_offset33b_memory_load_provenance.py
        |
        +-> 05_bmw_offset33b_memory_load_provenance.json
        |
        v
bmw_offset33b_reduced_static_proof_bundle.json
```

Only `FUN_0076b280` requires a Ghidra instruction export. The two bootstrap-zero
reductions use the saved retail metadata and exact reviewed/fingerprinted static
semantics.

## Invocation

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_bmw_offset33b_reduced_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_offset33b_reduced_static_proof
```

## Positive handoff

A fully bounded result exposes:

```text
offset33b_store_provenance_ready                         = true
offset33b_actual_additional_mass_bootstrap_zero_ready     = true
offset33b_vehicle_reference_y_bootstrap_zero_ready        = true
offset33b_memory_LOAD_frontier_ready                      = true
offset33b_exact_memory_field_worklist_ready               = true
```

and the decision becomes:

```text
semantic-resource-field-join
```

The next action is exactly:

```text
(base-origin expression, displacement, width)
  -> HDV/VDF/SDF/tire owner + semantic field
  -> exact BMW resource/init value
  -> supported numeric arithmetic
```

## Current reductions

The bundle carries two independent first-bootstrap reductions:

```text
actual_additional_mass_first_bootstrap_zero = true
additional_mass_term_elidable_for_first_bootstrap = true

vehicle_reference_y_first_bootstrap_zero = true
reference_y_reduced_to_negative_graphical_offset = true
```

The additional-mass zero is still not attached to an arbitrary `+0xba0/+0x860`
machine LOAD until exact pointer provenance joins that LOAD to the actual
PhysicsParticipant/embedded Vehicle object.

## Upstream blocking and failure behavior

Both metadata-only reductions run after a successfully completed base bundle.
The LOAD stage runs only when STORE/value-root provenance is ready. Downstream
failures preserve all earlier artifacts and write a fail-closed bundle naming the
failed stage.

## Deliberate non-claims

Even the strongest current reduced bundle keeps:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

The runner never reuses the retracted manager-record zero claim, never requests a
second Ghidra export, never infers resource semantics from displacement alone,
and never executes the original game or requests a runtime capture.
