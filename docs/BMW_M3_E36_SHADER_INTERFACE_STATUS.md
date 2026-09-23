# BMW M3 E36: VS/PS semantic interface status

Реальный набор: BMW_M3_E36.bff + BMW_M3_E36_Cockpit.bff.

- 1,707 FXO files
- 10,756 decoded shader programs: 5,378 pixel + 5,378 vertex
- 125 unique stage+input/output signatures
- 21,488 VS/PS cross-pairs внутри FXO
- 13,909 пар (64.7%) имеют полное покрытие PS input semantics со стороны VS output semantics

## D3D9 declaration codes

Исправлена прежняя таблица usage codes. По официальной D3D9 `D3DDECLUSAGE`:

- 0 POSITION
- 1 BLENDWEIGHT
- 2 BLENDINDICES
- 3 NORMAL
- 4 PSIZE
- 5 TEXCOORD
- 6 TANGENT
- 7 BINORMAL
- 8 TESSFACTOR
- 9 POSITIONT
- 10 COLOR
- 11 FOG
- 12 DEPTH
- 13 SAMPLE

В M3 это даёт важный результат: массовый input `v1` ранее ошибочно отображался как SAMPLE0, а реально это COLOR0.

## MEB -> vertex semantics

Подтверждённые mappings:

- 200 -> POSITION0
- 460 -> COLOR0
- 220 -> NORMAL0
- 240 -> TANGENT0
- 250 -> BINORMAL0
- 130..134 -> TEXCOORD0..4
- 310 -> BLENDWEIGHT0
- 580 -> BLENDINDICES0

230..234 — 3-компонентные UVW-каналы; пока связываются с соответствующими TEXCOORD slots, но исходный D3D declaration type ещё требует отдельной проверки.

На двух M3 архивах обнаружено 8 уникальных layout combinations в основном car BFF и 9 в cockpit BFF.

## Реальная VS/PS связь

Для одного из bodywork FXO:

- PS inputs: TEXCOORD5 -> v0, TEXCOORD0 -> v1, TEXCOORD1 -> v2
- VS outputs: TEXCOORD5 -> oT1, TEXCOORD0 -> oT2, TEXCOORD1 -> oT3

Связь полная, несмотря на разные физические номера регистров. Значит runtime linker должен использовать semantic key `(usage,index)` и строить explicit interpolator map.

## Что осталось

Следующая задача — восстановить D3D9 vertex declaration type/packing для каждого MEB property, после чего VS input semantic set можно превратить в реальный Android vertex layout. Затем MaterialBinding сможет фиксировать конкретную VS/PS permutation вместо одной только sampler permutation.