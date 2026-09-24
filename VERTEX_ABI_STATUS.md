# SHIFT Vertex ABI status

## Phase 11

SHIFT.VertexLayout/1 now records ABI evidence explicitly instead of exposing only a storage descriptor.

### Evidence states

- `proven`: source representation and semantic contract are established by the current parser/runtime evidence.
- `inferred`: storage/width is established, but the exact original D3D9 declaration still needs direct declaration evidence.
- `ambiguous`: multiple source interpretations remain valid, and the renderer must not choose silently.
- `unknown`: the property is not yet decoded well enough for a render contract.

### Current BMW target state

| MEB | Semantic | Android storage | State |
|---|---|---|---|
| 200 | POSITION0 | FLOAT32x3 | inferred |
| 220 | NORMAL0 | FLOAT32x3 | inferred |
| 240 | TANGENT0 | FLOAT32x3 | inferred |
| 250 | BINORMAL0 | FLOAT32x3 | inferred |
| 130-134 | TEXCOORD0-4 | FLOAT32x2 | inferred |
| 230-234 | TEXCOORD0-4 family | FLOAT32x3 | inferred |
| 310 | BLENDWEIGHT0 | FLOAT32x4 | proven |
| 580 | BLENDINDICES0 | UINT8x4 | proven |
| 460/461 | COLOR0/1 | UINT8x4 normalized | ambiguous |
| 033 | unknown | RAW4 | unknown |

`460/461` remain the primary unresolved render ABI because the current evidence does not prove the original D3D9 declaration (`D3DCOLOR` vs `UBYTE4N`) or channel byte order (`RGBA` vs `BGRA`).

`SHIFT.StaticDraw/1` therefore blocks those attributes only when the selected shader binding actually consumes them.
## Phase 28: vertex location collision guard

`build_vertex_input_locations()` now rejects two classes of silent ABI corruption: one D3D9 input register mapping to multiple target locations, and multiple shader registers mapping to the same target location. The resulting `location_collisions` and `unresolved` records remain machine-readable.
## Phase 41: COLOR0/COLOR1 evidence

`color_abi.py` now preserves the unresolved MEB 460/461 channel-order ambiguity as explicit RGBA and BGRA candidate interpretations. It records raw/candidate SHA-256, basic channel statistics and can compare both candidates against a known RGBA8 reference without selecting a winner.


## Phase 55: 230..234 reference execution

The deterministic reference layers now consume `230..234` directly as `TEXCOORD0..4` semantic inputs, preserving their FLOAT32x3 payloads. This is an execution mapping only; it does not assert an exact original D3D9 declaration beyond the evidence already recorded. Mixed 130/230 families for the same semantic remain a hard ABI collision.


## Phase 56: skin inputs at the renderer boundary

`BLENDWEIGHT0` (MEB 310) and `BLENDINDICES0` (MEB 580) are now available to the integrated vertex shader reference path. The neutral mesh values are converted to shader-register float4 values without normalization or reinterpretation. Actual SkinPose matrix application remains a separate milestone.


## Phase 65: TEXCOORD5 evidence boundary

`TEXCOORD5` is present in the recovered BMW shader interface and can be linked to a matching vertex output, but its MEB storage property remains unresolved. The runtime reference layer now accepts it only through an explicit semantic stream; no property id 235/236/etc. is inferred.


## Phase 66: COLOR evidence CLI

`shift_importer.py color-evidence` is now the standard entry point for collecting evidence on MEB properties 460/461. It preserves both RGBA and BGRA candidate streams and reports exact byte differences against an external RGBA8 reference without changing the unresolved ABI status.


## Phase 67: MEB JSON evidence input

The COLOR ABI investigation no longer requires manual raw-stream extraction. The evidence CLI accepts canonical MEB mesh JSON and reconstructs the exact four-byte `colors`/`colors2` streams emitted by the decoder, preserving the unresolved declaration/channel-order status.


## Phase 68: direct MEB resource evidence

`color-evidence-resource` can read properties 460/461 directly from a `.meb` stored inside a `.bff`, recording entry index, resource SHA256, vertex count and `property_layout` metadata. This is now the canonical ingestion path for future real BMW color evidence.


## Phase 69: COLOR corpus consistency

Multiple 460/461 evidence reports can now be aggregated without selecting RGBA/BGRA. Candidate hashes and cross-report stability are exposed as machine-readable data for later declaration verification.


## Phase 70: corpus-scale COLOR evidence

A directory-level BFF scan now collects 460/461 samples from decoded MEB resources and records archive/resource identity. This provides cross-vehicle evidence for future D3D9 declaration/channel-order verification without changing the current ambiguous runtime ABI.

## Phase 72: packed-color evidence from SHIFT.exe

The uploaded full Ghidra decompilation provides a new source-level observation in the
original renderer. `FUN_008310c0` rounds a float4 color to 8-bit channels and constructs
the value as `0xAARRGGBB`; on the original little-endian Windows target this is a BGRA
byte sequence in memory. The same helper is called from the vertex-buffer conversion
logic in `FUN_00854e70`, where a 4-byte converted value is written into the generated
vertex buffer.

This is **supporting evidence for the packed-color/D3DCOLOR-style candidate**, but it
does not by itself prove that MEB properties 460/461 use `D3DDECLTYPE_D3DCOLOR` rather
than `D3DDECLTYPE_UBYTE4N`. The exact MEB declaration remains ambiguous.

`color_abi.py` and `vertex_layout.py` now preserve this distinction explicitly:
- `UBYTE4N` candidate: RGBA bytes are consumed in memory order and normalized;
- `D3DCOLOR` candidate: packed BGRA memory is expanded to shader-visible RGBA;
- no candidate is selected automatically.

## Phase 74: machine-readable SHIFT.exe source evidence

`d3d9_source_evidence.py` and `shift_importer.py source-d3d9-evidence` now turn the
recovered `SHIFT.exe.c` observations into a reproducible JSON report. The extractor
records `FUN_008310c0` as the packed-color helper and `FUN_00854e70` as the vertex
conversion/declaration path where type code 4 calls that helper. It also records the
`STREAM` parser's `Type`, `Usage` and `Channel` fields.

The extractor deliberately reports `MEB 460/461 -> type 4` as `not-proven`: the
exported C does not expose the contents of `DAT_00b90088` / `PTR_DAT_00b901d0` well
enough to establish that exact property-to-type linkage. Therefore phase 74 improves
provenance and repeatability without changing the runtime ABI selection.

## Phase 78: recovered D3D9 primitive-type switch

The recovered `FUN_00854e70` declaration conversion switch contains every type code `0..16`. A dedicated `d3d9_type_semantics.py` evidence layer records each case's source behavior and the corresponding D3D9 `D3DDECLTYPE` name. The strongest new link is type code `4 -> D3DDECLTYPE_D3DCOLOR -> FUN_008310c0 packed-color conversion`.

This proves the semantics of the recovered type-code switch, but it still does not prove `MEB 460/461 -> type code 4`. The mesh ABI therefore remains ambiguous until the declaration/table linkage is recovered.

The full supplied source snapshot is recorded without including the game source itself in `evidence/shift_d3d9_type_switch_snapshot.json`.


## Phase 80: recovered Usage semantics

The recovered XML stream loader iterates a fixed usage domain `0..8` and resolves the usage name through `PTR_s_Position_00b901a8`. Source-visible entries are `Position`, `Weights`, `Normal`, an opaque `DAT_00b1d188` entry, `Tangent`, `Binormal`, `Colour`, `Depth`, and `Indices`. Usage code `6 -> Colour` is now machine-readable. This does not resolve the separate Type table, so COLOR0/1 remain ambiguous.


## Phase 81: raw memory table evidence

`d3d9_memory_table_evidence.py` provides an input path for the data missing from the recovered C export: a raw memory window plus its virtual base address. The tool decodes `DAT_00b90088`, `DAT_00b900d8`, usage tables, and the 17-entry `PTR_DAT_00b901d0` pointer table without inventing initializer values. Resolved printable C strings are reported as evidence; unresolved pointers remain unresolved.


## Phase 83: STREAM declaration record semantics

The recovered loader constructs a fixed 8-byte record for each XML `STREAM` entry whose six fields match the documented `D3DVERTEXELEMENT9` order: `Stream` (WORD), `Offset` (WORD), `Type` (BYTE), `Method` (BYTE), `Usage` (BYTE), `UsageIndex` (BYTE). Source evidence shows `Stream=0`, a running `Offset`, the resolved D3D9 `Type` at `+4`, `Method=0`, the resolved `Usage` at `+6`, and the XML `Channel` at `+7`. Microsoft documents the same field order and meanings for `D3DVERTEXELEMENT9`. This is a source-level ABI observation and does not assign MEB property ids 460/461 to any Type ordinal.


## Phase 84: declaration canonicalizer evidence

`FUN_00830f80` compares the two WORD fields plus the four BYTE fields of the recovered 8-byte declaration record and copies/interns the complete record. Combined with phase 83, this is source-level evidence that the renderer treats the recovered `Stream/Offset/Type/Method/Usage/UsageIndex` tuple as the declaration identity. MEB 460/461 linkage remains unresolved.


## Phase 85: Type -> layout table semantics

The renderer uses the declaration Type byte at offset `+4` as the common key for two opaque runtime tables. `DAT_00b8eef0[Type]` supplies the element byte size; `DAT_00b8ef38[Type]` supplies the component count. The source repeatedly uses these values for stream offset accumulation, vertex-buffer allocation/copy sizes and source component reads. The exact table initializer bytes are still absent from the exported Ghidra C, so numeric contents are not guessed.


## Phase 86: Type semantic validation profile

The recovered D3D9 Type switch is now paired with a validation-only semantic profile. The profile expects the documented packed sizes/components for Type `0..16` and can compare them against real `DAT_00b8eef0`/`DAT_00b8ef38` bytes when a memory dump is supplied. Missing values stay unavailable; mismatches are surfaced rather than repaired. `MEB 460/461 -> Type` remains a separate unresolved linkage.


## Phase 87: Stream-group topology

The recovered renderer groups declaration records by Stream id. The Stream/Type/Usage/Channel input arrays are carried separately; each element resolves its Type and Usage through the recovered ordinal tables, writes Channel as UsageIndex, and is appended to a per-stream record list. The same Type byte indexes `DAT_00b8eef0` to grow the per-stream byte-size accumulator. This provides source-backed topology for future MEB→STREAM correlation, without asserting a property mapping.


## Phase 90: D3D9 declaration evidence chain

`SHIFT.D3D9DeclarationChainEvidence/1` теперь объединяет четыре независимых source-backed звена: Type size/component semantics, STREAM grouping, 8-byte `D3DVERTEXELEMENT9`-shaped record и full-record canonicalization. Отсутствующее звено блокирует итоговый статус. Реальный runtime declaration и MEB 460/461 → Type ordinal остаются отдельными unresolved boundaries.

## Phase 91: raw declaration instance decoder

`SHIFT.D3D9DeclarationInstanceEvidence/1` даёт воспроизводимый декодер фактических 8-байтных declaration records. Type codes 0..16 разрешаются через recovered Type profile, `0x11` экспонируется как `D3DDECLTYPE_UNUSED`; неполный payload и неизвестный Type не принимаются как валидный declaration. Numeric Usage/UsageIndex сохраняются без недоказанной semantic remapping, а MEB 460/461 linkage остаётся `not-proven`.

## Phase 92: instance-to-chain integration

При передаче `SHIFT.D3D9DeclarationInstanceEvidence/1` в declaration chain фактический instance становится отдельным обязательным check. Это связывает декодер bytes с ранее подтверждённой source-backed ABI-формой, не закрывая MEB 460/461 → Type ordinal.


## Phase 93: declaration instance integrity

Точная форма `D3DDECL_END` теперь фиксируется как отдельное наблюдение, а chain проверяет внутреннюю согласованность runtime report, а не доверяет его полю `status`. Это снижает риск ложного `observed` при импорте внешних memory-dump evidence.


## Phase 94: runtime memory declaration evidence

SHIFT.D3D9MemoryDeclarationEvidence/1 теперь связывает сырой loaded-memory dump с recovered 8-byte D3D9 declaration instance через явный адресный диапазон, little-endian marker, SHA-256 полного dump/slice и exact raw bytes. Declaration array автоматически ограничивается точным D3DDECL_END sentinel; дополнительные bytes после него не считаются частью ABI.

Chain-level validation перепроверяет slice hash и структуру вложенного declaration report, поэтому внешний JSON не может одним полем status=match скрыть повреждённые bytes. Provenance фиксирует источник, но остаётся not-authenticated: сам факт наличия dump не является независимой проверкой его происхождения. MEB 460/461 -> Type ordinal остаётся not-proven.
