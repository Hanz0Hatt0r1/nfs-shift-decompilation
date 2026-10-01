# Phase 624 — prepared native BODY constraint orchestration

Phases 616–623 port every independently recovered numerical primitive used by
the `FUN_007bc680` BODY contribution path. Phase 624 joins those primitives in
the recovered retail order over explicit prepared JOINT/HINGE/BAR sample
arrays.

## Prepared boundary

The new native contract is intentionally downstream of `FUN_007b3ed0`.
It does not invent runtime sample values.

`BodyConstraintAssemblyInput` carries:

- BODY position, axis/correction/state, frame and inverse scalar;
- the BODY matrix tensor used by `FUN_007bbb80`;
- explicit linear/quadratic projection scales;
- scalar-domain size;
- ordered prepared JOINT samples;
- ordered prepared HINGE samples;
- ordered prepared BAR samples.

Each sample carries only source-backed fields required by the already-native
projection and coupling kernels, including scalar base and side flag.

Scalar ranges are fail-closed:

- JOINT width = 3;
- HINGE width = 2;
- BAR width = 1;
- every range must fit the BODY solver domain;
- ranges may not overlap.

## Recovered execution order

`assemble_fun_007bc680_body_constraints()` executes:

1. Phase 616 BODY preprojection;
2. JOINT projections (`FUN_007bac60`);
3. HINGE projections (`FUN_007bae40`);
4. BAR projections (`FUN_007bb090`);
5. JOINT-owned matrix pass (`FUN_007bbb80`): self, later JOINTs, all HINGEs, all BARs;
6. HINGE-owned matrix pass (`FUN_007bb250`): self, later HINGEs, all BARs;
7. BAR-owned matrix pass (`FUN_007bb6c0`): self, later BARs.

This ownership avoids duplicate pair writes while preserving the recovered
kernel split. Pair sign still comes only from equality/difference of the two
sample side flags. Each existing kernel remains responsible for scalar-base
orientation.

## Output

The result contains the transformed BODY preprojection state, complete
BODY-local solver-vector contribution, complete dense logical lower-triangle
matrix contribution, and per-stage sample/write counters.

The matrix output is a logical dense view of source lower-triangle writes.
Phase 624 does not claim that dense indexing is the retail `BODY+0x158`
row-pointer execution path.

## Frozen mixed oracle

The deterministic checker uses one JOINT, one HINGE and one BAR occupying a
six-scalar domain.

Expected BODY-local solver vector:

```text
[7.125, 15.0, 20.3125, 9.125, 20.75, 52.5]
```

Expected lower-triangle matrix:

```text
19.5     0       0      0    0   0
-3.75   15.5     0      0    0   0
-5.25   -8.75    9.5    0    0   0
-0.5     1      -0.5   14    0   0
 2.5    -5       2.5   32   77   0
-3      24     -13      6    3  41
```

The checker also requires exact stage counts, rejects overlapping scalar blocks
and rejects out-of-domain blocks.

## Native implementation

New files:

- `native_runtime/include/shift_body_constraint_assembly.hpp`;
- `native_runtime/src/body_constraint_assembly.cpp`;
- `native_runtime/tests/body_constraint_assembly_check.cpp`.

Linux Vulkan CI runs the checker through CTest and requires maximum error at or
below `1e-12`.

## Boundary after Phase 624

Phase 624 closes prepared sample-array orchestration for the BODY-local
`FUN_007bc680` numerical contribution.

Still open:

- exact sparse `BODY+0x158` row-pointer write execution;
- packaging/authentic supply of refreshed samples from `FUN_007b3ed0`;
- joining generated BODY-local contributions to `FUN_007ba570`/SBEX on fixed
  native steps;
- runtime reset-node selection;
- authentic per-step matrix/RHS observations;
- provider-present dispatch;
- persistent vehicle transform/motion integration.

The checker explicitly reports
`sampled_state_refresh_executed=false` and
`sparse_row_pointer_write_executed=false`.
