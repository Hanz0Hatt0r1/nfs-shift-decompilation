# Process 1 — BMW `offset33b` semantic static-proof runner

## Blocker reduced

`BMW_numeric_offset33b_ready` requires one exact machine/resource join after the
existing reduced `FUN_0076b280` proof. The repository already has:

```text
SHIFT.BMWOffset33bReducedStaticProofBundle/1
  -> one read-only FUN_0076b280 instruction export
  -> exact STORE/LOAD worklist

SHIFT.BMWOffset33bFieldOwnerFrontier/1
  -> safe HDVehicle-this owner classification

SHIFT.BMWOffset33bResourceInputs/1
  -> hash-locked BMW CDF/SDF values + source-backed CDF load-data offsets
```

This runner composes them in one command:

```text
SHIFT.BMWOffset33bSemanticStaticProofBundle/1
```

Implementation:

```text
tools/ghidra/run_bmw_offset33b_semantic_static_proof.py
```

## Invocation

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_bmw_offset33b_semantic_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_offset33b_semantic_static_proof
```

Only `FUN_0076b280` is exported from Ghidra. The runner reuses that export for
STORE provenance and memory-LOAD provenance, then emits:

```text
06_bmw_offset33b_field_owner_frontier.json
07_bmw_offset33b_resource_inputs_validation.json
bmw_offset33b_semantic_static_proof_bundle.json
```

alongside all artifacts from the reduced runner.

## Fail-closed policy

The final bundle exposes exact direct HDVehicle fields, indirect owner slots,
unresolved owner groups, and the exact CDF load-data mapping side by side. It
does not pair them merely because offsets look compatible.

These remain false until pointer/owner provenance establishes the actual join:

```text
offset33b_semantic_field_names_ready                = false
offset33b_memory_LOAD_semantic_join_ready            = false
BMW_numeric_offset33b_ready                          = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready     = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

`load_data+0x338` remains explicitly unassigned because it is a derived value,
not a direct CDF destination.

## Why this is the last useful orchestration step

After this runner, the output itself lists every remaining pointer/owner join.
No second broad Ghidra export or manual resource lookup is needed. If all LOAD
bases resolve to already-known objects, the next pass can evaluate the three
`offset33b` doubles. If one base remains unresolved, only that exact producer
edge needs another targeted export.
