# Phase 376 — matrix-vector transform runtime

Phase 376 reconstructs FUN_007af0a0, the common transform used by the wheel
velocity, response-input and auxiliary contact-response paths.

## Exact representation

The transform object exposes nine float fields:

| Matrix field | Offset |
|---|---:|
| m00, m01, m02 | +0x00, +0x04, +0x08 |
| m10, m11, m12 | +0x0C, +0x10, +0x14 |
| m20, m21, m22 | +0x18, +0x1C, +0x20 |

Each double input component is converted to float before multiplication. Each
resulting float is widened back to double for the output array.

The recovered equations are:

- X = m20·Z + m00·X + m10·Y
- Y = m21·Z + m11·Y + m01·X
- Z = m22·Z + m12·Y + m02·X

The project deliberately does not rename this object as a specific matrix or
state-space convention.

## Consumers

The same helper is used in the already reconstructed FUN_00755f80,
FUN_00758fc0 and FUN_00766510 paths, so this phase removes a common external
transform boundary without changing their physical interpretation.
