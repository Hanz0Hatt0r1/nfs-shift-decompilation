# Phase 511 — IGPhaseVehicle completion/finalization boundary

## Goal

Close the concrete lifecycle boundary that follows the Phase 509
process/reselection loop.

Contract:

\`SHIFT.IGPhaseVehicleCompletionFinalization/1\`

## Completion finalizer

\`FUN_004d5930\` is called from \`FUN_004d5f30\` after the normal
participant-selection/load loop terminates.

It processes three owned containers:

| Field | Observed per-entry action |
|---|---|
| \`+0x3ec\` | dispatch through \`DAT_00c26058\` vtable \`+0x204\` |
| \`+0x3cc\` | dispatch through \`DAT_00c26058\` vtable \`+0x220\` |
| \`+0x40c\` | take \`entry+0xc\`, then \`thunk_FUN_00470711\` and \`FUN_0067a6b0\` |

After each container's iteration, \`FUN_00697420\` clears the container.

The contract intentionally does not invent names for these lists or the
dispatch slots.

## Guarded resource cleanup

Before returning, \`FUN_004d5930\` checks:

\`IGPhaseVehicle+0x3c8 != 0\`

When true it performs:

\`FUN_006372a0(IGPhaseVehicle+0x160)\`

and resets:

\`IGPhaseVehicle+0x3c8 = 0\`.

It then performs the observed cleanup sequence:

\`+0x8 → +0x160 → +0x3a4 → global +0x1758 → thunk_FUN_0050caa0\`

using the concrete helper calls recorded in the machine-readable contract.

## Callback ordering

The Phase 509 process path has two completion modes.

Normal completion:

\`FUN_004d5f30 → FUN_004d5930 → "IGPhaseVehicle: Process Done" → object vtable +0xc\`

Cockpit completion:

\`state +0x45c == 2 → thunk_FUN_00d7f900 → FUN_004d5930 → "IGPhaseVehicle: Process Cockpit Done" → object vtable +0xc\`

Therefore the final object callback occurs after the observed finalizer, not
before it.

## Destructor boundary

\`FUN_004d54a0\` performs broader teardown. It releases the \`+0x460\` object,
clears \`+0x3ec\`, \`+0x3cc\`, \`+0x40c\`, \`+0x3a4\` and \`+0x42c\`, calls
\`thunk_FUN_0050caa0\`, and releases \`+0xc\` when present.

This is kept separate from \`FUN_004d5930\`: completion finalization is part of
the process lifecycle; destructor teardown is object-lifetime cleanup.

## Cross-phase closure

Phase 509 established:

\`participant pointer/ordinal → process/reselection → BFF load → successful writeback → FUN_004d5930\`

Phase 511 adds:

\`FUN_004d5930 → owned-container callbacks/clears → guarded resource cleanup → thunk_FUN_0050caa0 → process callback\`

This closes the static post-process lifecycle boundary.

## Evidence boundary

No engine container type, ownership model, PhysX class identity, physical unit or
runtime numeric equivalence is inferred. Runtime capture remains separate.
