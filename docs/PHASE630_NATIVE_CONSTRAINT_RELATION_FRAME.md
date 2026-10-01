# Phase 630 — native FUN_007b3820 relation ownership bridge

Phase 629 ports the numerical `FUN_007b3ed0` refresh kernels, but its API still
accepts already BODY-local endpoint samples. Retail does not start there:
`FUN_007b3820` allocates each relation endpoint into the owning BODY sample
array, derives the BODY-local rows and only then runs the refresh helper.

Phase 630 reconstructs that source-backed ownership boundary and emits the
existing `PreparedJointSample`, `PreparedHingeSample` and
`PreparedBarSample` ABI consumed by Phase 624 and GBCF.

## Source evidence

The implementation is audited against `SHIFT.exe.c` SHA-256:

`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

The relevant retail chain is:

```text
FUN_007b3820
  -> FUN_007ba8b0 JOINT BODY sample allocation
  -> FUN_007ba900 HINGE BODY sample allocation
  -> FUN_007ba990 BAR BODY sample allocation
  -> FUN_007b2da0 / FUN_007b2de0 / FUN_007b2f70
  -> FUN_007b3ed0 on subsequent frames
```

Before allocation, `FUN_007b1b60` assigns one packed scalar domain across all
relations. Widths are source-backed:

- JOINT: 3;
- HINGE: 2;
- BAR: 1.

The native bridge therefore rejects overlap, gaps and incomplete coverage
instead of silently repacking a malformed prepared relation frame.

## Relation ownership ABI

All three top-level relation records use:

- positive BODY pointer at `+0x78`;
- positive BODY-owned sample pointer at `+0x7c`;
- negative BODY pointer at `+0x80`;
- negative BODY-owned sample pointer at `+0x84`.

`FUN_007b3820` always allocates the positive endpoint first with
`side_flag=1`, then the negative endpoint with `side_flag=0`. The new native
result keeps an explicit per-BODY ownership map with relation index, BODY index,
BODY sample ordinal, scalar base and side flag. Same-BODY relations preserve
that positive-then-negative insertion order.

No raw retail pointers are serialized or fabricated.

## FUN_007afcd0

JOINT and BAR allocators convert a world point into BODY-local coordinates with:

```text
delta = world_point - BODY.position
local = FUN_007af0a0(BODY.frame, delta)
```

Phase 630 exposes this as
`inverse_transform_fun_007afcd0_relation()` and reuses the exact Phase 629
float32 transform boundary.

## HINGE basis construction

`FUN_007ba900` does not subtract BODY position because the relation value is
an axis/vector. It applies `FUN_007af0a0` and then `FUN_007b1230`.

Phase 630 ports that basis construction:

1. normalize the primary local row with the zero-vector preserving
   `FUN_00753690` behavior;
2. choose the retail seed branch at `abs(primary.x) >= 0.7`;
3. build the two cross-product rows;
4. normalize both rows.

The positive angular/linear local rows feed the existing
`FUN_007b2de0` refresh. The negative primary local row remains the source
from which the negative angular/linear rows are rebuilt.

## HINGE +0x78 frame-offset refresh

Immediately before BODY contribution assembly, retail `FUN_007bb8d0` updates
only positive-side HINGE samples:

```text
positive sample +0x78 =
    FUN_007aefb0(negative BODY frame, negative sample +0x00)
```

The bridge materializes this value into `PreparedHingeSample.frame_offset`.
That makes the output directly compatible with the existing Phase 618/624
nonzero-side HINGE projection path without assigning a new semantic name to the
retail row.

## BAR side bias

`FUN_007b3820` computes the endpoint separation length once and passes the
same value to both `FUN_007ba990` allocations. Phase 630 preserves it as
`PreparedBarSample.side_bias`, while the refreshed common BAR direction still
comes from the existing `FUN_007b2f70` implementation.

## Native API

New files:

- `native_runtime/include/shift_constraint_relation_frame.hpp`;
- `native_runtime/src/constraint_relation_frame.cpp`;
- `native_runtime/tests/constraint_relation_frame_check.cpp`.

Primary entry point:

`build_fun_007b3820_constraint_relation_frame()`.

The result contains:

- the exact Phase 629 refresh input;
- the Phase 629 refresh result;
- GBCF-compatible prepared sample arrays grouped by BODY;
- explicit JOINT/HINGE/BAR relation-to-BODY sample ownership maps.

## Regression coverage

`shift_runtime_constraint_relation_frame_check` freezes:

- `FUN_007afcd0` world-to-BODY local conversion;
- JOINT positive/negative ownership and refreshed positions;
- HINGE primary basis and positive-side `+0x78` frame-offset production;
- BAR local points, endpoint distance, refreshed points and common direction;
- positive-before-negative insertion when both endpoints reference one BODY;
- fail-closed scalar overlap/gap behavior;
- fail-closed BODY index validation.

The checker reports `gbcf_packet_emitted=false` deliberately.

## Boundary after Phase 630

The project no longer needs caller-invented BODY-local JOINT/HINGE/BAR endpoint
rows to exercise the native refresh/assembly path. A prepared relation frame can
now be converted into the exact BODY-owned sample ABI used downstream.

Still open:

- serializing/proof-gating this relation frame for fixed-step transport;
- applying the rebuilt sample arrays into a GBCF instance before the Phase 628
  equality gate;
- authentic per-frame BODY/relation input capture;
- runtime `sample+0x70 & 1` reset-node selection;
- provider-present dispatch;
- persistent vehicle transform/motion integration.

The next safe step is a proof-gated relation-frame packet plus a strict
relation-frame -> GBCF join.
