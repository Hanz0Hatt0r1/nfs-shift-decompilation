# Phase 728 next blocker

Phase 728 proves and implements the exact source core that produces `HDVehicle+0x3938` from exact-offset inputs. Together with Phase 727, the arithmetic from those inputs through to the `FUN_007b0710` world position is now source-backed and native-ready.

## NEXT_STEP

The remaining runtime join is ownership/timing, not arithmetic:

1. Trace ownership and refresh timing of the pointer targets stored at `HDVehicle+0x820` and `HDVehicle+0x12a0`.
2. Trace ownership of the second `FUN_007618f0` source argument carrying `f64 +0x338` and `f64 vec3 +0x918` without assigning unsupported semantic names.
3. Expose the current chassis BODY0 bytes to the `FUN_00765c40` anchor for each recovered pass. Pass 1 must see the BODY state after the first half-step.

Only after those joins are proven should the active `Fun00765c40ExternalPassResult` stop accepting an externally supplied `world_position` and instead build it from native Phase 728 + Phase 727 source cores.

The collision provider remains a separate external blocker. Keep the active provider count at seven until the runtime join is complete.
