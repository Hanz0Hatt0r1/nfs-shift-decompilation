# Render pipeline stage: VHF -> MEB -> BMT -> FX/FXO

Добавлен `render_pipeline.py`, который строит `SHIFT.RenderBinding/1` поверх Android IR.

Пайплайн:
1. VHF node resource -> MEB.
2. MEB primitive material reference.
3. Legacy `.mtx` автоматически разрешается как `.bmt`.
4. BMT -> FX source -> все соответствующие FXO cache permutations.
5. `material_linker.py` выбирает совместимую FXO permutation по sampler set и восстанавливает D3D9 sampler registers.
6. VHF Matrix/parent hierarchy превращается в world 4x4 transform.
7. Результат сохраняет unresolved references вместо удаления.

На реальном BMW M3 E36 установлено: 162 MEB, 21 уникальный material alias и VHF содержит 162 render-resource references. Для bodywork FXO реальные CTAB sampler registers восстанавливаются (diffuse s1, specular s2, scratch s4); остальные renderer-global samplers остаются external/specialised.

Следующий критический слой: доказать точный vertex ABI и затем довести реальный material/shader render на golden BMW mesh. VS/PS semantic pairing и SHIFT.StaticDraw/1 уже реализованы.

## Vertex layout layer

MEB parsing now preserves exact `payload_offset`, `stride` and payload byte count for every vertex property. `vertex_layout.py` converts those properties into `SHIFT.VertexLayout/1` Android-neutral attributes. FLOAT3/FLOAT2/FLOAT4 and UBYTE4 storage are established from the decoder; MEB color properties 460/461 remain explicitly ambiguous between D3D9 `D3DCOLOR` and `UBYTE4N` until byte-order behavior is proven.

`render_pipeline.py` now places this vertex layout beside every draw packet and passes the MEB properties into VS selection.

## Phase 11: vertex ABI evidence

SHIFT.VertexLayout/1 now carries an explicit abi_status per attribute (proven, inferred, ambiguous, unknown) plus a human-readable evidence basis. The layout also reports semantic collisions instead of silently collapsing multiple MEB properties onto one semantic key.

StaticDraw/1 now blocks an ambiguous vertex ABI only when the selected shader actually consumes that property. This prevents an unused ambiguous color field from blocking unrelated draws while preventing a renderer from silently choosing RGBA/BGRA or another unresolved declaration form.
