# Phase 687 — machine-backed transform operand precision correction

Phase 687 corrects an older source-shaped assumption in the native transform
family used throughout BODY/constraint physics.

The recovered C decompile renders `FUN_007aefb0` and `FUN_007af0a0` as if each
input double component were cast to float before multiplication.  Phase 629
therefore implemented that cast.  Direct audit of the matching retail PE proves
that interpretation is wrong: the x87 instructions multiply float32 matrix
coefficients by **QWORD / float64** operands.

This phase also freezes and ports the adjacent `FUN_007af010` scalar-to-column
helper needed by the wheel longitudinal path.

## Retail identity

Executable:

```text
SHIFT.exe MD5 705af8b420e5eb1e3834ac43d5533c6b
x86 PE image base 0x00400000
```

Recovered source:

```text
SHIFT.exe.c SHA256 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

Machine-readable evidence:

```text
evidence/transform_machine_precision.json
SHIFT.TransformMachinePrecisionEvidence/1
```

## `FUN_007aefb0`

Exact retail range:

```text
0x007aefb0..0x007af002
83 bytes
SHA256 76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29
```

The machine sequence uses `FLD m32real` for matrix values and `FMUL m64real`
for vector values.  Component order is:

```text
x: m01*y -> + m00*x -> + m02*z
y: m10*x -> + m11*y -> + m12*z
z: m20*x -> + m21*y -> + m22*z
```

There is no f64-to-f32 conversion of `x/y/z`.

## `FUN_007af0a0`

Exact retail range:

```text
0x007af0a0..0x007af0f2
83 bytes
SHA256 8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc
```

The same operand widths are used, with the transposed coefficient order:

```text
x: m10*y -> + m00*x -> + m20*z
y: m01*x -> + m11*y -> + m21*z
z: m02*x -> + m12*y -> + m22*z
```

This also corrects the old C++ expression ordering, which began each component
with the third product rather than the first x87 product.

## `FUN_007af010`

Exact retail range:

```text
0x007af010..0x007af032
35 bytes
SHA256 f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324
```

The function loads the scalar as QWORD and keeps it on the x87 stack while it
multiplies the first matrix column:

```text
out.x = m00 * scalar
out.y = m10 * scalar
out.z = m20 * scalar
```

Again, there is no scalar double -> float conversion despite the decompiler's
local `float fVar1` presentation.

## Native correction

`native_runtime/src/constraint_sample_refresh.cpp` now:

- preserves vector/scalar inputs as doubles;
- converts only the stored matrix coefficients from their native float32 form;
- evaluates products/additions in exact retail instruction order;
- uses `long double` intermediates to model the x87 extended stack before each
  final double store;
- exposes `transform_fun_007af010_refresh()` alongside the existing two helpers;
- retains the existing non-finite fail-closed checks.

This correction automatically reaches every existing native consumer of
`transform_fun_007aefb0_refresh()` and `transform_fun_007af0a0_refresh()`,
including constraint refresh, BODY preparation, wheel/contact response, and
persistent BODY integration.

## Regression discriminators

The Phase 687 regression deliberately uses inputs that the old implementation
cannot pass.

### QWORD operand discriminator

```text
1.0 + 2^-30
```

is distinct in binary64 but rounds to exactly `1.0f`.  An identity transform must
return the original binary64 value.  The old f32-cast implementation returned
`1.0`; retail and Phase 687 preserve the perturbation.

### Operation-order discriminator

For a component with all three coefficients equal to one:

```text
vector = (1e20, -1e20, 1)
```

retail order evaluates:

```text
(-1e20 + 1e20) + 1 = 1
```

The old reversed expression order can lose the trailing one.  The native
regression requires the retail result.

## Canonical Python contract

`src/core/matrix_vector_transform_runtime.py` is upgraded to:

```text
SHIFT.MatrixVectorTransformRuntime/3
```

It now records the machine byte hashes, QWORD input widths, operation order, and
all three helper identities.  Python arithmetic remains binary64, so it is a
contract/orchestration oracle rather than a claim to emulate every x87 extended
intermediate.

## Remaining precision boundary

This phase proves function bytes, operand widths, coefficient offsets and
instruction order.  It does **not** prove the ambient x87 control word at every
callsite.  The native implementation uses Linux `long double` for extended
intermediates, which matches the structural x87 dataflow and removes the known
f32 truncation bug, but the report remains explicit:

```text
ambient_x87_control_word_proven = false
```

No assumption about rendered-frame cadence, vehicle ownership, or physical units
is introduced.

## Effect on Phase 686

Phase 686 still keeps the transform producer typed/external because its provider
shape includes both localization and reconstruction results.  Phase 687 now
provides the missing machine-backed arithmetic primitives needed to replace that
precomputed-vector boundary in a later composition phase without guessing the
matrix convention or scalar width.
