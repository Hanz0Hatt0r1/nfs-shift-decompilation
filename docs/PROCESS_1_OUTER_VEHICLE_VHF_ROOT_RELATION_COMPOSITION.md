# Process 1 — exact outer Vehicle / BMW VHF root relation composition

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

The remaining transform blocker is the exact source-backed relation

```text
outer Vehicle root
    -> canonical BMW VHF HIERARCHY Root
```

needed before `SHIFT.BMWBody0BindFrameProof/1` can be assembled.  PR #1330 made
the intervening ownership/coordinate-domain edge positive: the participant root
affine is now proven to be local-to-world for the same materialized Vehicle
Render Model domain selected as canonical
`vehicles/bmw_m3_e36/bmw_m3_e36.vhf`.

The remaining work must therefore not reopen render-model ownership or VHF root
extraction.  It is one exact composition plus one still-unresolved numeric value:
the source-backed `FUN_00795d60` setup delta stored at outer Vehicle
`+0x19c/+0x1a0/+0x1a4`.

## INPUT

The composer consumes only already-positive contracts:

```text
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
SHIFT.VehicleRenderModelRootAffineDomainJoin/1
SHIFT.BMWVHFHierarchyRootFrame/1
```

and, for a positive final relation, one additional narrow value contract:

```text
SHIFT.OuterVehicleRenderRootDeltaNumeric/1
```

The numeric contract is intentionally **not** created from arbitrary XYZ input.
It must bind by canonical JSON SHA-256 to the exact
`SHIFT.OuterVehicleRenderRootDeltaProvenance/1` artifact and must explicitly
prove that its three numbers resolve those source-backed terminal roots.  New
runtime capture, original-game execution, and synthetic test values are rejected
as retail evidence.

This leaves one current value blocker rather than another broad semantic audit:
resolve the exact `FUN_00795d60` terminal roots to their retail setup values.

## OUTPUT

New final Process 1 semantic contract:

```text
SHIFT.OuterVehicleVHFRootRelation/1
```

implemented by:

```text
tools/ghidra/build_outer_vehicle_vhf_root_relation.py
```

Without `SHIFT.OuterVehicleRenderRootDeltaNumeric/1`, the builder returns a
fail-closed blocked report that already freezes the exact composition formula
and the SHA-256 expected from the missing numeric stage.

With a valid numeric delta proof, it emits a positive source-backed relation with:

- exact outer and VHF frame identities;
- canonical VHF path and decoded SHA-256;
- exact HIERARCHY Root path, MatrixNumber and parent-chain identity;
- relation kind `identity` or `fixed_affine`;
- one finite D3D row-vector affine matrix;
- explicit Process 1 semantic authority;
- final downstream bind/world-transform gates still closed.

## Exact row-vector composition

Let:

```text
O = outer Vehicle root local -> world
D = Translation(delta_local)
H = canonical VHF HIERARCHY Root local -> Vehicle Render Model domain
```

The merged affine bridge proves:

```text
P_snapshot = P_outer + R_outer * delta_local
```

Under D3D row vectors this is exactly:

```text
M_model_domain_to_world = D * O
```

PR #1330 proves this affine belongs to the same Vehicle Render Model domain as
the canonical BMW VHF.  The exact VHF root-frame contract independently gives:

```text
M_vhf_root_to_model_domain = H
```

so:

```text
M_vhf_root_to_world = H * D * O
```

and therefore the coordinate transform from outer Vehicle root to VHF root is:

```text
M_outer_to_vhf = inverse(D) * inverse(H)
```

The multiplication order is part of the contract.  Regression coverage uses a
non-commuting VHF root rotation and nonzero delta, so reversing the two inverses
cannot silently pass.

This convention is consistent with the existing Process 1
`SHIFT.BMWBody0VehicleRootBindRelation/1`: source-frame coordinates are mapped to
target-frame coordinates.  Once this relation is positive, the final static bind
matrix is the row-vector chain:

```text
M_BODY0_to_vhf = M_BODY0_to_outer * M_outer_to_vhf
```

using the already-positive target-session numeric BODY0 -> outer Vehicle relation.

## Identity handling

An identity-valued VHF root matrix alone is **not** a frame-identity proof.

The composer reports:

```text
relation.kind = identity
```

only when the complete source-backed composition

```text
inverse(D) * inverse(H)
```

evaluates to identity.  In that case the report explicitly records that identity
semantics were proven by the complete relation chain.  A nonzero delta with an
identity VHF root correctly remains `fixed_affine`.

## CONSUMER

Immediate consumers are:

```text
SHIFT.BMWOffset33bNativeSessionSelection/1
+ SHIFT.BMWBody0VehicleRootBindRelation/1
+ SHIFT.OuterVehicleVHFRootRelation/1
        |
        v
SHIFT.BMWBody0BindFrameProof/1
```

and the already-merged Process 2 strict admission seam from PR #1329.  Process 2
may bind the exact positive Process 1 format after this contract becomes ready;
it does not adjudicate the relation itself.

## GATES_CHANGED

This shard makes the composition itself ready now:

```text
outer_vehicle_vhf_composition_formula_ready = true
```

Until the source-backed numeric delta is supplied, these remain false:

```text
outer_vehicle_render_root_delta_numeric_ready       = false
outer_vehicle_root_to_VHF_vehicle_root_ready        = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready  = false
relation_matrix_numeric_ready                       = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                        = false
vehicle_world_transform_ready                       = false
```

With a valid `SHIFT.OuterVehicleRenderRootDeltaNumeric/1`, the relation and
numeric relation-matrix gates become positive.  The BODY0 bind and vehicle-world
transform gates still remain false until the next explicit composition/admission
stage.

## LIMITS

- No executable ownership is inferred from VHF hierarchy.
- No resource identity is promoted to frame identity.
- No visual similarity is proof.
- No equal-number comparison alone is semantic proof.
- No static VHF transform is treated as dynamic vehicle pose.
- No arbitrary XYZ input can satisfy the numeric-delta gate.
- No new runtime capture or original-game execution is required or accepted as
  the missing static value proof.
- Process 1 remains the sole semantic authority for this relation.

## TESTS

`tests/test_ghidra_outer_vehicle_vhf_root_relation.py` covers:

- current positive inputs narrowing cleanly to the one numeric-delta blocker;
- exact provenance-SHA binding for the numeric delta;
- non-commuting row-vector composition order;
- full-chain identity proof;
- identity VHF root plus nonzero delta remaining fixed-affine;
- synthetic retail-value rejection;
- upstream semantic-preclaim rejection;
- non-affine root-matrix rejection.

## NEXT_OWNER

Process 1 value slice: resolve the already-bounded `FUN_00795d60`
`+0x19c/+0x1a0/+0x1a4` terminal roots to exact retail numeric setup values and
publish `SHIFT.OuterVehicleRenderRootDeltaNumeric/1` bound to the exact provenance
artifact.  Feed it immediately into this composer.  If the relation becomes
positive, compose the target-session BODY0 -> outer Vehicle numeric matrix with it
and publish `SHIFT.BMWBody0BindFrameProof/1` without reopening earlier proofs.
