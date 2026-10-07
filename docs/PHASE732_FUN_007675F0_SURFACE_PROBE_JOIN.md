# Phase 732 — FUN_007675f0 surface-probe join

Phase 732 joins the already-native Phase 661 `FUN_00759210` surface probe into the production `FUN_007675f0` path. This removes two precomputed per-pass values from the session provider: `planar_delta` and `surface_scalar`.

## Exact PC caller mapping

Direct disassembly of the retail `SHIFT.exe` (`sha256 eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`) proves the caller boundary at `0x0076760c..0x0076765d`:

1. `FUN_007675f0` receives a node pointer as its first stack argument;
2. chassis BODY origin `+0x00/+0x08/+0x10` is converted from f64 to three f32 locals;
3. `FUN_00759210` is called at `0x00767643` with the query point, node pointer, output point and output scalar;
4. `0x004a7870` then subtracts the BODY query point from the returned point;
5. the resulting vector feeds the X/Z distance/direction path;
6. the returned scalar feeds the later gap path.

The native implementation preserves the caller's f64-to-f32 BODY-origin spill and f32 result/subtraction boundary rather than silently evaluating the join entirely in host double precision.

## Node ownership remains external

The same PC machine code shows the node passed to `FUN_007675f0` comes from `HDVehicle+0x120` in `FUN_0076d100` (`0x0076a0c9`, call at `0x0076a1c7`). A stale/null path refreshes it by calling `FUN_00717cd0` at `0x0076a09c`, then writes the returned pointer to `HDVehicle+0x120`.

Phase 732 does not name or implement that refresh provider. Production therefore supplies a typed `SurfaceProbeNode*`; the native `FUN_00759210` arithmetic and BODY-relative delta are internal, while node refresh/ownership freshness remains the next evidence target.

## Corrected active gap arithmetic

Direct machine inspection also corrects an older decompiler-level approximation. After `FUN_00783a30`, PC retail stores the filtered value to `HDVehicle+0x4080`, reloads it, and later forms the gap at `0x00767937..0x00767949` as:

```text
filtered_distance_state - (surface_scalar - 1.5)
```

The active native C++ and Python oracle now use that exact formula. Historical Phase 379 evidence is left unchanged as history.

## Production provider frontier

After Phase 732, `ContactOuterSessionInput` has five production fields:

- `surface_probe_node`;
- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`;
- `param_3`.

Historical lower-chain fixtures can still provide a compatibility planar/scalar snapshot. This compatibility path is not evidence that production should externalize those values again.

The number of top-level external provider boundaries remains seven.

## Xbox 360 cross-check

The European Xbox 360 build independently mirrors the same structure: its `FUN_007675f0` counterpart at `0x8259a9f0` calls the surface-probe counterpart at `0x8258ffb8` before constructing the BODY-relative planar path. This is corroboration only; PC retail machine code remains authoritative for the native PC contract.

## Next boundary

The preferred next target is the `FUN_00717cd0` / `HDVehicle+0x120` refresh-provider boundary. It should only be internalized after its provider ownership, freshness rule, and returned-node contract are source-backed. The remaining four scalar inputs are an alternative bounded target.
