# Phase 388 — Solver scalar-node domain

Source inspection of `FUN_007b3820` resolved a previously ambiguous count. The value written to physics-system `+0x34` is the cumulative scalar solver-node count produced by `FUN_007b1b60`, not the number of JOINT/HINGE/BAR runtime records.

## Scalar widths

Runtime constraint records contribute fixed block widths: JOINT = 3, HINGE = 2 and BAR = 1. A `JOINT&HINGE` source section is emitted as one JOINT record and one HINGE record, therefore contributing 5 scalar solver nodes.

After ordering, each constraint receives a contiguous scalar block offset. `FUN_007b2010` then allocates a row-pointer array with `scalar_count * 4` bytes and a matrix with `scalar_count * scalar_count * 8` bytes. The fallback vector at physics-system `+0x40` is allocated with `scalar_count * 8` bytes.

## Matrix expansion

`FUN_007ba2b0` processes per-body incidence lists. When two runtime constraints share a body, it writes `1.0` across the Cartesian product of their scalar blocks. Thus a JOINT/HINGE pair produces a 3×2 block of ones in both symmetric directions. Diagonal entries are initialized separately by `FUN_007b2210` before the final sparse solve.

The implementation now exposes `build_sdf_scalar_connectivity_matrix()` and reports both the constraint-record count and the scalar solver-node count. This removes the previous ambiguity from the Phase 386 graph/Phase 387 solver contracts.

## Remaining boundary

The remaining numerical semantics are the body-specific transforms and any coefficients that can overwrite the binary coupling pattern before `FUN_007b2210`. Provider-specific solver behavior remains opaque.
