# Phase 428 — exact SDF 3x3 transform helpers

Phase 428 resolves the transform-helper boundary left explicit in Phase 427.

## Recovered helpers

FUN_007aefb0 reads a 3x3 float matrix at the body runtime block beginning at +0xD4:

    m00 +0xD4   m01 +0xD8   m02 +0xDC
    m10 +0xE0   m11 +0xE4   m12 +0xE8
    m20 +0xEC   m21 +0xF0   m22 +0xF4

It computes the ordinary row-major matrix-times-vector result.

FUN_007af0a0 uses the transposed coefficient ordering. The reconstruction names this operation "transposed" rather than assuming a mathematical inverse for arbitrary matrices.

Both helpers cast input vector components to float, consume float matrix entries and write the resulting three components as double values.

## Integration

The JOINT/HINGE/BAR post-load runtime from Phase 427 can now use deterministic matrix arithmetic at the exact helper boundary. Translation is not part of these functions; position addition/subtraction performed by callers remains a separate operation.
