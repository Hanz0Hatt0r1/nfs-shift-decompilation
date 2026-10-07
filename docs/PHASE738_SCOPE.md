# Phase 738 scope

In scope:

- prove the `FUN_007618f0` source object from PC source allocation/callsite continuity rather than offset-name inference;
- prove `HDVehicle+0x66b4` owns the allocated `VehicleLoadData` pointer and is passed as `FUN_007618f0 param_2`;
- corroborate the two-explicit-argument thiscall ABI with exact PC machine code;
- correct the targeted Ghidra provenance tool to model right-to-left `param_2`, `param_1` pushes rather than treating the nearest push as the source object;
- join `VehicleLoadData+0x338` to `FUN_007bfbe0` and preserve the exact f32-input/x87/f64-store precision sequence;
- extract the exact BMW M3 E36 CDF from the retail BFF and freeze `CGHeight=0.280` plus `FWCenter=(0.00,-0.100,-0.50)`;
- expose the selected source values through `SHIFT.Fun007618f0SelectedBMWSource/1`;
- retain Phase737 wheel BODY origins and Phase728/727 arithmetic unchanged.

Out of scope:

- inferring VehicleLoadData identity from `+0x338/+0x918` shape alone;
- using the VehicleLoadData constructor's zero defaults in place of the actual BMW `FWCenter` property;
- rounding the retail `CGHeight * scale` product back through f32 after the multiplication;
- wiring the complete Phase737 -> Phase728 -> Phase727 world-position chain into the selected per-pass `FUN_00765c40` provider;
- internalizing collision-provider behavior or residual `FUN_00765c40` side effects;
- reducing the seven-provider frontier before that composed runtime join is source-backed and regression-tested.
