# Phase 732 next blocker

Phase 732 internalizes the already-native `FUN_00759210` surface-probe arithmetic inside the production `FUN_007675f0` path. Current BODY0 provides the query point; the probe returns the point/scalar used to derive `planar_delta` and `surface_scalar`.

The remaining node itself is source-visible at `HDVehicle+0x120`. PC `FUN_0076d100` loads that pointer before calling `FUN_007675f0`. When its stale/null path fires, the retail function calls `FUN_00717cd0` and writes the returned pointer back to `HDVehicle+0x120`, then snapshots current BODY origin to `+0x128/+0x130/+0x138`.

The next precise Process 2 blocker is therefore the `FUN_00717cd0` / `HDVehicle+0x120` refresh-provider contract:

1. recover the exact input/context and returned-node contract of `FUN_00717cd0`;
2. prove the source-visible stale/refresh condition around `+0x120` and `+0x128/+0x130/+0x138`;
3. determine whether the selected native session already owns the required provider/context;
4. only then replace the external `SurfaceProbeNode*` input with native persistent node ownership.

Do not infer a node class name, track/surface manager type, physical units, or scene-query semantics from Xbox-only evidence. If `FUN_00717cd0` cannot yet be implemented, narrow the provider boundary rather than inventing it.
