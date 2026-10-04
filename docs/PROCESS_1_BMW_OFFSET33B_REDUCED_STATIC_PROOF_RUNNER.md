# Process 1 — reduced BMW `offset33b` static-proof runner

## Playable-slice blocker reduced

The numeric BMW BODY0 bind translation depends on three `offset33b` doubles.
Three bounded proofs now exist:

```text
SHIFT.BMWOffset33bStaticProofBundle/1
  -> one read-only/noanalysis FUN_0076b280 export
  -> exact HDVehicle STORE/value-root frontier

SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1
  -> PhysicsParticipant+0xba0 / Vehicle+0x860 = +0.0f
     for fresh/reinitialized first bootstrap

SHIFT.BMWOffset33bMemoryLoadProvenance/1
  -> exact memory LOAD base-origin/displacement/width worklist
```

This runner composes them without requesting another Ghidra export.

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
        v
analyze_bmw_offset33b_additional_mass_bootstrap_zero.py
        |
        +-> 03_bmw_offset33b_additional_mass_bootstrap_zero.json
        |
        v
analyze_bmw_offset33b_memory_load_provenance.py
        |
        +-> 04_bmw_offset33b_memory_load_provenance.json
        |
        v
bmw_offset33b_reduced_static_proof_bundle.json
```

The first instruction export is reused by the LOAD analysis. There is no second
Ghidra project open and no second target list.

## Invocation

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_bmw_offset33b_reduced_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_offset33b_reduced_static_proof
```

Optional arguments remain compatible with the base runner:

```text
--relation <SHIFT.BMWBody0VehicleRootBindRelation/1>
--program-name SHIFT.exe
--ghidra-home /opt/ghidra
--timeout-seconds N
```

## Upstream blocking behavior

The additional-mass proof is useful independently of STORE coverage, so it runs
after any successfully completed base bundle.

If the base bundle does not yet have both:

```text
offset33b_store_provenance_ready    = true
offset33b_value_root_frontier_ready = true
```

then the memory-LOAD stage is marked:

```text
blocked_by_upstream_gate
```

rather than being invoked on an incomplete STORE artifact.

## Positive handoff

When the LOAD pass produces a deterministic exact worklist, the bundle reports:

```text
offset33b_store_provenance_ready                = true
offset33b_additional_mass_bootstrap_zero_ready  = true
offset33b_memory_LOAD_frontier_ready             = true
offset33b_exact_memory_field_worklist_ready      = true
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

## Additional-mass reduction boundary

The bundle carries the independent fact:

```text
additional_mass_first_bootstrap_zero = true
additional_mass_term_elidable_for_first_bootstrap = true
```

but keeps:

```text
additional_mass_machine_LOAD_join_ready = false
```

until the LOAD base pointer is proved to be the exact current PhysicsParticipant
or embedded outer Vehicle. Matching `+0xba0`/`+0x860` alone is not pointer
identity.

## Deliberate non-claims

Even the strongest current reduced-static bundle keeps:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

The runner does not:

- request another Ghidra export after `FUN_0076b280`;
- convert a field worklist into resource semantics automatically;
- apply bootstrap-zero to an unjoined machine LOAD;
- invent helper return values or unsupported p-code arithmetic;
- execute the original game or request a runtime capture.

## Failure behavior

Every downstream failure preserves artifacts already produced and writes a
fail-closed bundle identifying the failed stage. No failure path can promote a
partial field worklist to numeric offset33b readiness.
