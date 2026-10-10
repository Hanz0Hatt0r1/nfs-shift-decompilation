# Process 1B — HDVehicle+0x4330 external caller tranche 1

This P1.3B slice closes the first two caller functions from
`SHIFT.P1B.HDVehicle4330IncomingDirectCallFrontier/1` by exact retail-machine
argument provenance. Direct callgraph reachability is navigation only.

## FUN_00491d86 wrapper chain

`FUN_00491d86` is not an independent producer. The retail path is:

`FUN_00768a30 -> FUN_00491d86 -> FUN_00768a4d`

Both wrappers preserve `ECX`. The direct entry surface of `FUN_00768a30` is
exactly three sites in the pinned SQLite index:

- `0x0070275c`: `FUN_00702720` loads `ECX = 0x00c13700`;
- `0x007027be`: `FUN_00702770` loads `ECX = 0x00c13700`;
- `0x0076e544`: already-admitted `FUN_0076df50` exact-root path.

Therefore this chain receives the HDVehicle root and reaches the already-proven
`FUN_00768a4d` `+0x4330` materializer. It does not forward a pre-existing
`HDVehicle+0x4330` pointer into the carrier.

## FUN_00798df0 five-call cluster

All five exact-carrier calls are pinned in retail bytes.

- `0x00798f5c -> FUN_00772200`: `ECX = EBP-0x238c`, a stack local.
- `0x00798f9c -> FUN_0076df50`: `ECX = 0x00c13700`, the exact HDVehicle root.
- `0x00798fce -> FUN_007c3b00`: the parameter position that carries
  `HDVehicle+0x4330` on the proven root-derived call is stack `param3`; here it
  is `EBP-0x238c`.
- `0x00798fff -> FUN_007c3b00`: same stack-local `param3`.
- `0x00799054 -> FUN_007c3b00`: same stack-local `param3`.

The root-derived reference call at `0x0076e1d0` is pinned as the comparison
shape: it materializes `LEA EBX,[ESI+0x4330]` and pushes that exact alias in the
same `param3` position.

## Result

This closes 2 of the 7 external caller functions and 6 of the 11 external
callsites from the incoming frontier. No pre-existing `HDVehicle+0x4330` alias
is found in this tranche.

The remaining direct callers are:

- `FUN_0074da70`
- `FUN_00795d60`
- `FUN_00aa2850`
- `Unwind@00a7063f`
- `Unwind@00a72322`

Global runtime-derived alias exhaustion, indirect entry, the
`manager+0x374 -> HDVehicle+0x4330` join, final `0x004b86cf`, aggregate P1.3,
and provider removal remain fail-closed. Provider count remains 7.

Run:

```bash
python3 tools/ghidra/verify_p1b_hdvehicle_4330_external_caller_tranche1.py \
  SHIFT.exe shift_ghidra.sqlite \
  --output out/p1b_hdvehicle_4330_external_caller_tranche1.json
```
