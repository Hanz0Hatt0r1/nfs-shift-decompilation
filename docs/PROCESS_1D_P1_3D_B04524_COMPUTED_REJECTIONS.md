# Process 1D — P1.3D `0x00b04524` computed `+0x374` receiver closure

## Result

P1.3D owns the two residual computed forwarding paths at `0x0070fb45` and `0x0070fdeb`.

Both occur in `FUN_0070fae0`. Machine transfer captures entry `ECX` in `ESI` at `0x0070fafd`, then installs exact vptr `0x00b04524` at `0x0070fb13` before either computed `ESI+0x374` materializer executes.

Participants Manager uses root vptr `0x00ab9190` and embedded `+0x20` vptr `0x00ab916c`. The exact same-receiver continuity therefore rejects both P1.3D paths as Participants Manager `+0x374` candidates:

```text
0x0070fb45 -> FUN_00533e70
0x0070fdeb -> FUN_006329e0
```

No conclusion is drawn from the shared numeric offset itself.

## Shard boundary

This closure is intentionally limited to the two sites assigned to **P1.3D**. `0x0070f62d` belongs to **P1.3B** even though its destructor receiver belongs to the same `0x00b04524` class, so this handoff does not adjudicate that site.

After the P1.3D handoff, the aggregate computed-forwarding frontier is reduced from six to four sites pending integration:

```text
0x005292db
0x005f4ffa
0x005f6eda
0x0070f62d
```

## Gate

```text
P1.3D assigned computed sites complete = true
P1.3D computed handoff ready           = true
manager+0x374 -> HDVehicle+0x4330      = false
final 0x004b86cf adjudicated           = false
P1.3 complete                          = false
provider count                         = 7
```

## Remaining P1.3D work

- recover exact selected-root alias/callee/bulk-copy writer provenance for `HDVehicle+0x28b8`;
- close Controller #1 indirect/native APC injection timing for the alertable-worker producer chain;
- return the completed P1.3D shard contract to Process 1B for aggregate P1.3 integration.
