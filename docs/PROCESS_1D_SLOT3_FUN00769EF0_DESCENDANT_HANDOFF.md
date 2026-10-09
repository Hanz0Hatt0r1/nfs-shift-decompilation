# Process 1D — `FUN_00769ef0` slot3 descendant handoff

This P1.3D slice consumes three already merged PC-retail contracts and closes only their explicitly proven exact-receiver descendant destinations.

The recovered pass-tail chain is:

```text
0x0076d2c1  FUN_0076d100 -> FUN_00769ef0   ECX = HDVehicle
0x0076a1c7  FUN_00769ef0 -> FUN_007675f0
0x0076a1e8  FUN_00769ef0 -> FUN_007682c0
```

`SHIFT.Fun007675f0SurfaceProbeNodeCache/1` and `SHIFT.Fun007675f0DistanceStateOwnership/1` pin the known persistent HDVehicle state in the `FUN_007675f0` branch to:

```text
HDVehicle+0x120
HDVehicle+0x128
HDVehicle+0x130
HDVehicle+0x138
HDVehicle+0x4080
```

Those qword lanes are disjoint from selected slot3 `HDVehicle+0x28b8..+0x28bf`.

`SHIFT.Fun007682c0Body0DeltaDestination/1` independently proves the other branch dereferences `HDVehicle+0x33a0` and writes the selected retail BMW chassis BODY0 record at `BODY0+0x50`. That destination is a separate object and must not be equated with `HDVehicle+0x28b8` by offset coincidence.

Reproduce the handoff:

```bash
python3 tools/ghidra/build_p1d_slot3_fun00769ef0_descendant_handoff.py \
  evidence/fun_007682c0_body0_delta_destination.json \
  evidence/fun_007675f0_surface_probe_node_cache.json \
  evidence/fun_007675f0_distance_state_ownership.json \
  --output out/p1d_slot3_fun00769ef0_descendant_handoff.json
```

## Fail-closed boundary

This closes only the already-proven descendant destinations above. It does **not** claim a complete write surface for `FUN_00769ef0` itself, does not close stored/escaped aliases, and does not close indirect/callback carriers.

The sibling exact-HDVehicle branch `0x0076d193 -> FUN_00758810` remains open and is the next direct target.

Slot3 writer provenance remains false, P1.3D remains false, aggregate P1.3 remains fail-closed, and external provider count remains 7.
