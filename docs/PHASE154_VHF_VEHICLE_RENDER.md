# Phase 154: VHF-driven whole vehicle geometry render

Phase 154 turns the first real MEB render into a real vehicle assembly.

The integration path is:

    BFF -> VHF XML -> VHF matrix hierarchy
       -> selected LODA MEB nodes -> world-space neutral mesh
       -> desktop reference rasterizer -> PPM

## Selection

The default kit00 profile includes:

- KIT00 body/chassis/interior/hood/trunk/bumpers/lights/steering-wheel nodes;
- shared wheel/tire/disc/caliper/mirror/lightglow LODA nodes.

It excludes _damage resources and alternative KIT01/KIT02/KIT04 body kits.

--profile all is available for diagnostic comparisons and intentionally makes
fewer selection assumptions.

## CLI

    python bff_vehicle_render.py \\
      BMW_M3_E36.bff \\
      vehicles/bmw_m3_e36/bmw_m3_e36.vhf \\
      out/bmw_m3_e36_kit00_vehicle.ppm \\
      --mesh-json out/bmw_m3_e36_kit00_vehicle.mesh.json

The camera uses a deterministic yaw/pitch pre-transform followed by the existing
reference_renderer.orthographic_mvp.

## Evidence and scope

Every included MEB records its exact archive entry index, decoded SHA-256,
primitive/material references and resolved VHF world matrix.

The resulting raster is deliberately geometry-only flat gray. This phase proves
scene assembly and transform application, not BMW paint shading.

It does not claim:

- final BMT/FX/FXO material execution;
- exact COLOR0/COLOR1 byte order as a renderer ABI;
- original game camera/post-processing;
- runtime D3D9 instance correlation.

The supplied BMW BFF has the real bmw_m3_e36.vhf, bmw_m3_e36_paint.bmt and many
cached .fxo permutations. The paint material references render/shaders/bodywork.fx,
so a full paint render still needs the corresponding render/shader source payload.
