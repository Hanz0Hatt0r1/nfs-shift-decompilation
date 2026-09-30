# Phase 604 — native builtin diagonal reset kernel

Phase 603 ports the recovered builtin sparse numerical solver
`FUN_007b0f20` into native C++.

Phase 604 ports the exact matrix/RHS mutation performed by
`FUN_007b2210`.

## Source-backed operation

For each already-selected scalar node, the retail helper:

1. zeroes the complete matrix row;
2. zeroes the complete matrix column;
3. writes `1.0` to the diagonal element;
4. writes `0.0` to the corresponding RHS element.

The native function
`apply_builtin_diagonal_reset()` mirrors only those operations.

Duplicate supplied nodes are normalized to one reset operation. Out-of-range
nodes fail closed.

## Selection remains evidence-gated

This phase does **not** infer which scalar nodes must be reset.

The recovered frame contract shows that `FUN_007b2210` is selected from the
runtime constraint-sample low bit:

```text
sample +0x70 & 1
```

The Python evidence path
`derive_builtin_diagonal_reset_nodes()` therefore remains blocked when those
runtime flags are not supplied.

The native API accepts explicit scalar nodes only. It does not derive them from
static SDF parity, scalar index parity, constraint type, or any fabricated
policy.

## Native regression

The existing `shift_runtime_builtin_solver_check` now covers:

- four `FUN_007b0f20` solver cases;
- exact `FUN_007b2210` row/column/diagonal/RHS mutation;
- duplicate-node normalization;
- rejection of an out-of-range reset node.

Its JSON output reports both source functions and six total cases.

Linux CI requires:

- `source_function = FUN_007b0f20`;
- `diagonal_reset_source_function = FUN_007b2210`;
- four solver cases;
- two reset cases;
- `status = ok`.

## Boundary after Phase 604

The native numerical backend now contains the two source-backed builtin
operations needed immediately around solve dispatch:

```text
selected reset nodes
  → FUN_007b2210-equivalent reset
  → FUN_007b0f20-equivalent builtin solve
```

A complete BMW fixed-step physics solve is still blocked until an exact frame
provides or reconstructs:

- the 40×40 matrix values;
- the 40-entry RHS values;
- runtime reset-selection flags/nodes;
- the exact sparse graph for that frame/domain;
- proof that the provider-absent builtin branch is the applicable dispatch;
- post-solve body-state application inputs.

Provider vtable `+0x18` remains a separate runtime-capture-gated path.
