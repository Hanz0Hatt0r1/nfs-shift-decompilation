# Process 1 — P1.3 absolute writer frontier

After rejecting `FUN_00791020`, the remaining P1.3 producer search is constrained to the exact selected-HDVehicle absolute fields consumed by the wheel path:

```text
HDVehicle+0x938
HDVehicle+0x13b8
HDVehicle+0x1e38
HDVehicle+0x28b8
```

A candidate is admissible only when its receiver/base is independently proven to alias selected `HDVehicle`. Matching a raw `+0x538` or `+0x938` literal on another object is insufficient.

The upstream value-transfer chain remains open and no throttle/brake/steering/gear semantics are assigned.

Provider count remains 7.
