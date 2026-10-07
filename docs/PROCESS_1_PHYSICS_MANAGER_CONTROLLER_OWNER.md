# Process 1 — Physics Manager controller/scheduler owner

This slice closes the lifecycle/scheduling-owner blocker immediately above the
already proven Process 1 path ending at `FUN_00713050`.

The authority is the pinned PC retail 1.02 executable plus the matching full
Ghidra decompile. The Xbox 360 recompilation tree was inventoried on Google
Drive but is not required for this promotion.

## Pinned PC inputs

```text
SHIFT.exe MD5    705af8b420e5eb1e3834ac43d5533c6b
SHIFT.exe SHA256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
SHIFT.exe.c SHA256
                 512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

## 1. The object is explicitly named `Physics Manager`

`FUN_0070fae0` constructs the singleton object later returned through
`FUN_0070fe90/FUN_0070fe99`. The constructor installs vtable `0x00b04524` and
registers the exact text `"Physics Manager"`.

The vtable cell at `0x00b0453c` is `0x00711b50`, so the default manager update
slot at offset `+0x18` resolves exactly to `FUN_00711b50`.

This is a stronger identity than an inferred semantic name: the retail binary
contains the manager name itself.

## 2. Startup attaches Physics Manager to `Controller #1`

The startup routine represented by `thunk_FUN_00d36000` uses the literal
`"Controller #1"` with `FUN_006339b0`, stores the resulting controller handle at
the parent object's `+0x12b0`, obtains Physics Manager through `FUN_0070fe90`,
and passes both identities to `FUN_006485b0`.

`FUN_006485b0` resolves the controller, inserts the manager through
`FUN_00662600`, and records the owning controller at manager offset `+0x14c`.

Therefore Process 1 no longer has an anonymous lifecycle owner above the Physics
Manager update path: the retail setup explicitly assigns it to `Controller #1`.

## 3. Physics Manager is configured for auto update

`FUN_0040e630` obtains Physics Manager and calls:

```text
FUN_00648890(PhysicsManager, 1, 6, 0)
```

`FUN_00648890` writes:

```text
manager+0x34  = 1
manager+0x35  = param2 = 1
manager+0x158 = param3 = 6
manager+0x15c = param4 = 0
```

The manager diagnostic path labels `manager+0x34 != 0` as `"Auto Update"`.

The numeric value `6` is retained only as a recovered configuration value. This
slice does **not** call it 6 Hz or otherwise assign frequency semantics to it.

## 4. Controller worker reaches the manager scheduler

Controller vtable `0x00af0568` has `FUN_00662880` at slot `+0x4`.
`FUN_00649b10`, the controller thread/fiber entry path, invokes that slot.

Inside `FUN_00662880`, after message processing, the worker calls
`FUN_006626a0`. When controller state `+0x98 == 6`, `FUN_006626a0` passes the
controller manager-list at `+0x58` to `FUN_0065b8b0`.

`FUN_0065b8b0` walks that list. For eligible managers it calls
`FUN_00647ef0(manager)`.

Because startup already proved that Physics Manager is a member of the
`Controller #1` list, this is the exact framework path that schedules it.

## 5. Generic manager dispatch resolves to `FUN_00711b50`

`FUN_00647ef0` is not a trivial one-shot wrapper. It maintains manager timing
state and has paths that may call `FUN_00647d80` repeatedly.

`FUN_00647d80` dispatches:

```text
[vptr + 0x18]   normally
[vptr + 0x1c]   when the separate framework flag at FUN_0065bf80()+0x529 is set
```

For Physics Manager, vtable `+0x18` is `FUN_00711b50`.

The previously recovered downstream chain then continues:

```text
FUN_00711b50
  -> FUN_007119c0
  -> FUN_007117e0
  -> FUN_0070f940
  -> FUN_007155e0
  -> FUN_0048ed52
  -> FUN_007155e9 (case 3)
  -> FUN_00715380
  -> FUN_00713050
```

From `FUN_00713050`, `SHIFT.Process1Fun0079b2d0VirtualDispatch/1` already proves
the queue/fiber path through `FUN_0079b2d0` to `FUN_00770e80`.

## Promoted owner path

```text
startup
  -> "Controller #1"
  -> attach Physics Manager
  -> Controller #1 worker
  -> FUN_006626a0
  -> FUN_0065b8b0(controller+0x58)
  -> FUN_00647ef0(Physics Manager)
  -> FUN_00647d80
  -> Physics Manager vtable +0x18
  -> FUN_00711b50
  -> ...
  -> FUN_00713050
  -> previously proven queue/fiber virtual dispatch
  -> FUN_0079b2d0
  -> FUN_00770e80
```

## What is not promoted

This closure deliberately does **not** claim:

- one Physics Manager update per rendered frame;
- that `Controller #1` wakes once per rendered frame;
- an exact external controller wake frequency;
- that configuration value `6` is a frequency;
- equivalence between controller-worker execution, manager scheduler dispatch,
  and presentation/render cadence.

In fact, `FUN_00647ef0` contains accumulator/timing behavior and can issue
multiple manager dispatches in a single invocation. That is a reason to keep
render cadence separate, not a reason to infer it.

## Next Process 1 blocker

The next bounded question is the external wake/synchronization cadence of
`Controller #1`: what releases or wakes its worker, and whether that event has
any proven relation to rendered frames.

Until that join is proved, Process 1 should keep the controller/manager timing
lane independent from render-frame cadence.
