# Process 1A / P1.3A — `FUN_00a62f60` direct queue-registration frontier

## Result

A whole-image retail disassembly contains exactly **four direct calls** to `FUN_00a62f60`, the queue registration routine proven to allocate a node and persist its EDX task pointer at node `+0`.

```text
0x0067b69e  FUN_0067b660
0x00713122  FUN_00713050
0x007131cc  FUN_00713050
0x0076e4ff  FUN_0076df50
```

The final call is the merged positive wheel path: `FUN_0076df50` passes the exact `HDVehicle+0x400+slot*0xa80` wheel root, including selected slot0 and slot1 roots.

The two `FUN_00713050` calls are independently closed by `SHIFT.Process1Fun0079b2d0VirtualDispatch/1`. They register the proven parent subobject at `+0x340`, whose object identity and queue continuity are already machine-pinned. They are not wheel roots.

That leaves exactly one direct-source provenance blocker: `FUN_0067b660`.

## `FUN_0067b660` callback frontier

The function receives `param_1`, iterates source records as:

```text
source = param_1 + 0x130 + index*0x30
queue  = param_1 + 0x2b0
```

and sends each source to `FUN_00a62f60`.

There are **zero direct call/jump transfers** to `FUN_0067b660` in the retail executable. Its absolute VA occurs exactly once on disk, at `.rdata` VA `0x00af7548`. That cell sits immediately after the static string:

```text
AnimationProcessor::mStartEvent
```

inside a compact function-pointer table.

This is positive static-callback evidence, but the callback invocation ABI and `param_1` object identity are not yet proven. Therefore this source cannot yet be declared non-wheel or selected-wheel-derived.

## Gate effect

Promoted only:

- `p13a_fun00a62f60_direct_registration_surface_complete = true`.

The four direct registrations classify as:

- 1 proven selected-wheel source;
- 2 proven distinct task-subobject sources;
- 1 unresolved callback source.

`fun0067b660_static_callback_pointer_found = true`, while `fun0067b660_callback_argument_provenance_complete = false`.

Global callback/incoming-indirect, runtime-generated selected-wheel pointer, stored-alias, slot0, slot1 and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

## Next step

Recover the static table dispatcher that invokes `FUN_0067b660`, including the callback calling convention and `param_1` object provenance. That is now the only unresolved source among direct `FUN_00a62f60` registrations.
