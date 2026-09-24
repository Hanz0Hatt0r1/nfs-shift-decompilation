# Phase 157: real BMW MEB + DDS texture preview

Phase 157 adds a renderer adapter for the real BMW M3 body MEB and the real COMMON_PAINT.dds from the same BFF.

Pipeline:

    BFF -> MEB -> UV0 (property 130) + DDS -> reference_renderer

CLI:

    python bff_meb_texture_render.py \\
      BMW_M3_E36.bff \\
      out/bmw_m3_e36_common_paint.ppm \\
      --primitive-index 1

The default resources are `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb` and `vehicles/textures/common_paint.dds`. The texture sampler uses the material contract's linear filtering and wrap addressing.

This phase intentionally does not execute the BMW paint shader. The supplied `COMMON_PAINT.dds` decodes to a uniform `(115, 115, 115)` base level; actual visible paint color therefore remains a shader/material-constant responsibility.

The adapter records decoded resource identities, DDS format/dimensions and deterministic PPM SHA-256.
