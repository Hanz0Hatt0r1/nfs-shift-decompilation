# Phase 155: external BMW shader-source boundary

The retail BMW archive contains the real M3 BMT, MEB, cached FXO permutations and DDS dependency paths, while the canonical material shader reference points at render/shaders/bodywork.fx. The render archive can therefore be supplied as a separate shader-source file without weakening the BFF-backed material evidence.

## CLI

    python bmw_material_external_fx.py \\
      BMW_M3_E36.bff \\
      bodywork.fx \\
      out/bmw_m3_e36_material.json \\
      --supplemental-bff BMW_M3_E36_Cockpit.bff

The external file must have the same basename as the material shader reference. Its byte SHA-256 and size are stored under provenance.shader_source with kind=external-file.

All other sources remain BFF-backed:

- BMW_M3_E36_PAINT.bmt;
- BMW_M3_E36_KIT00_BODY_LODA.meb;
- FXO cache candidates;
- DDS dependency path inventory.

The adapter does not select a shader permutation automatically beyond the existing evidence-ranked material_linker and BMW paint gates. It does not commit proprietary shader bytes.
