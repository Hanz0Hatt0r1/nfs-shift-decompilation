# Process 1 — BMW `offset33b` field-owner frontier

## Playable-slice blocker reduced

The reduced static proof now turns the three `offset33b` STORE value slices into
an exact worklist of memory field groups:

```text
(base-origin expression set, displacement, width)
```

The remaining semantic gap is not arithmetic yet. Each group must first be
attached to the correct object domain without guessing VDF/SDF/tire meanings.

This pass performs only the owner promotions that are already justified by the
retail producer ABI.

Contract:

```text
SHIFT.BMWOffset33bFieldOwnerFrontier/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_field_owner_frontier.py
```

## Input gate

The analyzer consumes a positive:

```text
SHIFT.BMWOffset33bMemoryLoadProvenance/1
```

and requires all of:

```text
offset33b_store_provenance_ready               = true
offset33b_memory_LOAD_frontier_ready            = true
offset33b_exact_memory_field_worklist_ready     = true
BMW_numeric_offset33b_ready                     = false
BODY0_bind_frame_proof_ready                    = false
vehicle_world_transform_ready                   = false
```

The exact object-field worklist must be non-empty and must still carry no
upstream semantic owner or semantic field-name preclaims.

## Safe direct promotion

`FUN_0076b280` is already source-backed as the HDVehicle `offset33b` producer and
its retail ABI is `__thiscall`. Therefore:

```text
FUN_0076b280 entry ECX == HDVehicle this
```

is the only entry-register owner promotion made by this stage.

A worklist group with:

```text
base_origin_expression_set = ["entry:ECX"]
```

becomes an exact owner reference:

```text
HDVehicle+<displacement>
```

For example, a load group at displacement `0x120` is classified as:

```text
semantic_owner_domain       = HDVehicle
exact_owner_field_reference = HDVehicle+0x120
owner_join_ready             = true
semantic_field_name          = null
semantic_field_value_ready   = false
```

The displacement still does not provide a semantic field name or numeric value.

## Indirect owner slots

A deterministic origin such as:

```text
memory:[esi+0x20]
```

is preserved exactly as:

```text
owner_class                       = indirect-owner-slot
indirect_owner_origin_expression  = memory:[esi+0x20]
semantic_owner_domain             = null
candidate_owner_types             = []
owner_join_ready                   = false
VDF_SDF_tire_identity_assumed      = false
```

The analyzer intentionally does not label this as VDF, SDF, tire, another
HDVehicle, or any other object based on call proximity or displacement.

## Other entry registers and multiple origins

`entry:EAX`, `entry:EDX`, and other non-ECX entry origins are not interpreted as
arguments merely because they are registers at function entry. Multi-origin,
derived, and otherwise unresolved sets also remain blocked.

These groups are emitted in:

```text
unresolved_owner_groups
```

with a concrete next requirement to prove one object identity first.

## Additional-mass reduction

#1247 independently proves the first-bootstrap semantic root:

```text
PhysicsParticipant+0xba0
== Vehicle+0x860
== +0.0f
```

The memory-LOAD frontier carries whether that semantic root has also been joined
to a concrete machine LOAD pointer.

This stage exposes:

```text
additional_mass_first_bootstrap_zero_ready
additional_mass_machine_LOAD_join_ready
additional_mass_zero_available_for_numeric_evaluator
```

The final availability flag is true only when both the zero proof and machine
pointer join are already positive upstream.

Even then this stage does not apply the zero itself:

```text
additional_mass_zero_applied_by_this_stage = false
```

so owner classification cannot silently alter numeric arithmetic.

## Handoff

The output separates three finite sets:

```text
direct_HDVehicle_fields
indirect_owner_slots
unresolved_owner_groups
```

and reports:

```text
offset33b_direct_HDVehicle_field_owner_joins_ready
offset33b_all_LOAD_owner_domains_classified
offset33b_all_field_owner_semantics_ready
offset33b_semantic_field_names_ready = false
```

`offset33b_all_LOAD_owner_domains_classified` means every exact LOAD group is at
least categorized as direct, indirect-slot, or unresolved. It does **not** mean
that every owner identity is known.

`offset33b_all_field_owner_semantics_ready` is true only when every worklist row
has a concrete owner join. Semantic field names and values are still separate
proofs.

## Next proof

After this pass the numeric blocker is narrowed to two tasks:

1. map direct `HDVehicle+offset` references to their exact semantic HDV fields;
2. resolve only the reported indirect/unresolved bases to concrete HDV/VDF/SDF/
   tire owners, then map their exact offsets to resource/init fields.

Only after those joins should a numeric evaluator reconstruct the three
`offset33b` doubles.

## Deliberate non-claims

This stage keeps all of the following false:

```text
offset33b_semantic_field_names_ready                = false
BMW_numeric_offset33b_ready                         = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready   = false
BODY0_bind_frame_proof_ready                        = false
vehicle_world_transform_ready                       = false
```

It does not infer:

- VDF/SDF/tire identity from a memory origin expression;
- parameter semantics from non-ECX entry registers;
- semantic field names from displacement;
- numeric values from owner identity;
- additional-mass applicability without the upstream machine pointer join.
