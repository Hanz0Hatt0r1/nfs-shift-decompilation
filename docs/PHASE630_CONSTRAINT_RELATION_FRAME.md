# Phase 630 — constraint relation ownership → refreshed GBCF

Phase 629 ports the numerical `FUN_007b3ed0` refresh kernels, but its input is
still an already-materialized set of relation/sample objects.

Phase 630 adds the missing ownership transport between the retail top-level
JOINT/HINGE/BAR relation arrays and the BODY-owned sample identities carried by
GBCF.

## Retail endpoint identity

Direct audit of the recovered `SHIFT.exe.c` construction loop confirms the
endpoint side identity for all three relation kinds:

```text
record +0x78 positive BODY → sample helper(..., side=1)
record +0x80 negative BODY → sample helper(..., side=0)
```

This is explicit at the call sites of:

- `FUN_007ba8b0` for JOINT;
- `FUN_007ba900` for HINGE;
- `FUN_007ba990` for BAR.

Both endpoints receive the same solver scalar base. BAR also receives the same
constructor-side bias value on both endpoint samples.

For HINGE, the BODY-owned 0xA0 sample keeps the constructor-generated primary
local row at `sample+0x00`. `FUN_007b2de0` uses that unchanged negative
primary row while rebuilding `+0x18/+0x30`, then refreshes the generated
`+0x48/+0x60` rows. This matches the existing
`PreparedHingeSample.position` / `angular` / `linear` split.

## CSRF packet

New input/report/packet contracts:

- `SHIFT.NativeConstraintSampleRelationFrameInput/1`;
- `SHIFT.NativeConstraintSampleRelationFrame/1`;
- `SHIFT.NativeConstraintSampleRelationFramePacket/1`.

Binary packet magic is `CSRF`, version 1.

The packet header stores:

- BODY count;
- JOINT relation count;
- HINGE relation count;
- BAR relation count;
- explicit proof flags.

Every relation row stores exact positive/negative GBCF endpoint references as
`(body_index, sample_index)`.

The value payload is intentionally minimal:

- JOINT: positive and negative local `sample+0x00` rows;
- HINGE: positive local `sample+0x18` and `sample+0x30` rows;
- BAR: positive and negative local `sample+0x00` rows.

The packet does **not** duplicate:

- BODY frames;
- BODY positions;
- sample scalar bases;
- sample side flags;
- BAR side bias;
- generated solver-vector or solver-matrix contributions.

Those fields remain authoritative in GBCF.

## Native ownership join

New native files:

- `native_runtime/include/shift_constraint_sample_relation_frame.hpp`;
- `native_runtime/src/constraint_sample_relation_frame.cpp`;
- `native_runtime/tests/constraint_sample_relation_frame_check.cpp`.

`refresh_generated_body_constraint_frame()` first validates the complete
relation → GBCF identity join:

1. CSRF BODY count equals GBCF BODY count.
2. Every endpoint BODY/sample index is in range.
3. Every BODY-owned sample is owned by exactly one relation endpoint.
4. Positive endpoints have the source-backed side flag `1`.
5. Negative endpoints have the source-backed side flag `0`.
6. The two endpoint samples of one relation have the same scalar base.
7. BAR endpoint side-bias values match.

Only after that gate passes does the implementation execute the Phase 629
kernels and overwrite a copy of the corresponding GBCF sample fields.

Execution remains in retail top-level order:

```text
JOINT relations
  → HINGE relations
  → BAR relations
```

## Relation count is not endpoint-sample count

This phase makes a previously blurred cardinality boundary explicit.

One retail relation owns **two** BODY samples:

```text
1 JOINT relation → 2 JOINT endpoint samples
1 HINGE relation → 2 HINGE endpoint samples
1 BAR relation   → 2 BAR endpoint samples
```

The Phase 630 native oracle freezes exactly that 1:2 relationship.

The older Phase 628 11-BODY / 4-JOINT / 4-HINGE / 20-BAR fixture remains a
scheduler/generation regression. Its sample-count equality gate is not treated
as proof that authentic BODY-owned sample cardinality equals top-level relation
cardinality. Fixed-step admission is the next integration step and must use the
new relation/endpoint distinction rather than preserve that synthetic shortcut.

## CLI

Prepare a relation frame with:

```bash
python shift_importer.py native-constraint-sample-relation-frame \
  constraint-relations.json \
  out/constraint-relations
```

Outputs:

- `constraint_sample_relations.csrf`;
- `constraint_sample_relations_manifest.json`.

## Regression

`shift_runtime_constraint_sample_relation_frame_check` consumes one GBCF and
one CSRF packet.

The frozen fixture uses two BODY objects with one JOINT, one HINGE and one BAR
relation. It requires:

- one relation of each type;
- two refreshed endpoint samples of each type;
- exact Phase 629 numerical refresh values;
- preserved scalar/side identity;
- complete endpoint coverage;
- duplicate ownership rejection;
- side mismatch rejection;
- scalar-base mismatch rejection;
- refreshed GBCF contribution generation to remain finite.

The relation packet never stores generated contribution values.

## Boundary after Phase 630

Phase 630 closes prepared relation ownership and the exact relation → BODY-owned
sample refresh join.

Still open:

- loading CSRF alongside GBCF on every admitted native fixed step;
- replacing Phase 628's synthetic sample-count equality with relation-aware
  endpoint cardinality;
- authentic BMW per-frame BODY transforms and raw relation/sample inputs;
- runtime `relation+0x70 & 1` reset-node selection;
- provider-present refresh/generation behavior;
- persistent vehicle transform/motion integration.

The next safe step is Phase 631: fixed-step CSRF → refreshed GBCF → generated
matrix/RHS admission, with relation and endpoint-sample cardinalities kept
separate.
