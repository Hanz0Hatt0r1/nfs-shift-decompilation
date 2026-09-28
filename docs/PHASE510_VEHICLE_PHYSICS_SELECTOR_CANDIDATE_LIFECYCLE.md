# Phase 510 — vehicle physics selector candidate lifecycle

## Goal

Close the descriptor-level state machine used by the \`DAT_00bbc600\` selector,
without inventing a higher-level class name for the descriptor records.

Contract:

\`SHIFT.VehiclePhysicsSelectorCandidateLifecycle/1\`

## Descriptor record

The retail source initializes a repeated descriptor record through
\`FUN_0040eec0\`. The records are laid out from:

- base: \`context+0xb8\`;
- stride: \`0x90\`;
- count: \`context+0x1c\`.

The constructor initializes, among other fields:

- \`+0x74 = 1\`;
- \`+0x7d = 1\`;
- \`+0x88 = 0\`;
- \`+0x8c = 0\`.

The present contract does not assign names to these fields beyond the directly
observed offsets.

## Two independent selector scans

\`FUN_00410ef0\` performs the Phase 508 selector-storage path. Its final
enumeration accepts the first candidate satisfying:

\`candidate+0x74 == 0\`

\`FUN_0043af50\` independently scans the original descriptor table at
\`context+0xb8\`, uses the same:

\`descriptor+0x74 == 0\`

test, writes the descriptor ordinal into:

\`descriptor+0x8c\`

and returns the ordinal together with the descriptor pointer. When no
eligible descriptor remains it returns \`-1\`.

This gives a concrete source-backed interpretation boundary for the repeated
descriptor table: the same byte/flag participates in multiple selection scans.

## Temporary exclusion during batch collection

\`FUN_004d69d0\` repeatedly calls \`FUN_0043af50(&DAT_00bbc600, ...)\`.

For every returned descriptor it temporarily writes:

\`descriptor+0x74 = 1\`

and retains the pointer. Collection is bounded at 16 descriptors. After the
collection phase, it resets the same flag to zero for all collected entries
before processing them.

The evidence therefore supports a narrow statement: \`+0x74\` acts as an
observed eligibility/exclusion state during selector scans and bounded batch
collection.

It does not by itself prove why the engine chooses this state or map it to a
named gameplay/physics concept.

## Separate post-load/process flag

\`FUN_00465860\` also consumes descriptors from \`DAT_00bbc600\`. After the observed
vehicle load/process step it writes:

\`descriptor+0x1d = 1\`

and then requests another descriptor.

This flag is deliberately kept separate from \`+0x74\`. Its wider semantics are
not established by the available static evidence.

## Cross-phase closure

Phase 508 established:

\`thunk_FUN_00453990 → FUN_00402435 → DAT_00bbc600\`

Phase 509 established:

\`IGPhaseVehicle+0x450/+0x454 → FUN_004d5f30 → FUN_00410ef0(&DAT_00bbc600) → BFF load → successful writeback\`

Phase 510 adds:

\`descriptor constructor → +0x74 initialization → selector scan/batch exclusion → ordinal at +0x8c\`

This closes an explicit descriptor-state boundary behind the already-resolved
selector object.

## Evidence boundary

No PhysX/engine class identity is assigned. No physical units are inferred.
No runtime instance identity or numeric provider equivalence is claimed.
Authentic runtime capture remains the evidence gate for those questions.
