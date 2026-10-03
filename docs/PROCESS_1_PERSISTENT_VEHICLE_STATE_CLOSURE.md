# Process 1 — persistent vehicle-state closure audit

This block reconciles the current static evidence after the BODY frame integrator
was recovered.  It does not run the original game and does not consume runtime
capture.

The machine-readable composition tool is:

```text
tools/ghidra/build_persistent_vehicle_state_closure.py
```

Output format:

```text
SHIFT.PersistentVehicleStateClosure/1
```

## Why this layer exists

Older writer-frontier documents intentionally stopped before the persistent BODY
integrator was known.  Current `main` is stronger:

```text
FUN_00770e80
  -> FUN_0076d100
  -> FUN_00765470
       -> FUN_007b3f40
       -> FUN_007b4110
       -> FUN_007b2270
            -> FUN_007bab70
```

`SHIFT.BodyFrameIntegrationStatic/1` proves the `FUN_007bab70` persistent BODY
state transition, while `SHIFT.GhidraBodyUpdateScheduleFrontier/2` proves its
placement after the solver/post-solve path.  Therefore Process 1 must no longer
spend targeted RE work searching for an unknown accumulator-to-motion or
motion-to-pose writer on this path.

The open frontier is now above `FUN_00770e80`: caller/object ownership,
input/control provenance, the ownerless alternate caller and rendered-frame
cadence.

## Inputs

The closure audit consumes three independently generated static reports:

1. `SHIFT.GhidraBodyUpdateScheduleFrontier/2`;
2. `SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1`;
3. `SHIFT.OuterUpdateCallsiteStatic/1`.

It fails closed unless those reports still agree on the current anchors:

```text
outer update              0x00770e80
physics pass              0x0076d100
half-step orchestrator    0x00765470
BODY array loop           0x007b2270
BODY integrator           0x007bab70
outer receiver            DAT_00c13700
```

It also requires exactly the two currently corroborated direct callers:

```text
0x00794a30 -> 0x00770e80
0x0079b2d0 -> 0x00770e80
```

If `FUN_0079b2d0` gains a direct incoming edge in a newer export, the tool aborts
instead of preserving the stale `ownerless` conclusion.

## Current proven/verified graph

The composed graph separates direct execution evidence from object ownership:

```text
FUN_00715380
  -> FUN_00713050
       -> FUN_00794a30 (three direct calls in the recovered batch path)
            -> FUN_00770e80(&DAT_00c13700, ...)
                 -> two FUN_0076d100 passes
                 -> after each pass: FUN_00765470
                      -> solve/post-solve
                      -> FUN_007b2270
                           -> FUN_007bab70
```

The alternate direct path is also retained:

```text
UNKNOWN OWNER
  -?-> FUN_0079b2d0
        -> FUN_00770e80(&DAT_00c13700, ...)
```

The direct `FUN_0079b2d0 -> FUN_00770e80` edge is proven.  Its incoming owner is
not.

## Candidate records

The audit emits one record for each current upper-frontier candidate and stores:

- address;
- direct callers/callees visible in the composed reports;
- source-backed read/write offsets where the input contracts expose them;
- pointer/base evidence without promoting class identity;
- exact source/callgraph evidence statements;
- subsystem;
- one of `proven`, `verified`, `inferred`, `ambiguous`, `unknown`;
- unresolved blockers.

Current candidate summary:

### `FUN_00794a30`

Verified facts:

- writes caller `+0x1aa8/+0x1ab0` from function arguments before the outer update;
- tests caller `+0x234` in the source-backed gate;
- directly calls `FUN_00770e80` once;
- its three direct incoming sites come from `FUN_00713050`.

Still unknown:

- final class identity;
- input/control provenance of the supplied channel values;
- rendered-frame cadence.

### `FUN_0079b2d0`

Verified local facts:

- reads caller `+0x34`, `+0x234`, `+0x1aa8`, `+0x1ab0` on the relevant path;
- directly calls `FUN_00770e80` once;
- the current direct callgraph has no incoming edge;
- its internal computed jump remains separate evidence and is not treated as the
  missing external dispatcher.

Evidence state remains `ambiguous` at the object/ownership level.

### `FUN_00713050`

Verified source/callgraph facts:

- container/base field `+0x140`;
- count `+0x144`;
- channel seed `+0x160`;
- source-visible accumulator `+0x348`;
- record stride `0x1fa0`;
- child object adjustment `*record + 0x340`;
- three correlated calls to `FUN_00794a30`.

This is a container/update shape, not a promoted gameplay class.

### `FUN_00715380`

Only the source/callgraph edge into `FUN_00713050` is imported here.  Adjacency is
not promoted to ownership or scheduler identity.

## Remaining blockers

The closure report keeps four unresolved boundaries explicit:

1. `input-control-owner` — identify the static caller/argument provenance that
   feeds the verified update chain;
2. `alternate-caller-dispatch-owner` — explain the missing incoming owner of
   `FUN_0079b2d0` through code/data refs, callback tables, vtable evidence, or an
   equivalent static mechanism;
3. `rendered-frame-cadence` — prove scheduling frequency rather than assuming one
   update per rendered frame;
4. `upper-object-lifecycle` — connect constructors/vtables/destructors or class
   registration evidence to the anonymous upper update objects.

## Targeted export plan

The generated priority order is:

```text
0x0079b2d0  priority 0 — references + p-code + vtable/static-table references
0x00715380  priority 1 — callers + p-code + strings + ctor/vtable references
0x00713050  priority 1 — p-code + caller argument provenance
0x00794a30  priority 2 — p-code + caller argument provenance
```

This deliberately targets the unresolved upper frontier instead of re-exporting
already closed BODY integration functions.

## Run

After generating the three source reports:

```bash
python3 tools/ghidra/build_persistent_vehicle_state_closure.py \
  out/body_update_schedule_frontier.json \
  out/vehicle_outer_update_caller_frontier.json \
  out/outer_update_callsite_static.json \
  --json-out out/persistent_vehicle_state_closure.json \
  --targets-out out/persistent_vehicle_state_targets.txt
```

The target list can then feed the existing targeted instruction/p-code exporters.
Reference/vtable work for `FUN_0079b2d0` should use the existing static Ghidra
artifacts as discovery aids, while promotion still requires exact pointer/dispatch
evidence.

## Fail-closed policy

This layer explicitly does **not** claim:

- that an offset pattern proves BODY/vehicle identity;
- that pointer similarity proves ownership;
- that direct-call adjacency proves a semantic method role;
- that the two 64-bit channels have known physical units;
- that `FUN_00770e80` runs once per rendered frame;
- that `FUN_0079b2d0` is a root because no direct caller is present;
- that any anonymous function has a recovered retail class/method name.

The BODY integrator is ready for native handoff from static evidence.  The full
`input/control -> ... -> next frame` chain remains not-ready until the upper
ownership and scheduling blockers are closed.
