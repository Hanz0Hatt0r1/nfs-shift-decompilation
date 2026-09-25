# Phase 248 — animation TRACK/node runtime semantics

This phase isolates the proven XML animation runtime contract recovered from the
retail SHIFT.exe.c. It does not equate XML track-form names with numeric BAB
channel ids.

## Recovered target usage

FUN_00a67540 maps usage to four runtime targets:

- translation = 0
- rotation = 1
- scale = 2
- weight = 3

## Recovered track forms

The parser dispatches ten forms:

SampledVec3f, SampledQuatf, Sampledf32, KeyedVec3f, KeyedQuatf, Keyedf32,
FixedVec3f, FixedQuatf, FixedEulerf, Fixedf32.

Vec3 attachers accept translation or scale and reject rotation. Quaternion
attachers accept rotation only. f32 attachers accept weight only. Transform
slots reject a second track of the same target.

FixedEulerf shares the fixed Vec3 parser/attacher, with an additional runtime
Euler-to-quaternion conversion whose axis/order convention remains unresolved.

## Serialization evidence

The XML readers parse vec3f and quatf child values using %08X words. The module
therefore preserves exact IEEE-754 bit patterns. Sampled tracks use sampleinterval;
keyed tracks carry per-key timestamps.

Node base-transform defaults recovered from FUN_00a670b0 are:

- translation (0,0,0)
- rotation (1,0,0,0)
- scale (1,1,1)

FUN_00a64630 maps animation nodes by exact names, and FUN_00a64d90 requires the
built node count to equal the expected count.

Duration consistency is kept as a separate contract derived from FUN_00a64be0.

This phase does not implement parent-pose composition, final clip selection, or
renderer integration.

Source evidence SHA-256: 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
