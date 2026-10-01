# Phase 614 — BODY export → builtin solver-frame join

Phase 613 can replay explicit per-BODY `FUN_007ba570` contributions into
complete global solver vector/matrix destinations.

Phase 606/608 already execute a proof-gated provider-absent builtin solver frame
whose matrix and RHS are independently supplied evidence.

Phase 614 joins those two contracts without choosing either one as authoritative.

## Exact pre-reset join

New native API:

`join_body_export_to_builtin_solver_frame()`.

The function:

1. executes the prepared Phase 613 SBEX frame;
2. requires equal scalar cardinality;
3. compares the complete exported solver vector with the SBFR RHS;
4. compares every flattened exported N×N matrix double with the SBFR matrix;
5. only after both joins pass, executes the existing
   `FUN_007b2210 → FUN_007b0f20` prepared solver path.

The comparison occurs before the Phase 606 reset nodes are applied, matching the
recovered retail order:

`FUN_007ba570 → FUN_007b2210 → FUN_007b0f20`.

No matrix entry or RHS value is synthesized to make the contracts agree.

## Native checker

New executable:

```bash
shift_runtime_body_export_solver_join_check \
  body_solver_export.sbex \
  solver_frame.sbfr
```

Output format:

`SHIFT.NativeBodyExportSolverFrameJoinCheck/1`.

It records:

- source functions `FUN_007ba570`, `FUN_007b2210`,
  `FUN_007b0f20`;
- scalar count;
- matrix double count;
- maximum RHS join error;
- maximum matrix join error;
- final solver oracle error.

## CI

Linux Vulkan CI builds a 3-scalar SBFR with:

```text
matrix =
4 1 1
1 3 0
1 0 2

rhs = [9, 7, 7]
reset_nodes = [2]
```

A three-BODY SBEX fixture distributes exactly those matrix/RHS values across
ordered BODY-local contribution arrays. CI requires zero vector, matrix and
solver errors.

A second SBEX remains internally valid but changes one BODY vector contribution
by +1. The join checker must reject it with:

`BODY export/RHS join mismatch`.

This proves that SBEX validity alone cannot satisfy the solver-frame gate.

## Boundary after Phase 614

Phase 614 closes the exact handoff from explicit BODY contribution evidence to
the already-prepared builtin solver matrix/RHS.

It still does not derive:

- BODY contribution values from `FUN_007bc680`;
- runtime constraint sampled-state refresh;
- runtime `sample+0x70 & 1` reset selection;
- provider-present dispatch.

The fixed-step runtime still consumes SBFR directly. A next integration step may
accept SBEX alongside SBFR and require this exact join before each prepared
solver execution, but only as an evidence gate; it must not claim that static
assets generated the BODY contributions.
