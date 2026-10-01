# Phase 627 — prepared generated-BODY constraint frame

Phase 626 proves that a prepared BODY state/sample set can generate the exact
provider-absent contribution consumed by `FUN_007ba570`.

The remaining integration problem is transport. The fixed-step runtime cannot
accept C++ fixture objects, and using SBEX would put already-generated
vector/matrix values back into the input.

Phase 627 adds a packet that carries only the inputs required to regenerate the
BODY contribution natively.

## Contract

Input JSON:

`SHIFT.NativeGeneratedBodyConstraintFrameInput/1`.

Prepared report:

`SHIFT.NativeGeneratedBodyConstraintFrame/1`.

Binary packet:

`SHIFT.NativeGeneratedBodyConstraintFramePacket/1`

with magic `GBCF`, version 1.

## Explicit proofs

The builder requires all four proofs:

- `sample_values_ready`;
- `body_order_ready`;
- `row_layout_ready`;
- `provider_absent`.

BODY order must be contiguous. The provider-absent path requires canonical
builtin row indices:

`row_index[row] = row * scalar_count`

and N² matrix storage.

## Packet contents

Each BODY stores only prepared generation inputs:

- BODY index;
- BODY position;
- correction/axis/angular/linear preprojection state;
- inverse scalar;
- 3×3 body frame;
- 3×3 body tensor;
- linear/quadratic constraint scales;
- canonical row-index vector;
- ordered JOINT samples;
- ordered HINGE samples;
- ordered BAR samples.

JOINT/HINGE/BAR records preserve scalar base and side flag together with the
already-source-backed fields consumed by Phases 617–623.

The packet does **not** store:

- BODY solver-vector contribution values;
- BODY solver-matrix contribution values;
- expected global matrix/RHS;
- solver result.

This is the key distinction from SBEX.

## Native execution

New native files:

- `native_runtime/include/shift_generated_body_constraint_frame.hpp`;
- `native_runtime/src/generated_body_constraint_frame.cpp`;
- `native_runtime/tests/generated_body_constraint_frame_check.cpp`.

The loader independently validates:

- GBCF magic/version;
- proof mask;
- body/scalar/matrix cardinality;
- contiguous BODY order;
- canonical row-index count;
- finite doubles/floats;
- side flags limited to 0/1;
- zero record padding;
- no trailing bytes.

Execution then performs, per BODY:

```text
GBCF prepared state/samples
  → Phase 626 generate_and_export_fun_007bc680_body()
      → Phase 624 FUN_007bc680
      → Phase 625 FUN_007bb8d0 storage
      → Phase 612 FUN_007ba570 contribution
  → ordered global additive accumulation
```

No generated contribution is read from the packet.

## Deterministic oracle

The CI fixture reuses the Phase 624 one-JOINT / one-HINGE / one-BAR six-scalar
BODY.

Expected native-generated global solver vector:

```text
[7.125, 15.0, 20.3125, 9.125, 20.75, 52.5]
```

Expected native-generated global matrix is the same 36-double lower-triangle
matrix frozen in Phase 624/626.

The native checker requires zero error and reports:

- `contribution_values_stored_in_packet=false`;
- `native_generation_executed=true`;
- `provider_present=false`;
- `sampled_state_refresh_executed=false`.

## CLI

Prepare a frame with:

```bash
python shift_importer.py native-generated-body-constraint-frame \
  generated-body-input.json \
  out/generated-body
```

The output contains:

- `generated_body_constraints.gbcf`;
- `generated_body_constraints_manifest.json`.

## Boundary after Phase 627

Phase 627 closes evidence-shaped transport of prepared BODY generation inputs
without smuggling contribution values through SBEX.

Still open:

- fixed-step `GBCF → generated matrix/RHS → SBFR` equality gate;
- authentic `FUN_007b3ed0` sampled-state refresh/input production;
- runtime reset-node selection from retail sample state;
- provider-present generation/storage/export;
- authentic matrix/RHS/reset observations;
- persistent vehicle transform/motion integration.

Phase 628 can safely consume GBCF on every admitted fixed step and retain the
existing exact SBFR comparison before reset/solve.
