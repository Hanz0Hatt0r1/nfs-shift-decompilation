# Phase 655 — native BODY frame preparation

Phase 655 ports three already source-backed BODY preparation primitives from the
Python evidence layer into `shift_runtime_physics`. These functions prepare the
internal frame-dependent state consumed by the constraint path; they do not
integrate the vehicle pose.

The native contract is:

```text
SHIFT.NativeBodyFramePreparation/1
```

implemented by:

- `native_runtime/include/shift_body_frame_preparation.hpp`;
- `native_runtime/src/body_frame_preparation.cpp`;
- `native_runtime/tests/body_frame_preparation_check.cpp`.

## `FUN_007ba860` coefficient initialization

The source writes the three input coefficients as float32 at:

```text
BODY +0x128
BODY +0x12c
BODY +0x130
```

and writes reciprocal doubles computed from the original, pre-truncation inputs
at:

```text
BODY +0x138
BODY +0x140
BODY +0x148
```

The native implementation preserves that distinction: float storage is produced
with the retail-width cast, while each reciprocal is `1.0 / original_double`.
Zero and non-finite inputs fail closed.

## `FUN_007ba630` symmetric BODY tensor

The function consumes the reciprocal/diagonal values associated with
`+0x138/+0x140/+0x148` and the float32 3x3 basis at `+0xd4..+0xf4`.

It evaluates the source-backed operation:

```text
B * diag(D) * transpose(B)
```

using float32 inputs/results and stores the symmetric 3x3 tensor in the retail
`+0xb0..+0xd0` region. The native API deliberately exposes this as a raw tensor;
no inertia or coordinate-system interpretation is added.

The regression freezes both an identity-basis case and the nontrivial fixture:

```text
D = (2, 3, 5)
B = ((1,2,3), (4,5,6), (7,8,9))

result =
  59 128 197
 128 287 446
 197 446 695
```

## `FUN_007ba7e0` frame-vector preparation

The native implementation reuses the exact transform helpers already admitted
for Phase 629:

```text
local = FUN_007af0a0(BODY+0xd4, BODY+0x18)
scaled = float32(local * BODY+0x128 coefficients)
out = FUN_007aefb0(BODY+0xd4, scaled)
```

The result corresponds to the retail writes at:

```text
BODY +0x30
BODY +0x38
BODY +0x40
```

and structurally equals:

```text
M^T * diag(C) * M * v
```

with the original float32 conversion boundaries retained. The regression uses
the existing Python oracle fixture and requires:

```text
basis = diag(1,2,3)
body vector = (1,2,3)
scale = (4,5,6)
local = (1,4,9)
scaled = (4,20,54)
output = (4,40,162)
```

## Boundary

The BODY origin used by `FUN_007ba9e0` is independently source-backed at
`+0x00/+0x08/+0x10`. Phase 655 does not write those fields.

Likewise, the basis at `+0xd4..+0xf4` is consumed as an input here; this phase
does not establish the function that advances that basis over time.

Therefore Phase 655 does **not** implement or claim:

- `position += velocity * dt` or any equivalent translational integration;
- orientation integration;
- a physical velocity interpretation for the persistent `+0x60/+0x68/+0x70`
  accumulator channels;
- any mapping from vehicle input controls into BODY motion.

It removes three remaining Python-only arithmetic boundaries so the next
writer-chain work can operate on a larger source-backed native BODY state rather
than inventing missing pose semantics.
