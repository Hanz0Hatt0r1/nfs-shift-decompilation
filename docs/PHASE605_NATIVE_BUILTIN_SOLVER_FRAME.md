# Phase 605 — native provider-absent builtin solver-frame composition

Phases 603–604 port the two source-backed builtin numerical operations used by
the SDF frame:

- `FUN_007b2210` — selected identity row/column/RHS reset;
- `FUN_007b0f20` — builtin sparse factorization and solve.

Phase 605 composes those operations in their recovered order.

## Native API

`execute_builtin_solver_frame()` accepts:

- an already-assembled square matrix;
- an already-assembled RHS vector;
- explicit reset scalar nodes;
- the exact forward sparse graph;
- the exact reverse sparse graph.

It executes:

```text
explicit reset nodes
  → apply_builtin_diagonal_reset()
  → solve_builtin_sparse()
```

and returns both the reset intermediate state and final factorized/solution
state as `SHIFT.NativeBuiltinSolverFrame/1`.

The recovered sequence is labeled:

```text
FUN_007b2210 -> FUN_007b0f20
```

## Regression

The native parity executable now includes two composition cases:

1. a 3×3 system with scalar node 1 reset, producing
   `[11/7, 0, 19/7]`;
2. the same system with no reset nodes, retaining the Phase 603
   `[1, 2, 3]` solution.

Together with the existing solver/reset validation, the executable covers eight
cases.

## Deliberate boundary

This is a **provider-absent numerical slice**, not the complete retail
`FUN_007b3f40` frame.

The function does not:

- assemble matrix/RHS values from BODY/JOINT/HINGE/BAR state;
- derive reset nodes from runtime `sample+0x70 & 1`;
- choose between provider vtable `+0x18` and builtin `FUN_007b0f20`;
- apply the solved vector through `FUN_007b4110`;
- create or identify a concrete runtime participant/provider.

Those remain independent evidence/integration gates.

## Next gate

The next safe step is an explicit native solver-frame input/admission contract
that carries exact matrix/RHS/graph/reset-node provenance and an authoritative
provider-absent dispatch assertion. Only such an admitted input should be
eligible for execution from the native fixed-step loop.
