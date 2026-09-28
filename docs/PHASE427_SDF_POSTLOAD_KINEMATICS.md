# Phase 427 — SDF constraint post-load kinematics

Phase 427 extends the SDF physics reconstruction past runtime constraint materialization into the post-load sample preparation helpers.

## FUN_007b2ae0

The runtime-copy boundary is now machine-readable. The function copies:

- type at +0x10;
- string references at +0x14/+0x18/+0x1C/+0x20 through FUN_00632920;
- nine consecutive 64-bit fields at +0x28 through +0x68.

## JOINT and HINGE

FUN_007b2da0 applies the forward transform helper FUN_007aefb0 to endpoint samples using each body's +0xD4 pose block.

FUN_007b2de0 performs two forward transforms, one inverse transform through FUN_007af0a0, then closes the second vector with the exact sequence:

    cross = v0 x v1
    v1_after = v0 x cross

The transform helpers remain explicit black-box boundaries; no matrix convention is guessed.

## BAR

FUN_007b2f70 transforms both endpoint positions, computes:

    delta = endpoint1_transformed - endpoint2_transformed

and normalizes delta when its squared length is non-zero. The resulting direction is written to both endpoint sample records at +0x40/+0x48/+0x50.

The module exposes these arithmetic stages as deterministic Python functions, allowing them to be compared with future captured runtime state without introducing PhysX assumptions.
