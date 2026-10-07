# Process 1 — `Controller #1` thread start and alertable pacing

This slice continues from `SHIFT.Process1PhysicsManagerControllerOwner/1` and
closes the next lifecycle question: how `Controller #1` begins executing its
worker and how that worker self-paces between iterations.

Authority remains the pinned PC retail 1.02 executable and matching full Ghidra
decompile. Xbox 360 recompilation output is not required for this promotion.

## Pinned PC inputs

```text
SHIFT.exe MD5    705af8b420e5eb1e3834ac43d5533c6b
SHIFT.exe SHA256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
SHIFT.exe.c SHA256
                 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

## 1. Controller creation installs `FUN_00649b10` as the thread entry

`FUN_006339b0` reaches `FUN_0065b750` when it needs the named controller.
`FUN_0065b750` names the object and calls `FUN_00649cb0` to create the worker
thread object.

The `_beginthreadex` setup in `FUN_00649cb0` packs:

```text
entry    = FUN_00649b10
argument = controller thread object
initflag = 4
```

The proof records the numeric initialization flag exactly. The lifecycle claim
does not depend on assigning extra scheduler semantics to that numeric flag,
because the same PC path later proves an explicit `ResumeThread`.

## 2. Startup resumes `Controller #1` only after manager attachment

The startup routine that previously proved the `Controller #1` → Physics Manager
attachment later calls `FUN_00649e20` for that controller.

`FUN_00649e20` dispatches controller vtable slot `+0x10`. For the recovered
controller vtable `0x00af0568`, cell `0x00af0578` contains `FUN_00655040`.

`FUN_00655040` forwards to `FUN_006496f0`, which updates thread bookkeeping and
calls the OS `ResumeThread` API on the stored thread handle.

Therefore the bounded lifecycle is:

```text
create controller worker
  -> create thread with entry FUN_00649b10 and initflag 4
  -> attach Controller #1 managers
  -> FUN_00649e20
  -> controller vtable +0x10
  -> FUN_00655040
  -> FUN_006496f0
  -> ResumeThread
```

This closes the former uncertainty about whether the manager-owning controller
worker merely existed or was explicitly started by the same startup sequence.

## 3. The worker does not wait on a render-frame event

Inside `FUN_00662880`, the loop begins with `FUN_00655190`. That helper refreshes
thread priority through the existing thread-priority path; it is not a blocking
wait.

`FUN_00655130`, used as another loop condition/probe, reads a thread-state flag;
it is also not a blocking wait.

After message handling and manager dispatch, the worker executes:

```text
FUN_00649780(10, 1)
```

`FUN_00649780` is a thin wrapper around:

```text
SleepEx(10, TRUE)
```

The worker then rechecks its stop byte and loops.

This is the first exact PC-static pacing mechanism recovered above the
`Controller #1` manager list: an alertable sleep request for 10 milliseconds
between worker-loop iterations.

## 4. What this does not mean

This evidence does **not** promote the worker to an exact 100 Hz clock.
`SleepEx(10, TRUE)` proves the requested timeout and alertable mode; it does not
prove exact elapsed wall-clock time for every iteration. OS scheduling latency
can extend the delay, while alertable completion mechanisms can change how the
sleep returns.

It also does **not** prove:

- one worker iteration per rendered frame;
- one Physics Manager update per worker iteration;
- an exact 100 Hz Physics Manager cadence;
- any render/present synchronization event;
- that `Controller #1` polling cadence replaces the independent timing and
  accumulator behavior already recovered inside `FUN_00647ef0`.

The previous Process 1 contract remains important here: `FUN_00647ef0` owns a
separate manager-local scheduling policy and may issue multiple manager
virtual-update dispatches during one call.

## Promoted lifecycle/pacing path

```text
FUN_006339b0("Controller #1")
  -> FUN_0065b750
  -> FUN_00649cb0
  -> _beginthreadex(entry=FUN_00649b10, initflag=4)
  -> startup attaches Controller #1 managers
  -> FUN_00649e20
  -> controller vtable +0x10 = FUN_00655040
  -> FUN_006496f0
  -> ResumeThread
  -> FUN_00649b10
  -> controller vtable +0x4 = FUN_00662880
  -> manager work / SHIFT.Process1PhysicsManagerControllerOwner/1
  -> FUN_00649780(10, 1)
  -> SleepEx(10, TRUE)
  -> loop
```

## Next Process 1 blocker

The next bounded target is no longer the controller wake mechanism. It is the
Physics Manager timing configuration consumed by `FUN_00647ef0`: recover which
manager-local fields establish its accumulator/frequency policy and prove how
that policy maps controller polling to manager update dispatches.

Until that is recovered, Process 1 must keep the 10 ms controller sleep request
separate from any claimed physics frequency.
