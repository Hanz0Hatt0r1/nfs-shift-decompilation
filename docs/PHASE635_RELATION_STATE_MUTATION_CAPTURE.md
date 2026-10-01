# Phase 635 — retail relation-state mutation event capture

Phase 634 closes the static dispatch from the recovered FL/FR/RL/RR component
slots into the set-only `FUN_00757d2c` relation-state mutation kernels. The
remaining blocker is runtime provenance: which slot is actually dispatched,
whether the slot spindle BODY exists at that instant, and where the call occurs
relative to the solver frame.

Phase 635 extends the existing retail GDB SDF probe with an observer breakpoint
at `FUN_00757d2c` (`0x00757d2c`). It records evidence only; it does not alter
retail state and it does not schedule the Phase 634 dispatcher in the Linux
runtime.

## Entry ABI proven from raw retail disassembly

At the exact function entry, before the first instruction executes:

- `ECX` is the vehicle pointer;
- `EAX` is `component_slot * 0xA80`;
- the first instruction computes `vehicle + 0x400 + EAX`.

The capture therefore derives the slot only when EAX is an exact member of:

- slot 0 / FL: `0x0000`;
- slot 1 / FR: `0x0A80`;
- slot 2 / RL: `0x1500`;
- slot 3 / RR: `0x1F80`.

No nearest-slot or modulo heuristic is used.

## Captured BODY identity inputs

For each breakpoint hit the probe records:

- vehicle pointer;
- raw EAX component offset;
- normalized 0..3 slot and FL/FR/RL/RR label;
- component block pointer `vehicle + 0x400 + EAX`;
- wheel BODY pointer from component `+0x420`;
- spindle BODY pointer from component `+0x424`;
- rear-axle BODY pointer from vehicle `+0x2E00`;
- whether the spindle pointer is nonzero;
- source branch: `wheel-rear-axle-pair` or `spindle-bar-endpoint`;
- raw caller return address;
- EAX/ECX/ESP/EIP register snapshot.

The stream is:

`relation_state_mutation_events.jsonl`

with format:

`SHIFT.ConstraintRelationStateMutationCaptureRuntime/1`.

## Shared solver timeline

Phase 635 also adds one monotonically increasing `runtime_event_sequence`
inside the GDB probe. The same sequence is attached to:

- `FUN_007b3f40` frame entry;
- `FUN_007b0f20` builtin solver entry;
- specialized-provider pre/post solve snapshots;
- `FUN_007b2210` scalar-reset events;
- `FUN_007b4110` post-solve entry;
- `FUN_00757d2c` relation-state mutation events.

Each mutation event additionally stores the most recently observed frame index,
that frame entry's event sequence, and scalar-reset counts at the instant of
the mutation. This gives a direct capture-time ordering key without assigning a
retail scheduler meaning in advance.

## Full mode only

The mutation observer is installed only in the normal/full `sdf-probe` mode.

`--provider-only` intentionally omits it because that mode also omits the
`FUN_007b3f40` frame-entry anchor. Recording the mutation there would preserve
raw pointers but would not satisfy the Phase 634 timing evidence gate.

The launcher and preflight contracts therefore expect
`relation_state_mutation_events.jsonl` only in full mode.

## Deliberate boundary

Phase 635 prepares the capture path; it does not claim that a real retail event
has been observed yet.

The Phase 634 dispatcher remains outside `shift_runtime` until an authentic
capture demonstrates:

1. a valid slot 0..3 event;
2. the observed spindle-presence branch;
3. stable BODY pointer identity for the selected wheel/spindle/rear-axle inputs;
4. event ordering relative to frame-entry/reset/solve/post-solve anchors.

After that evidence exists, the next safe step is an offline correlation
validator that converts the raw event stream into a fail-closed scheduler
admission artifact. Only that validated artifact should be considered for
native fixed-step integration.
