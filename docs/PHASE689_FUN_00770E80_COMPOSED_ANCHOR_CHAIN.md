# Phase 689 — composed `FUN_00770e80` two-half-step anchor chain

Phase 689 composes the already admitted native anchor layers from Phases 683,
684 and 688 into one reusable outer-update boundary while keeping all unknown
refresh work external.

The static schedule proves:

```text
FUN_00770e80
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
  -> FUN_007b8810
  -> FUN_0076d100
  -> FUN_00765470(0.5 * dt)
  -> FUN_007b8810
```

Phase 684 preserves the required direct-call anchor sequence inside each
`FUN_0076d100` pass. Phase 688 preserves the machine-backed `FUN_00763570`
longitudinal transform path followed by the existing solver/post-solve/persistent
BODY integration chain inside the `FUN_00765470` half-step anchor.

Phase 689 now composes those already-proven pieces without asserting that the
remaining local work between anchors is implemented.

## Native contract

New files:

```text
native_runtime/include/shift_fun_00770e80_composed_anchor_chain.hpp
native_runtime/src/fun_00770e80_composed_anchor_chain.cpp
```

Format:

```text
SHIFT.NativeFun00770e80ComposedAnchorChain/1
```

The entry point is:

```text
execute_fun_00770e80_composed_anchor_chain(...)
```

It consumes:

- the outer timestep;
- initial raw persistent BODY bytes;
- a mandatory per-pass Phase 684 callback provider;
- a mandatory per-half-step Phase 688 input provider;
- the mandatory `FUN_007b8810` callback boundary.

The half-step provider receives:

```text
pass_index
half_timestep
current_body_bytes
```

and returns the complete typed Phase 688 input bundle for that half-step:

- machine `FUN_00763570` wheel inputs;
- generated BODY source frame;
- constraint relations;
- relation-derived reset state;
- builtin solver topology;
- post-solve projection;
- basis-rotation provider;
- tolerance.

This is intentional: Phase 689 does not manufacture or reuse those values as a
retail scheduling claim. Each half-step may receive independently refreshed
inputs from a higher proven producer when that evidence becomes available.

## Exact state handoff

The only state Phase 689 carries automatically between the two half-steps is the
raw persistent BODY buffer already proven by the Phase 677–688 chain:

```text
initial BODY bytes
  -> half-step 0 Phase 688
  -> persistent BODY bytes 0
  -> half-step 1 provider + Phase 688
  -> persistent BODY bytes 1
  -> final BODY bytes
```

The second provider receives byte-for-byte the first Phase 688 output. No hidden
reconstruction or field copy occurs at this boundary.

## Physics-pass anchor provider

For each of the two `FUN_0076d100` passes, the required provider returns five
callbacks consumed by Phase 684:

```text
FUN_00765c40
FUN_00758b50
FUN_00766510
FUN_007675f0
FUN_007682c0
```

The existing Phase 684 implementation preserves their required relative order and
the nested `FUN_00769ef0` tail relationship. Phase 689 does not promote any of
these callback boundaries to complete retail function implementations.

## Reference oracle

Scheduling oracle:

```text
src/physics/fun_00770e80_composed_anchor_chain_runtime.py
```

Regression:

```text
tests/test_fun_00770e80_composed_anchor_chain_runtime.py
```

The oracle freezes the repeated order:

```text
Phase 684 provider
-> Phase 684 executor
-> Phase 688 provider(current BODY bytes)
-> Phase 688 executor
-> FUN_007b8810
```

for pass indices `0,1`, and proves that pass 1 receives exactly the BODY bytes
returned by pass 0.

## Native regression

`shift_runtime_fun_00770e80_composed_anchor_chain_check` uses the established
Phase 688 deterministic two-BODY / six-scalar fixture.

The fixture deliberately returns a complete typed solver/constraint bundle from
the half-step provider on each pass. That repeated fixture is only a regression
input; it is not promoted to a statement that retail reuses identical solver
state.

At outer timestep `0.5`, the proven schedule supplies `0.25` to both half-step
anchors. With the deterministic zero-solution fixture and identity basis callback,
BODY 0 progresses:

```text
initial origin       = (1.0, 2.0, 3.0)
after half-step 0    = (2.0, 3.25, 4.5)
after half-step 1    = (3.125, 4.65625, 6.1875)
```

The regression checks:

- exactly two Phase 684 pass providers/executions;
- all five Phase 684 anchors exactly once per pass;
- exactly two Phase 688 half-step providers/executions;
- exact raw BODY output 0 -> input 1 handoff;
- exact `FUN_007b8810` order after each half-step;
- final BODY bytes equal the second Phase 688 output;
- fail-closed missing provider, incomplete pass callback set and non-finite outer
  timestep.

## Evidence boundary

Phase 689 proves a larger native **anchor chain**, not complete scheduler parity.
The report therefore keeps these distinctions explicit:

```text
phase684_required_anchor_sequence_reused = true
phase688_machine_half_step_reused = true
persistent_body_bytes_carried_between_half_steps = true
per_pass_physics_refresh_proven = false
per_half_step_solver_refresh_proven = false
intervening_local_work_modeled = false
rendered_frame_cadence_proven = false
complete_fun_00770e80_semantics = false
```

## Non-goals

Phase 689 does **not**:

- claim complete `FUN_0076d100`, `FUN_00765470` or `FUN_00770e80` behavior;
- invent local arithmetic/calls between proven anchors;
- infer how solver/contact inputs are refreshed between passes;
- infer that `FUN_00770e80` executes once per rendered frame;
- infer input/control ownership;
- implement the remaining partial wheel/contact response producers;
- close the independent `FUN_007afdd0` scalar-production/x87 control-state gate;
- create or admit the final vehicle participant;
- run `SHIFT.exe` or request new runtime capture.
