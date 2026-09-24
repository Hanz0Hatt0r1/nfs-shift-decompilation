# Phase 138 — enforce BMW M3 paint contract in render preparation

The documented BMW M3 paint contract is now enforced inside the real `compile_material()` path for the exact normalized material reference `vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx`.

For that material, the pipeline validates:

- `bodywork.fx` shader identity;
- `USE_FRESNEL`, `ALLOW_VINYLS`, `DIRT_SCRATCH` specialization flags;
- diffuse/specular/scratch texture names and D3D9 registers s1/s2/s4;
- sampler filter/address/sRGB state;
- renderer-global environment/shadow sampler bindings s3/s0.

The result is stored as `paint_contract` and its blockers are carried into `StaticDraw/1`. This means the exact M3 material cannot reach renderer execution while the documented paint binding is incomplete or drifted.

Non-M3 materials do not activate this contract, preserving the generic renderer path.

## Boundary

This is still a static material contract. It does not prove runtime object/frame attribution and does not choose an FXO permutation; those remain handled by the separate shader identity and runtime gates.

## Next

Run the real M3 `bmw_m3_e36_paint.bmt` through the linker with its actual FXO/texture records and verify that the emitted material passes the contract without fixture substitution.