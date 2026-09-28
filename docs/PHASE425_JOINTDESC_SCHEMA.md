# Phase 425 — JointDesc schema and constructor defaults

Phase 425 closes the next source-backed constraint-definition layer by extracting the \`JointDesc\` and \`JointLimitDesc\` registration schemas from the retail \`SHIFT.exe.c\` snapshot.

## Recovered \`JointDesc\`

\`FUN_007b9100\` registers the following fields with exact offsets and observed serializer type-ids:

- \`Object1\` \`+0x14\`
- \`Object2\` \`+0x18\`
- \`Anchor1\` \`+0x1c\`
- \`Anchor2\` \`+0x28\`
- \`Axis1\` \`+0x34\`
- \`Axis2\` \`+0x40\`
- \`Normal1\` \`+0x4c\`
- \`Normal2\` \`+0x58\`
- \`Breakable\` \`+0x64\`
- \`LimitsEnabled\` \`+0x68\`
- \`LimitMin\` \`+0x6c\`
- \`LimitMax\` \`+0x70\`
- \`BreakLimit\` \`+0x74\`

The joint type field is at \`+0x10\`.

## Recovered \`JointLimitDesc\`

\`FUN_007b95d0\` registers:

- type at \`+0x10\`
- \`Value\` at \`+0x14\`
- \`Restitution\` at \`+0x18\`
- \`Spring\` at \`+0x1c\`
- \`Damping\` at \`+0x20\`

Observed serializer type-ids are preserved as opaque values rather than being assigned unsupported semantic names.

## Constructor defaults

\`FUN_007b9030\` explicitly writes:

- joint type \`1\`;
- one non-zero component for Axis1, Axis2, Normal1 and Normal2;
- \`Breakable=0\`;
- \`LimitsEnabled=0\`;
- \`LimitMin=0\`;
- \`LimitMax=0\`;
- \`BreakLimit=0\`.

The helper exposes the corresponding unit-vector defaults only as a direct consequence of the explicitly written components and the constructor's base-zeroed storage; it does not add a physical-unit conversion.

## Integration target

The schema is now available as machine-readable evidence for the existing SDF constraint/materialization chain. The next unresolved step is runtime use/application of these descriptor properties at the SDK/provider boundary, not the schema itself.
