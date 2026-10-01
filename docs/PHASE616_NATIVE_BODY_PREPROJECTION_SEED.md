# Phase 616 — native FUN_007bc680 preprojection seed

Phase 615 proves that supplied BODY-local solver contributions can gate the
native fixed-step solver through an exact SBEX→SBFR join.

The next missing source stage is contribution generation in
`FUN_007bc680`. Phase 616 ports only the source-backed seed at the front of
that function. It deliberately stops before JOINT/HINGE/BAR projection and
matrix coupling.

## Retail source boundary

The local `SHIFT.exe.c` snapshot shows `FUN_007bc680` at source line
820081.

Before it calls any constraint helper, it computes three double residuals:

```text
r0 = +0x48 - (+0x40 * +0x20 - +0x38 * +0x28)
r1 = +0x50 - (+0x30 * +0x28 - +0x40 * +0x18)
r2 = +0x58 - (+0x38 * +0x18 - +0x30 * +0x20)
```

It then calls:

```text
FUN_007aefb0(body + 0xb0, residual, transformed)
```

and independently prepares:

```text
scaled_linear =
  (+0x60 * +0x90,
   +0x68 * +0x90,
   +0x70 * +0x90)
```

The next retail calls are:

```text
FUN_007bac60(body, transformed, scaled_linear)
FUN_007bae40(body, transformed)
FUN_007bb090(body, transformed, scaled_linear)
FUN_007bbb80(...)
FUN_007bb250(body)
FUN_007bb6c0(body)
```

Phase 616 does not execute those calls yet.

## Native implementation

The native physics library adds:

```text
evaluate_fun_007bc680_preprojection()
```

Inputs preserve the already-recovered body fields:

- `body_correction`: +0x30/+0x38/+0x40;
- `body_axis`: +0x18/+0x20/+0x28;
- `angular_state`: +0x48/+0x50/+0x58;
- `linear_state`: +0x60/+0x68/+0x70;
- `inverse_scalar`: +0x90;
- `body_frame`: the nine float coefficients consumed through body +0xb0.

The `FUN_007aefb0` port preserves the retail numeric boundary: residual
components are cast to float, the 3×3 coefficients are float, and the three
results are stored back as double.

Non-finite inputs fail closed.

## Regression

`shift_runtime_body_preprojection_check` covers:

1. identity transform with a hand-derived residual;
2. a nontrivial 3×3 transform that yields `[140, 320, 500]`;
3. an all-zero seed;
4. explicit non-finite rejection.

The checker emits `SHIFT.NativeBodyPreProjectionCheck/1` and keeps
`full_constraint_projection_executed=false`.

The Python runtime contract now exposes the same executable preprojection seed
through `evaluate_fun_007bc680_preprojection()`.

## Boundary after Phase 616

This phase closes only the deterministic input seed to the already-recovered
constraint projection equations.

Still open:

- native `FUN_007bac60` JOINT projection;
- native `FUN_007bae40` HINGE projection;
- native `FUN_007bb090` BAR projection;
- native `FUN_007bbb80/FUN_007bb250/FUN_007bb6c0` matrix coupling;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step BODY contribution evidence;
- provider-present dispatch.

No physical unit or coordinate-system interpretation is introduced.
