# Phase 616 — native FUN_007bc680 BODY projection seed

Phase 615 gates every fixed-step builtin solve with an exact prepared BODY
export witness, but the BODY-local contribution arrays are still supplied as
external evidence.

Phase 616 begins closing that gap at the first deterministic arithmetic boundary
inside `FUN_007bc680`.

## Scope

This phase implements only the source-backed seed that runs before the
JOINT/HINGE/BAR contribution helpers.

For one BODY, the recovered residual is:

```text
x = +0x48 - (+0x40 * +0x20 - +0x38 * +0x28)
y = +0x50 - (+0x30 * +0x28 - +0x40 * +0x18)
z = +0x58 - (+0x38 * +0x18 - +0x30 * +0x20)
```

That triplet is passed through the exact `FUN_007aefb0` coefficient ordering
using the BODY 3×3 float frame.

The BODY linear triplet:

```text
+0x60 / +0x68 / +0x70
```

is multiplied component-wise by the scalar at `+0x90`.

The outputs are the two inputs consumed by the later constraint-projection
helpers.

## Native API

New files:

- `native_runtime/include/shift_body_projection_seed.hpp`;
- `native_runtime/src/body_projection_seed.cpp`.

The API is:

`build_body_projection_seed()`.

It returns:

- raw three-component residual;
- `FUN_007aefb0` transformed residual;
- scaled linear triplet.

All explicit inputs and outputs must remain finite.

## Transform boundary

The transform preserves the Phase 428/429 recovered helper contract:

- nine matrix coefficients are float32;
- the three input components are cast to float32;
- coefficient ordering is exactly `FUN_007aefb0`;
- the resulting components are exposed as doubles.

No coordinate-system semantic name is assigned.

## Deterministic regression

New executable:

`shift_runtime_body_projection_seed_check`.

The frozen case uses:

- angular state `[10, 20, 30]`;
- axis state `[1, 2, 3]`;
- prepared BODY state `[4, 5, 6]`;
- linear state `[2, -4, 8]`;
- scalar `0.25`;
- non-identity 3×3 matrix `[1..9]`.

It must produce:

```text
residual             = [13, 14, 33]
transformed_residual = [140, 320, 500]
scaled_linear        = [0.5, -1, 2]
```

The checker also requires non-finite input rejection.

Linux Vulkan CI runs the CTest target and freezes the source-function and
transform-function identities.

## Deliberate boundary

Phase 616 does **not** claim full `FUN_007bc680`.

Still open inside that function:

- `FUN_007bac60` JOINT projection;
- `FUN_007bae40` HINGE projection;
- `FUN_007bb090` BAR projection;
- `FUN_007bbb80` shared post-projection stage;
- `FUN_007bb250` HINGE coupling;
- `FUN_007bb6c0` BAR coupling;
- generation of complete BODY `+0x150/+0x154` contribution arrays.

Runtime sampled-state refresh `FUN_007b3ed0`, reset-node selection and
provider-present dispatch remain independent gates.

## Next

The next safe step is to port the already source-backed JOINT/HINGE/BAR scalar
projection equations into native code against explicit prepared sample rows,
then join their outputs to the Phase 616 seed without deriving unavailable
runtime sampled state.
