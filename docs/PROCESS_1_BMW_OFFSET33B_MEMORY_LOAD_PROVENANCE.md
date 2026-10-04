# Process 1 — BMW `offset33b` memory-LOAD provenance

## Playable-slice blocker reduced

The BODY0-local -> outer Vehicle-root translation is already symbolic:

```text
translation = -offset33b
```

`SHIFT.BMWOffset33bStoreProvenance/1` proves the three HDVehicle STORE targets
and gives a backward p-code value slice for every admitted STORE. The remaining
memory inputs are still too anonymous for a numeric BMW bind matrix: a terminal
`external-or-memory-varnode` does not say which object/resource field was read.

This pass reuses the same targeted `FUN_0076b280` instruction export and resolves
only memory LOADs that are actually part of those STORE slices.

Contract:

```text
SHIFT.BMWOffset33bMemoryLoadProvenance/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_memory_load_provenance.py
```

## Inputs

The pass consumes three bounded artifacts:

1. positive `SHIFT.BMWOffset33bStoreProvenance/1`;
2. the exact `SHIFT.GhidraFunctionInstructions/2` export for `FUN_0076b280`
   that produced that STORE report;
3. positive `SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1` from #1257.

The historical manager-record proof `SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1`
is explicitly rejected. #1250 established that manager record `+0xba0` is not the
consumed storage; the valid first-bootstrap zero belongs to the separately
allocated actual PhysicsParticipant at `+0xba0`, alias embedded Vehicle `+0x860`.

No second Ghidra export is needed.

Example:

```bash
python3 tools/ghidra/analyze_bmw_offset33b_memory_load_provenance.py \
  out/bmw_offset33b_static_proof/02_bmw_offset33b_store_provenance.json \
  out/bmw_offset33b_static_proof/01_fun_0076b280_instructions.jsonl \
  out/bmw_offset33b_actual_additional_mass_bootstrap_zero.json \
  --json-out out/bmw_offset33b_memory_load_provenance.json
```

## Exact LOAD join

For each `LOAD` p-code node present in an admitted offset33b STORE dependency
slice, the analyzer requires:

```text
one p-code LOAD in the machine instruction
+
one simple register-relative machine memory operand
+
all-path register provenance for that memory base
```

A positive machine join records the LOAD instruction, p-code node id, machine
operand, base register, all-path base-origin expression set, exact displacement,
LOAD width, consuming STOREs and affected offset33b components.

The semantic worklist is grouped by:

```text
(base-origin expression set, displacement, width)
```

## Additional-mass reduction boundary

The valid #1257 reduction is carried as:

```text
actual PhysicsParticipant+0xba0
== embedded Vehicle+0x860
== +0.0f
```

for a freshly allocated first-bootstrap actual participant. It remains independent
of any machine LOAD until pointer provenance proves the LOAD base is that exact
object. Matching `+0xba0` or `+0x860` alone never applies zero.

The report therefore keeps:

```text
additional_mass_pointer_identity_proven   = false
additional_mass_zero_applied_to_this_load = false
```

for displacement-only matches.

## Positive result

A fully deterministic LOAD frontier exposes:

```text
offset33b_memory_LOAD_frontier_ready        = true
offset33b_exact_memory_field_worklist_ready = true
```

Each worklist row still has unresolved semantic owner/field names. The next proof
is narrow:

```text
exact base-origin/displacement group
  -> HDVehicle / VDF / SDF / tire object identity
  -> exact resource/init field
  -> numeric field value
```

## Fail-closed behavior

The pass fails closed on missing LOAD nodes, ambiguous machine LOADs, complex
memory operands, non-deterministic base provenance, malformed STORE contracts,
or an invalid/retracted additional-mass proof.

Even a positive worklist keeps:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

No original-game execution or new runtime capture is required.
