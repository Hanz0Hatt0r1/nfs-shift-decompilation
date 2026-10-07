# Phase 738 next blocker

Phase 738 closes the last unresolved inputs of the Phase 728 `FUN_007618f0` local-sample formula for the selected Silverstone + BMW M3 E36 session:

- Phase737 supplies current FL/FR wheel BODY origins from persistent BODY3/BODY4;
- `FUN_007618f0 param_2` is proven as `VehicleLoadData*` from `HDVehicle+0x66b4`;
- selected `VehicleLoadData+0x338` is frozen with exact f64 bits `0x3fc5810634bc6a80` from the PC f32-input/x87/direct-f64-store path;
- selected `VehicleLoadData+0x918/+0x920/+0x928` is exact BMW CDF `FWCenter=(0.00,-0.100,-0.50)`.

The next precise Process 2 slice is the composed per-pass world-position join:

1. observe the current persistent BODY array at the `FUN_00765c40` anchor for each recovered pass;
2. derive the Phase737 wheel-origin inputs from BODY3/BODY4 at that exact point;
3. combine them with `SHIFT.Fun007618f0SelectedBMWSource/1` through the existing Phase728 local-sample producer;
4. transform that local sample through the existing Phase727 current BODY0 origin/basis transform;
5. compare/store the resulting world position as the typed `Fun00765c40QueryInputBoundary.world_position` consumed by native `FUN_007b0710` query-record materialization;
6. prove pass 1 observes the BODY records after the first `FUN_00765470` half-step rather than the outer-step snapshot;
7. leave collision-provider implementation and any other residual `FUN_00765c40` side effects external unless separately source-backed.

Phase738 itself keeps the active top-level external-provider count at seven. A provider-count reduction is allowed only if the composed Phase739 join proves that no remaining work requires the existing complete `FUN_00765c40` provider boundary.
