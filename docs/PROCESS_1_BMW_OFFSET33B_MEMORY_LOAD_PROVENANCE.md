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

The pass consumes three already-bounded artifacts:

1. positive `SHIFT.BMWOffset33bStoreProvenance/1`;
2. the exact `SHIFT.GhidraFunctionInstructions/2` export for `FUN_0076b280`
   that produced that STORE report;
3. positive `SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1` from #1247.

No second Ghidra export is needed.

Example:

```bash
python3 tools/ghidra/analyze_bmw_offset33b_memory_load_provenance.py \
  out/bmw_offset33b_static_proof/bmw_offset33b_store_provenance.json \
  out/bmw_offset33b_static_proof/bmw_offset33b_fun_0076b280_instructions.jsonl \
  out/bmw_offset33b_additional_mass_bootstrap_zero.json \
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

A positive machine join records:

```text
LOAD instruction
p-code node id
machine operand
base register
all-path base-origin expression set
exact displacement
LOAD width
which offset33b STORE(s) consume the value
which offset33b x/y/z field(s) depend on it
```

The resulting semantic worklist is grouped by:

```text
(base-origin expression set, displacement, width)
```

This is the first artifact in the numeric offset33b chain that turns an anonymous
memory root into an exact object-origin/field-offset candidate.

## Why displacement is not semantics

A displacement such as `+0xba0` or `+0x860` is not enough to identify an object.
The analyzer therefore records matching displacements but keeps:

```text
additional_mass_pointer_identity_proven     = false
additional_mass_zero_applied_to_this_load   = false
resource_or_object_semantics_proven         = false
```

until pointer provenance joins the base to the exact current PhysicsParticipant
or embedded outer Vehicle.

This matters because #1247 independently proves:

```text
PhysicsParticipant+0xba0
== Vehicle+0x860
== additional participant mass root
== +0.0f
```

for fresh/reinitialized first bootstrap. That proof is consumed and preserved as
a known semantic reduction, but it is never attached to an unrelated machine
LOAD merely because an offset happens to match.

## Positive result

A fully deterministic LOAD frontier exposes:

```text
offset33b_memory_LOAD_frontier_ready          = true
offset33b_exact_memory_field_worklist_ready   = true
```

Each worklist row still intentionally has:

```text
semantic_owner_or_resource = null
semantic_field_name        = null
semantic_join_ready        = false
```

The next proof can therefore be narrow and data-driven:

```text
exact base-origin/displacement group
  -> HDVehicle / VDF / SDF / tire object identity
  -> exact resource/init field
  -> numeric field value
```

## Fail-closed cases

The analyzer blocks or keeps the semantic frontier incomplete when:

- a LOAD p-code node from the STORE report is absent from the supplied
  instruction export;
- one machine instruction contains multiple LOADs that cannot be uniquely joined;
- the relevant memory operand is complex rather than simple register-relative;
- all-path base-register provenance is non-deterministic;
- a memory root exists but no structured LOAD node reaches the STORE slice.

It never creates a PHI value, CALL return value, object identity, or resource
field meaning that is not already present in static evidence.

## Deliberate non-claims

Even a positive exact-memory-field worklist keeps:

```text
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

The pass only removes the anonymous-memory part of the blocker. Numeric
`offset33b` becomes ready only after all required field groups are joined to
exact BMW resource/init values and the supported arithmetic is evaluated.
