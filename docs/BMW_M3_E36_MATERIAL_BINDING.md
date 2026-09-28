# BMW M3 E36 material / shader binding

## Corpus

The two supplied BMW archives contain:

- 2,165 resources;
- 1,707 FXO;
- 75 BMT;
- 147 DDS;
- 206 MEB.

All sampled Type-2 resources decode successfully, and all 206 MEB resources pass the existing MEB→MGEO path.

## Paint material

For `vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt`:

| BMT parameter | FX sampler | D3D9 slot | Resource |
|---|---|---:|---|
| diffuseTexture | diffuseMap | s1 | COMMON_PAINT.dds |
| specularTexture | specularMap | s2 | COMMON_PAINT_SPECULAR.dds |
| scratchControlTexture | scratchControlMap | s4 | COMMON_BLANK.dds |
| environmentMap | environmentMap | s3 | external cube |
| shadow map | sShadowMap_f1_0 | s0 | external shadow |

## Permutation policy

FXO is a permutation corpus. Selection uses sampler/interface/vertex evidence and preserves ambiguity instead of choosing by archive order.

## Current boundary

Static material binding is sufficient to feed DrawPacket/RenderCommand.

The remaining BMW render problem is:

`static material → exact runtime draw instance → complete shader/material execution`

External s0/s3 resources and unsupported shader operations remain explicit dependencies.
