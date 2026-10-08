# Process 1B — reject `manager+0x2a0` entry identity with `HDVehicle+0x4330`

## Blocker

The merged selection/population proof established a complete structural path:

```text
manager+0x2a0 population
  -> selected 0x22e0 collection entry
  -> thunk_FUN_00d60660
  -> manager+0x374
```

The remaining question was whether that selected entry pointer is exactly the already-proven selected `HDVehicle+0x4330` record.

## Manager collection element extent

`SHIFT.HDVehicle64e8Manager2a0PopulationProducerProof/1` establishes that the exact manager collection is configured with element size/stride `0x22e0` and alignment `0x20`. The append path obtains backing storage by element index and initializes each element through `FUN_00481a10`.

In source-order form:

```text
FUN_0062ffd0(collection, 0, 0x22e0, 0x20, 0x1f, 1)
...
entry = backing_store + index * 0x22e0
FUN_00481a10(entry)
```

Thus the pointer returned by `FUN_0054ed00(manager+0x2a0,index)` denotes one exact `0x22e0` collection element.

## Selected HDVehicle record requires a larger receiver-relative extent

The selected record ownership is independently machine-proven:

```text
0x0076b241  ECX = HDVehicle+0x4330
0x0076b247  call FUN_00772200
```

The PC-retail decompiler source for that constructor contains receiver-relative dword writes through:

```text
record+0x2350
record+0x2354
record+0x2358
record+0x235c
record+0x2360
```

The last dword store requires valid selected-record storage through `record+0x2363`, i.e. a minimum constructor extent of `0x2364`.

## Exact contradiction

```text
manager collection entry extent   = 0x22e0
selected record minimum extent     = 0x2364
excess required by selected record = 0x0084
```

If the pointers were identical, `FUN_00772200`'s store at `+0x2360` would land `0x80` bytes past the end of the selected `0x22e0` collection element. In a fixed-stride collection that address belongs outside the element being selected. Therefore the exact pointer identity is rejected:

```text
manager+0x2a0[index] != HDVehicle+0x4330
manager+0x374         != HDVehicle+0x4330
```

This is a layout contradiction, not an inference from names or similar offsets.

As independent corroboration only, the selected HDVehicle owns `VehicleLoadData*` at `HDVehicle+0x66b4`, which is `record+0x2384`, also beyond the `0x22e0` manager-entry stride. The primary rejection does not depend on that root-owned field.

## Consequence for `HDVehicle+0x64e8`

The manager-domain literal stores of values `1/2/3/4` previously remained candidates only if `manager+0x374` or a `manager+0x2a0` entry could be joined to `HDVehicle+0x4330`. That identity route is now rejected. Those manager-domain stores must not be promoted as the selected `HDVehicle+0x64e8` non-sentinel writer.

The selected-record writer remains open through other alias/callee/computed paths. Retail input/control provenance remains incomplete and the external provider count remains 7.

## Next step

Stop pursuing selected-HDVehicle pointer identity through manager `+0x374/+0x2a0`. Search exact post-construction writers of `HDVehicle+0x64e8` directly, including address-taken aliases and callee side effects. Keep the manager collection as a separate vehicle-loading/session domain unless a later exact value-transfer bridge is proven.
