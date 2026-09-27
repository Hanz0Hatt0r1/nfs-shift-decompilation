# Phase 361 — tyre model and slip-curve runtime

Phase 361 continues from the HDV wheel/physics loader into the tyre data path. The
primary source is the recovered retail SHIFT.exe.c with SHA-256
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9.

## TBC loading

FUN_007a10f0 is the tyre-manager loader. It scans the TBC resource for [SLIPCURVE]
and [COMPOUND] sections, counts both record classes, allocates fixed-size vectors,
then revisits the file and fills the corresponding records.

The observed element sizes are 0x38 bytes for slip curves and 0x610 bytes for
compounds. Named compound fields include Tyre Lat Drag Reduction at +0x08,
Tyre Long Drag Reduction at +0x10, Style at +0x24 and LaunchControlFactor at +0x28.

Compound selection accepts the recovered scope tokens NONE:, FRONTLEFT:, FRONTRIGHT:,
REARLEFT:, REARRIGHT:, FRONT:, REAR:, LEFT:, RIGHT: and ALL:.

## Slip-curve registry

Each slip-curve record exposes named parameters for dry/wet slide, cornering/braking/
self-aligning stiffness, camber stiffness, design load, load sensitivity, peaks,
temperature/pressure response, heating/transfer/wear parameters and AI controls.

The registry stores three curve-name references at +0x138/+0x13c/+0x140:
LatCurve, BrakingCurve and TractiveCurve.

## Curve compilation

FUN_007a07c0 converts sampled curve points into compiled records with 0x28-byte
stride. The compiled record contains four doubles at +0x08/+0x10/+0x18/+0x20 used
as cubic coefficients by the runtime evaluator, while +0x18/+0x20 also retain the
observed global maximum value and its position in the source object.

The compiler uses FUN_007af310 with dimension 4 while constructing each segment, then
normalizes coefficients by the recovered maximum. It also scans the resulting cubic
pieces for a larger local maximum before normalization.

This is recorded as arithmetic evidence, not as a guessed tyre-law model.

## Curve evaluation

FUN_007a0c00 evaluates a precompiled curve with Horner-form cubic evaluation. The
segment selection uses FUN_00715990, which is exactly ROUND(float), and clamps the
resulting index to count-1. The runtime path seen in FUN_007572f0/FUN_00757318 binds
LatCurve/BrakingCurve/TractiveCurve and samples LatCurve at 0.0001 three times before
forming the inverse-origin-slope field at wheel-runtime +0x6f0. The arithmetic is
frozen in the contract; semantic units are deliberately left unresolved.

## Response helpers

FUN_007a0490 computes the observed affine thermal-response expression from four
compound fields and the constant 273.16:

((field_0x1e0 + 273.16) * input / (field_0x1e8 + 273.16)) * field_0x90 + field_0x88

FUN_007a06a0 constructs a cubic response through a 4x4 linear solve and emits four
double coefficients. The solver dimension and arithmetic are proven; the exact
physical interpretation of each response input is not.

FUN_007a05c0 converts selected curve fields between the observed angular/scalar
representations. No extra unit labels are added beyond constants directly visible in
the recovered instructions.

## Wheel runtime binding

FUN_007572f0 and FUN_00757318 copy the selected compound into each wheel runtime,
resolve the three curve names through FUN_007a1010, build load/temperature response
coefficients and cache multiple derived fields. These functions are the first clear
bridge from static TBC tyre data into the per-wheel physics state.

## Verification

Added:
- SHIFT.TireModelRuntime/1;
- compact source-evidence fingerprint;
- regression coverage for TBC sizes, scope tokens, property offsets, curve binding,
  cubic Horner evaluation and source markers.

The renderer and RENDER.bff remain untouched.
