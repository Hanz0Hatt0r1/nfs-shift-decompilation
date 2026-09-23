# BMW M3 E36 material/shader binding result

Источник: загруженный набор BMW_M3_E36.bff + BMW_M3_E36_Cockpit.bff.

## Архивная статистика

- 2 BFF: 2,165 ресурсов
- 1,707 FXO, 75 BMT, 147 DDS, 206 MEB
- Type-2 XMem/LZX: 2,165/2,165 ресурсов декодированы без ошибок
- все 206 MEB прошли существующий MEB -> MGEO конвертер

## Точная связь BMT -> FX -> FXO

Для vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt:

| BMT shaderparam | FX sampler | D3D9 register | texture |
|---|---|---:|---|
| diffuseTexture | diffuseMap | s1 | COMMON_PAINT.dds |
| specularTexture | specularMap | s2 | COMMON_PAINT_SPECULAR.dds |
| scratchControlTexture | scratchControlMap | s4 | COMMON_BLANK.dds |
| renderer-global | environmentMap | s3 | external cube map |
| renderer-global | sShadowMap_f1_0 | s0 | external shadow map |

RegisterSet=3 в D3DX9 CTAB означает sampler, а RegisterIndex дает фактический sN.

## Sampler state из bodywork.fx

- diffuse: Linear / Linear / Linear, Wrap / Wrap, sRGB
- specular: Linear / Linear / Linear, Wrap / Wrap, sRGB
- scratch control: Linear / Linear / None, Clamp / Clamp, linear
- environment cube: Linear / Linear / Linear, Clamp / Clamp / Clamp, linear

Теперь BMT можно превращать не просто в список DDS, а в платформенный material binding с точными D3D9 sampler slots и source-level sampler state.

## Ограничение

FXO содержит несколько compilation permutations одного bodywork.fx. По sampler-set можно отсеять несовместимые варианты и восстановить register binding, но один только sampler-set не доказывает уникальный permutation hash.

## Следующий этап

1. связать VHF node -> MEB -> material -> MaterialBinding -> VS/PS pair;
2. восстановить semantic vertex/pixel interface;
3. убрать material-order-inferred из SHIFT.DrawPacket/1;
4. затем добавить IMB skeletal animation и scene transforms.
