# Process 1 — BMW `offset33b` field-owner frontier

## Playable-slice blocker reduced

The repaired reduced static proof now turns the three `offset33b` STORE value
slices into an exact memory-field worklist:

```text
(base-origin expression set, displacement, width)
```

This pass classifies only the owner relations already justified by retail ABI and
keeps VDF/SDF/tire identity unresolved until pointer provenance proves it.

Contract:

```text
SHIFT.BMWOffset33bFieldOwnerFrontier/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_field_owner_frontier.py
```

## Input gate

The input must be a positive repaired:

```text
SHIFT.BMWOffset33bMemoryLoadProvenance/1
```

with:

```text
offset33b_store_provenance_ready                              = true
offset33b_memory_LOAD_frontier_ready                           = true
offset33b_exact_memory_field_worklist_ready                    = true
offset33b_actual_additional_mass_bootstrap_zero_proof_consumed = true
BMW_numeric_offset33b_ready                                    = false
BODY0_bind_frame_proof_ready                                   = false
vehicle_world_transform_ready                                  = false
```

The additional-mass reduction must identify:

```text
proof_format = SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1
retracted_manager_record_zero_claim_reused = false
```

and the LOAD report scope must keep:

```text
retracted_manager_record_zero_contract_accepted = false
```

Thus a historical #1247-style manager-record proof cannot enter this stage even
indirectly.

## Safe direct promotion

`FUN_0076b280` is source-backed as the HDVehicle `offset33b` producer and uses
`__thiscall`, so only:

```text
base_origin_expression_set = ["entry:ECX"]
```

is promoted to:

```text
semantic_owner_domain       = HDVehicle
exact_owner_field_reference = HDVehicle+<displacement>
owner_join_ready             = true
```

The displacement still does not imply a semantic field name or value.

## Indirect and unresolved owners

A deterministic memory-derived base such as:

```text
memory:[esi+0x20]
```

remains:

```text
owner_class                      = indirect-owner-slot
semantic_owner_domain            = null
candidate_owner_types            = []
VDF_SDF_tire_identity_assumed     = false
owner_join_ready                  = false
```

Other entry registers, multi-origin sets, and derived/unknown bases remain
unresolved. No argument meaning or resource type is inferred from register name,
call proximity, or displacement.

## Correct additional-mass reduction

#1257 proves for a fresh first-bootstrap **actual separately allocated**
PhysicsParticipant:

```text
actual PhysicsParticipant+0xba0
== embedded Vehicle+0x860
== +0.0f
```

This stage accepts that fact only from the #1257 format. It exposes whether an
upstream machine LOAD pointer join has also identified the exact storage. Zero is
available to a future numeric evaluator only when both proofs are positive, and
this owner-classification stage never reapplies the numeric zero itself.

## Handoff

The output separates:

```text
direct_HDVehicle_fields
indirect_owner_slots
unresolved_owner_groups
```

and reports whether direct HDVehicle owner joins are ready, whether all LOAD
owner domains are classified, and whether every owner identity is concrete.
Semantic field names remain a later proof.

The next work is finite:

1. map direct `HDVehicle+offset` references to exact HDV field semantics;
2. resolve only reported indirect/unresolved bases to concrete HDV/VDF/SDF/tire
   owners;
3. map those exact owner+offset pairs to resource/init values;
4. only then evaluate numeric `offset33b`.

## Deliberate non-claims

The analyzer keeps:

```text
offset33b_semantic_field_names_ready              = false
BMW_numeric_offset33b_ready                       = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                      = false
vehicle_world_transform_ready                     = false
```

It never accepts the retracted manager-record zero contract, guesses VDF/SDF/tire
identity, infers a semantic field name from displacement, promotes owner identity
to a numeric value, executes the original game, or requests a runtime capture.
