# Phase 156: real BMW material slice with external FX source

Phase 156 connects the external bodywork.fx boundary to the existing real BMW material-slice builder.

The resulting path is:

    BMW_M3_E36.bff
      -> real BMT + MEB + FXO + DDS evidence
      -> external bodywork.fx
      -> BMT/FX/FXO linker
      -> StaticDraw/1
      -> RenderCommand/1

CLI:

    python bmw_real_material_slice_external_fx.py \\
      BMW_M3_E36.bff \\
      evidence/bmw_m3_e36_kit00_body_loda.golden.json \\
      bodywork.fx \\
      out/bmw_m3_e36_material_slice.json \\
      --primitive-index 1 \\
      --supplemental-bff BMW_M3_E36_Cockpit.bff

The external FX basename must match the BMT shader reference. Its SHA-256 and size are preserved in material provenance.

This phase does not invent environment-map/shadow resources, resolve the COLOR0/COLOR1 runtime declaration question, or claim a final BMW paint image. bmw_reference_render.py remains the rendering boundary once the material slice is ready.
