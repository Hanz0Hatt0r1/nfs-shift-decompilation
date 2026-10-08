# Process 1D — retail physics -> mode-2 camera update ordering

## Result

Phase 651 request 4 is closed positively for the recovered default/steady cPhysicsManager path: the retail physics scheduler executes before the registered camera callback, and the mode-2 source per-frame update is downstream of that callback.

## Callback ownership

`FUN_0048a7f0` obtains the source-backed cPhysicsManager through `FUN_0070fe90()` and installs:

```text
0x0048a800  call FUN_0070fe90
0x0048a80d  mov [eax+0x298], 0x00489f70
```

Therefore:

```text
cPhysicsManager+0x298 = FUN_00489f70
```

This is exact callback ownership, not callgraph adjacency.

## Scheduler-before-callback order

The admitted cPhysicsManager vtable scheduler slot is:

```text
vtable+0x18 -> FUN_00711b50
```

The exact chain is:

```text
FUN_00711b50
  -> FUN_007119c0
    -> FUN_007117e0
```

Inside `FUN_007117e0` the relevant instructions are ordered on the same path:

```text
0x0071196b call FUN_0070f940   ; physics scheduler work
...
0x007119a7 call FUN_0070f890   ; callback dispatcher
```

`FUN_0070f940` performs the admitted scheduler call. On the ordinary/default path (`DAT_00c104a4 == 0`) it executes:

```text
0x0070f9af call FUN_007155e0
```

The previously merged retail cadence proof connects `FUN_007155e0` to the recovered scheduler chain and inner physics execution (`FUN_00715380 -> FUN_00713050`).

Only after `FUN_0070f940` returns does `FUN_007117e0` invoke `FUN_0070f890`.

## Callback -> camera update chain

`FUN_0070f890` reads `cPhysicsManager+0x298` and calls it indirectly at:

```text
0x0070f897  mov edi,[esi+0x298]
...
0x0070f90c  call edi
```

The registered target is `FUN_00489f70`.

`FUN_00489f70` performs the camera frame path:

```text
FUN_00489f70
  -> FUN_0080bfb0
  -> FUN_0080b820
  -> FUN_0080ec80
```

Within `FUN_0080ec80`, the active source at `CameraManager+0x2568` is updated through vtable `+0x60`:

```text
0x0080f220  mov ecx,[esi+0x2568]
0x0080f22d  mov eax,[edx+0x60]
0x0080f23a  call eax
```

For the proven mode-2 source vtable `0x00b16788`, `+0x60` resolves to `FUN_008216a0`.

Thus the bounded retail order is:

```text
cPhysicsManager default outer dispatch
  -> FUN_0070f940
  -> FUN_007155e0
  -> recovered inner physics execution
  -> return
  -> FUN_0070f890
  -> cPhysicsManager+0x298 = FUN_00489f70
  -> CameraManager update
  -> active mode-2 source vtable+0x60 = FUN_008216a0
```

## Freshness consequence

For a normal admitted cPhysicsManager dispatch, the mode-2 source update consumes state after the scheduler/physics work of that same dispatch. This proves the retail **physics-before-camera** ordering relation required by Phase 651 request 4.

It does not by itself prove which `manager+0x2a0[target_id]` entry is the selected BMW/player vehicle; that identity remains the separate P1.3.manager2a0 dependency of request 3.

## Gates

Positive:

- cPhysicsManager callback owner `+0x298 = FUN_00489f70`: proven;
- physics scheduler call precedes callback dispatch: proven;
- callback reaches CameraManager frame update: proven;
- active mode-2 source per-frame update uses vtable `+0x60 = FUN_008216a0`: proven;
- Phase 651 request 4 retail update ordering/freshness relation: **ready** for the admitted default/steady path.

Still blocked:

- Phase 651 request 3 exact selected BMW/BODY0 target identity;
- native camera-follow admission until request 3 and current retail world-matrix gates are positive.

External provider count remains **7**.
