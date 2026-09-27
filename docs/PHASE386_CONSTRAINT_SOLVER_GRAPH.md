# Phase 386 — Constraint solver graph reconstruction

The SDF physics path now reaches the compact graph consumed by `FUN_007b0f20`. The graph operates in the scalar solver-node domain returned by `FUN_007b1b60`, while the source constraint-record count remains a separate topology value.

## Connectivity

`FUN_007b1b60` compares runtime constraint pairs using their `posbody` and `negbody` references. Two constraints are graph-neighbors when they share either endpoint body. Runtime constraint block widths are 3 for JOINT, 2 for HINGE and 1 for BAR. A `JOINT&HINGE` source section has already been split into separate JOINT and HINGE runtime records by Phase 384.

## Ordering

The recovered ordering stage maintains both a node→position map and a position→node permutation. Its objective is the sum of squared differences between block offsets for every connected constraint pair. It repeatedly attempts adjacent moves of each constraint in both directions and accepts only strict cost reductions.

## Compact graph

`FUN_007b1360` consumes the ordered connectivity matrix. It normalizes nonzero matrix values to 1.0, temporarily discovers two-hop relations with marker 2.0, and emits two compact dependency tables:

- a forward table with `constraint_count + 1` outer records;
- a reverse table with `constraint_count` item records in reverse node order.

Each compact item is 8 bytes: node byte, dependency-count byte and a 32-bit pointer/offset to its byte-sized dependency index list. The source also seeds the solver vector with 1.0 for every scalar solver node.

The implementation exposes these structures without assigning undocumented PhysX class names or physical meanings to the coefficient matrix.

## Current boundary

The remaining unknown is the numeric coefficient population performed by `FUN_007b2010` and `FUN_007ba2b0`, plus the provider-specific implementation of the final solver consumer. The graph topology and ordering boundaries are now separated from those unknown coefficient values.
