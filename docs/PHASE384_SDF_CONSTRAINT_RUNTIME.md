# Phase 384 — SDF constraint runtime materialization

Phase 384 continues the non-rendering physics track from the real SHIFT.exe.c SDF loader and freezes the next proven boundary after the Phase 382 topology graph.

## Proven source boundary

FUN_007b3150 materializes each SDF constraint into a runtime record selected by the section flags:

| SDF section | flag | runtime stride | body counter | sample helper | sample stride |
|---|---:|---:|---:|---|---:|
| JOINT | 0x01 | 0xA0 | +0x98 | FUN_007ba8b0 | 0x40 |
| HINGE | 0x02 | 0xA0 | +0x9c | FUN_007ba900 | 0xA0 |
| BAR | 0x04 | 0xB8 | +0xa0 | FUN_007ba990 | 0x60 |
| JOINT&HINGE | 0x03 | two records: JOINT 0xA0 + HINGE 0xA0 | +0x98 / +0x9c | FUN_007ba8b0 + FUN_007ba900 | 0x40 / 0xA0 |

A JOINT&HINGE source section is materialized twice: once through the JOINT branch and once through the HINGE branch. The positive and negative body references are stored in runtime record slots +0x78 and +0x80. The record's node/aggregate index is written to +0x70. The post-load sample pointers occupy +0x7c and +0x84.

FUN_007b2ae0 copies the common constraint payload, including the flag byte and string/reference fields: constraint name +0x14, posbody +0x18, negbody +0x1c, copy-body name +0x20. It also copies the double-valued storage from +0x28..+0x68. Section-specific vectors are copied to:

- JOINT: source +0x28/+0x30/+0x38 -> runtime +0x88/+0x90/+0x98;
- HINGE: source +0x58/+0x60/+0x68 -> runtime +0x88/+0x90/+0x98;
- BAR: source +0x28..+0x50 -> runtime +0x88..+0xb0.

After sample construction, the source calls FUN_007b2da0, FUN_007b2de0 and FUN_007b2f70 for JOINT, HINGE and BAR respectively. Their coordinate/vector semantics remain represented as helper boundaries rather than assigned undocumented PhysX names.

## Implementation

rigid_body_sdf_runtime.py now exposes describe_sdf_constraint_runtime_lowering() as SHIFT.SDFConstraintRuntimeLowering/1.

vehicle_physics_asset_graph_runtime.py includes that contract in the generated vehicle physics profile so the BFF bundle entry point carries the constraint materialization evidence together with CDF/EDF/GDF/SDF topology.

## Regression coverage

The test suite now checks the JOINT&HINGE combined flag/counter behavior, per-section sampling strides/helpers, the exact positive/negative body slots, section-specific source/runtime vector offsets, and fail-closed handling when an endpoint name is missing.

## Explicit unknowns

PhysX SDK class names, provider ownership, physical units, and the higher-level meaning of the sampled endpoint data remain unresolved.
