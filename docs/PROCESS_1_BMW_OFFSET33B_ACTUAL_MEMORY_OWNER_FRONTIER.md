# Process 1 — actual-object BMW `offset33b` memory/owner frontier

## Playable-slice blocker reduced

The three `HDVehicle+0x33b0/+0x33b8/+0x33c0` stores are already bounded to
`FUN_0076b280`, and the fresh-bootstrap additional-mass scalar is now correctly
proved through the separately allocated PhysicsParticipant in
`SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1`.

The older `SHIFT.BMWOffset33bMemoryLoadProvenance/1` implementation contains a
useful, already-regressed p-code/register provenance engine, but its direct
additional-mass input validator predates the object-base correction and accepts
only the retracted manager-record proof.  It must therefore not be used directly
for the current numeric chain.

This layer preserves the proven engine while making the historical proof
technically impossible to pass downstream.

Tools:

```text
tools/ghidra/analyze_bmw_offset33b_memory_load_provenance_actual_object.py
tools/ghidra/analyze_bmw_offset33b_actual_field_owner_frontier.py
```

Contracts:

```text
SHIFT.BMWOffset33bMemoryLoadProvenance/1
SHIFT.BMWOffset33bActualFieldOwnerFrontier/1
```

## Stage 1 — actual-object adapter

The adapter accepts only:

```text
SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1
```

and validates all object-identity facts needed for the reduction:

```text
actual PhysicsParticipant allocation size = 0x2b90
embedded Vehicle offset                   = 0x340
actual participant additional mass        = +0xba0
Vehicle alias                              = +0x860
allocation flag                            = 0x20
allocator operation                        = memset(allocation, 0, requested_size)
value                                      = float32 +0.0
```

It also requires the proof to state that manager-record `+0xba0` is **not** the
proven storage and that the retracted manager-record claim was not reused.

After validation the adapter invokes the already-regressed memory-LOAD engine.
Only the historical proof validator is substituted, and only for that call.  The
engine still performs the same instruction/p-code/register analysis and emits the
same `SHIFT.BMWOffset33bMemoryLoadProvenance/1` shape.

The output is then explicitly marked:

```text
offset33b_additional_mass_bootstrap_zero_proof_consumed        = false
offset33b_actual_additional_mass_bootstrap_zero_proof_consumed = true
historical_manager_record_zero_proof_consumed                  = false
actual_object_allocator_zero_proof_consumed                    = true
```

The known +0.0 reduction remains semantic-only until an exact machine LOAD
pointer join proves that a particular LOAD is the current actual participant
`+0xba0` / embedded Vehicle `+0x860` storage.

## Stage 2 — conservative owner classification

`SHIFT.BMWOffset33bActualFieldOwnerFrontier/1` refuses any memory-LOAD report
that consumed the historical manager-record proof.

For each exact `(base-origin expression set, displacement, width)` group:

- exactly `entry:ECX` is promoted to `HDVehicle+offset`, because
  `FUN_0076b280` is the source-backed HDVehicle `__thiscall` producer;
- a single deterministic `memory:[...]` origin remains only an indirect owner
  slot;
- another entry register, multi-origin, derived, or otherwise unresolved base is
  left unresolved;
- no VDF/SDF/tire identity, semantic field name, or numeric value is guessed from
  a displacement.

This creates the smallest safe worklist for the next step: direct HDVehicle
field semantic lookup plus pointer identity for only the indirect/unresolved
owner bases.

## Usage

Run the existing STORE/instruction proof first, then:

```bash
python3 tools/ghidra/analyze_bmw_offset33b_memory_load_provenance_actual_object.py \
  out/bmw_offset33b_store_provenance.json \
  out/fun_0076b280_instructions.jsonl \
  out/bmw_offset33b_actual_additional_mass_bootstrap_zero.json \
  --json-out out/bmw_offset33b_memory_load_actual_object.json

python3 tools/ghidra/analyze_bmw_offset33b_actual_field_owner_frontier.py \
  out/bmw_offset33b_memory_load_actual_object.json \
  --json-out out/bmw_offset33b_actual_field_owner_frontier.json
```

The original game is not executed and no new runtime capture is required.

## Deliberate non-claims

Neither stage assigns semantic field names or values to unresolved resource
roots.  Neither stage applies the +0.0 additional-mass reduction merely because a
LOAD displacement is `0xba0` or `0x860`.

These gates remain false:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

## Next blocker

Consume the actual owner frontier and map only its exact physical fields to the
materialized BMW HDV/VDF/SDF/tire resources.  Once those remaining mass,
geometry, and effective graphical-offset roots are numeric, the three
`HDVehicle+0x33b*` doubles can be evaluated and the BODY0 -> Vehicle-root numeric
matrix can be produced.
