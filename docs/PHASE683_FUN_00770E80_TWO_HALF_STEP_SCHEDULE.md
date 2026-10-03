# Phase 683 — `FUN_00770e80` two-half-step anchor schedule

Process 1 static evidence proves that `FUN_00770e80` contains two repeated
anchor groups in this exact direct-call order:

```text
FUN_0076d100
FUN_00765470(0.5 * outer_dt)
FUN_007b8810
```

followed by the same three anchors a second time.

Phase 683 ports only that scheduling fact. It does not invent the unfinished
internals of any callback boundary and does not claim one invocation per rendered
frame.

## Native contract

New files:

```text
native_runtime/include/shift_fun_00770e80_two_half_step_schedule.hpp
native_runtime/src/fun_00770e80_two_half_step_schedule.cpp
```

Format:

```text
SHIFT.NativeFun00770e80TwoHalfStepSchedule/1
```

The native orchestrator requires three callbacks:

- `FUN_0076d100` pass boundary;
- `FUN_00765470` half-step boundary;
- `FUN_007b8810` post-half-step boundary.

All three are mandatory. Their internal semantics remain external.

For finite `outer_timestep` the orchestrator computes one f64 value:

```text
half_timestep = outer_timestep * 0.5
```

and executes exactly:

```text
pass[0]
half_step[0](half_timestep)
post_half_step[0]
pass[1]
half_step[1](half_timestep)
post_half_step[1]
```

## Reference oracle

Python contract/oracle:

```text
src/physics/fun_00770e80_two_half_step_schedule_runtime.py
```

Regression:

```text
tests/test_fun_00770e80_two_half_step_schedule_runtime.py
```

It checks exact callback order, both half-step timesteps, preservation of negative
zero through the f64 multiply, missing callback rejection and non-finite timestep
rejection.

## Native persistent-state regression

`shift_runtime_fun_00770e80_two_half_step_schedule_check` connects the new
scheduler boundary to the already admitted Phase 682 BODY path inside the
`FUN_00765470` callback.

The fixture begins with one raw `0x170` BODY record whose x motion triplet is
`4.0`. With:

```text
outer_dt = 0.5
half_dt  = 0.25
```

two admitted BODY integrations produce:

```text
origin.x: 0 -> 1 -> 2
motion.x: 4 -> 4 -> 4
```

The basis rotation stays on the recovered zero path through the mandatory Phase
682 scalar provider. The regression also verifies that an unrelated BODY byte is
preserved.

This proves that persistent native BODY state can cross both statically proven
half-step anchors without asserting that the currently external callback bodies
are already complete retail implementations.

## Evidence boundary

Phase 683 does **not** prove or implement:

- complete `FUN_0076d100` behavior;
- complete `FUN_00765470` behavior;
- semantic meaning of `FUN_007b8810`;
- the other local work performed by `FUN_00770e80` outside these direct-call
  anchors;
- caller/object ownership above `FUN_00770e80`;
- rendered-frame cadence;
- input/control ownership;
- exact machine production of the Phase 682 `FUN_007afdd0` scalar provider.

Accordingly the report keeps:

```text
callback_bodies_external = true
complete_fun_00770e80_semantics = false
rendered_frame_cadence_proven = false
```

The next native integration step should replace one callback boundary only when
its own source/static contract is strong enough; this scheduler must not be used
as evidence for unproven callback internals.
