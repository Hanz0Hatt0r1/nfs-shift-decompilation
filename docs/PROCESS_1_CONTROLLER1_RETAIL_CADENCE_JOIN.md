# Process 1 — Controller #1 lifecycle to retail cadence join

This is a cross-evidence adjudication, not a new machine-code recovery.

It joins three already-authoritative contracts:

```text
SHIFT.Process1PhysicsManagerControllerOwner/1
SHIFT.Process1Controller1AlertablePacing/1
SHIFT.RetailOuterUpdateCadence/1
```

and checks that the native `RetailOuterSchedulerContract` uses the retail
scheduler authority from the S5 cadence evidence rather than the Controller #1
polling delay or the host-development 1/60 clock.

## Identity join

The contracts agree on the same lifecycle path:

```text
Controller #1
  -> worker FUN_00662880
  -> manager list
  -> Physics Manager scheduler FUN_00647ef0
  -> default manager slot +0x18
  -> FUN_00711b50
  -> downstream recovered physics path
```

The Physics Manager vtable identity is `0x00b04524` in both the Process 1 owner
evidence and the S5 cadence evidence.

## Timing-domain separation

The Controller #1 pacing proof establishes only:

```text
SleepEx(10, TRUE)
```

as an alertable requested timeout between worker-loop iterations. It does not
establish an exact 100 Hz clock.

The authoritative retail outer cadence remains the pre-existing S5 contract:

```text
nominal manager frequency       30 Hz
quantized manager gate          33 ms
normal accumulator contribution 0.03333333507180214 s
steady default dispatch count   1
scheduler authority             RetailEvidence
```

Those values are not re-derived here. They are consumed from
`SHIFT.RetailOuterUpdateCadence/1`.

The host runtime's development clock is also a separate domain:

```text
host-development tick = 1/60 s
```

`runtime_loop_policy.hpp` explicitly rejects using host 1/60 pacing as retail
scheduler/cadence authority.

Therefore the supported relation is:

```text
Controller #1 alertable polling
    -> reaches the Physics Manager owner/scheduler path

Physics Manager scheduler
    -> is governed by existing SHIFT.RetailOuterUpdateCadence/1 evidence

render/presentation cadence
    -> still not joined
```

The following substitutions remain forbidden:

- 10 ms polling timeout = exact 100 Hz;
- Controller #1 polling frequency = Physics Manager 30 Hz;
- host 1/60 development pacing = retail cadence;
- Physics Manager 30 Hz = rendered-frame cadence;
- one physics update = one rendered frame.

## Why this Process 1 join matters

Before this join, Process 1 had recovered the lifecycle owner and worker pacing,
while S5 separately carried the admitted retail cadence. The shared object and
function identities now make the handoff explicit without duplicating S5
machine evidence or weakening either contract's fail-closed limits.

## Next Process 1 blocker

Trace the producer/consumer surface that can affect Controller #1's alertable
wait or queued messages, then determine whether any proven render/presentation
path reaches that surface.

Until such a path is demonstrated, render phase-locking remains unproven.
