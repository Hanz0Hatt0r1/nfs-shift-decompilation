# Process 1 — Controller #1 manager APC reachability

This slice moves one level above the Controller #1 worker and asks whether the
manager updates executed by that controller have a **direct named-call path**
to the known asynchronous file-I/O / APC surface.

The proof uses the exact PC retail 1.02 `SHIFT.exe` and matching full Ghidra C
export. Xbox recompilation evidence is not required.

## Controller #1 manager set

The startup path `thunk_FUN_00d36000` attaches three manager objects to
Controller #1 through `FUN_006485b0`:

1. `Physics Manager` from `FUN_0070fe90()`;
2. `Camera Manager` from `FUN_0080bfb0()`;
3. `CameraScriptManager` from `thunk_FUN_0048993b()`.

The following `FUN_008695a0()` / `FUN_006984f0()` attachments belong to
Controller #2 and are excluded from this Controller #1 contract.

## Default update identities

The controller-side manager scheduler dispatches manager vtable slot `+0x18`.
For the three Controller #1 managers the exact PC tables resolve to:

- Physics Manager: `0x00b04524 + 0x18 -> FUN_00711b50`;
- Camera Manager: `0x00b157d8 + 0x18 -> 0x0080c990`, a five-byte jump thunk to
  source-visible `FUN_0080c920`;
- CameraScriptManager: `0x00ac5670 + 0x18 -> FUN_0050b5d0`.

The startup attach block, all three table prefixes, and the Camera Manager thunk
are machine-hash locked in the evidence artifact.

## Direct named-call closure

The analyzer indexes all source-visible Ghidra functions and computes the full
transitive closure of direct named calls from each normalized update root.
With the exact source hash the closures contain:

- `FUN_00711b50`: 2896 named functions;
- `FUN_0080c920`: 428 named functions;
- `FUN_0050b5d0`: 452 named functions.

None of the three closures reaches the recovered async-file initiators
`FUN_006557a0`, `FUN_00655900`, `FUN_00655ab0`, `FUN_00655c80`, either
completion routine, or a function body containing a direct `ReadFileEx` /
`WriteFileEx` call.

This closes the **direct named-call** manager route to the known file APC
surface.

## Limits

This is not a whole-program no-APC proof. In particular it does not resolve:

- indirect virtual calls inside any of the three closures;
- function-pointer callbacks whose concrete target is not source-visible at the
  callsite;
- aliases of async-file objects passed through generic containers;
- aliases of Controller #1 queue storage reached through generic queue APIs;
- any equivalence between Controller/Physics Manager cadence and rendered-frame
  cadence.

## Next Process 1 blocker

Resolve indirect/virtual callsites in the three Controller #1 manager update
closures against concrete object/vtable provenance. In parallel, classify
`FUN_00650350` producers by **queue object identity**, not by the shared queue
API name, to determine whether any render/presentation producer can reach the
Controller #1 queue indirectly.
