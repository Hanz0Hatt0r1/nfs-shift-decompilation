# SHIFT Track / Scene status

## Current boundary

`SGB container → NODE/PART/SUMM/OCCL/FLAT runtime records → partial scene/object IR`

The top-level SGB parser preserves header, reversed FourCC tags, chunk sizes and payload hashes; bytes after END are retained as the SGB-relative reference arena used by NODE/object strings rather than mislabeled as trailing garbage.

## Runtime reconstruction

Covered boundaries include:

- NODE 0x1c-byte metadata with inline object payloads and SGB-relative reference offsets;
- LOD/HIERARCHY MATRIX records, subobject tables and recursive OBJECT payloads;
- PART corrected 0x30-byte fixed layout plus variable child-object table;
- PART runtime partition tree: AABB nodes, four child-partition ID/pointer slots, mask-driven insertion and scene-wrapper partition pointers;
- SUMM;
- OCCL fixed 0x38-byte source records with source-backed Name/Resource and PositionTL/TR/BL/BR semantics;
- OCCL concrete 0x120-byte runtime objects plus header-bit1 wrapper/batch admission modes;
- FLAT;
- binary NODE/SUMM object routing into LOD/HIERARCHY/OBJECT; DAMAGE is retained only as a concrete alternate XML-path runtime kind;
- common object byte +0x21 preserved as source-unconsumed raw data; it is zero across 541 recursively decoded NODE objects from the four Silverstone Era3 visual variants;
- XML-only DAMAGE wrapper fields for matrices (+0x80), runtime matrix array (+0x84), runtime subobject array (+0x88) and MatrixNumber (+0x90);
- recursive FLAT tree structure with 0x40-byte direct records;
- production signed-terminal FLAT span normalization controlled by SGB header bit2;
- FLAT +0x3c runtime index table joins and +0x38 direct-object lookup/refcount teardown consumers;
- FLAT leaf +0x3c → SUMM wrapper-order placement identity, production-verified across 21,580 Silverstone placements;
- PART one-based child-object IDs → NODE wrapper registry indices;
- PART runtime → generated FLAT-like 0x40-byte record materialization through FUN_00689db0;
- FLAT leaf include/exclude 64-bit query-mask pairs at +0x00..+0x0f;
- FLAT leaf bounding sphere at +0x10..+0x1c;
- FLAT tree-node AABB at header +0x00..+0x14;
- FLAT leaf +0x20..+0x34 consumed directly by the secondary spatial-query virtual interface as six-float bounds; all 21,580 Silverstone leaves validate as ordered min/max triples whose midpoint matches the source-backed sphere centre;
- `SHIFT.SGBScenePlacement/1` normalizes FLAT/SUMM and PART/NODE object identity with source-backed node/leaf/partition geometry; FLAT leaf bounds are admitted as proven geometry;
- `SHIFT.SGBObjectRenderHandoffSet/1` maps OBJECT resource descriptor +0x80 to renderer factory vfunc +0x214 and transform submission vfunc +0x2c;
- `SHIFT.SGBObjectResourceFactory/1` maps the descriptor's default MeshType/type-0 path, `.imb/.imx` promotion to MeshInst/type 7 in `FUN_00831940`, and the additional type-7 render-instance call before the common transform submission;
- `SHIFT.SGBMeshInstRuntime/1` maps `.imx` to `LoadXMLMeshFromResource`, `.imb` to `LoadBinaryMeshFromResource`, the 0xb0 MeshInst layout, descriptor +0x30 → runtime +0x80 count, aligned 0x40-stride storage at +0x84, and renderer category-10 registration/teardown;
- `SHIFT.IMBBinaryMeshSchema/1` decodes the source-backed IMB fixed header, optional bone-name/0x30 matrix block and 0x0c Type/Usage/Channel stream records;
- `SHIFT.IMBBinaryPrefix/1` reconstructs the 4/6/11/11 packed version, v0.2/v0.4 control variants, embedded resource-name boundary, v0.4 4-byte name alignment and automatic bone-block gate/header location;
- `SHIFT.IMBNeutralGeometry/1` consumes the proven v0.4 stream/primitive payload into neutral vertices, UV/color/bone fields and ordered primitive index ranges while preserving unmapped streams raw;
- admitted `.imb` MeshInst resources now resolve through `SHIFT.IMBNeutralGeometry/1` into the existing BMT/FX/FXO → DrawPacket/StaticDraw/RenderCommand path while retaining explicit IMB provenance;
- the supplied Silverstone Era3 corpus production-validates 427/427 IMBs: all are v0.4.0.0, all observed vertex property triples are already supported, 92 carry bone blocks, and no decoded primitive record leaves trailing bytes;
- all 428 Silverstone IMB primitive `.mtx` material references resolve to exactly one same-archive `.bmt` entry across 84 unique logical materials;
- all 239 archive-local BMT occurrences parse, all 563 DDS references resolve in the same Silverstone BFF, and all five global `render/shaders/*.fx` families resolve exactly once in retail `RENDER.bff`;
- `SHIFT.ShaderFamilyFXOInventory/1` production-inventories those five compiled cache families across Silverstone + `RENDER.bff`: 1,280 FXO copies collapse to 368 unique decoded payloads with zero D3D9 parse failures; static family-level permutation selection remains explicitly ambiguous;
- `SHIFT.IMBMaterialShaderRanking/1` adds concrete primitive-context ranking over IMB vertex properties + same-archive BMT + exact FX source + deduplicated family FXOs using the existing material linker; Phase 567 executes all 428 production primitive bindings and finds 428 ambiguous / 0 unique / 0 heuristic / 0 missing, collapsing the tied surface to 51 distinct permutation identities;\n- `SHIFT.IMBRuntimeShaderTargetSet/1` preserves each complete top-rank set as runtime-observable hashes without selecting a permutation; all 428 Silverstone bindings are capture-ready and collapse globally to 51 pixel-shader hashes, with 5–15 targets per primitive and zero exact-pair-attribution-ready rows;\n- `SHIFT.IMBRawCaptureShaderPrefilter/1` consumes those targets against raw D3D9 JSONL, tracks shader creation/set state per device and preserves only DrawIndexedPrimitive events whose active shader bytes intersect the whitelist; it explicitly does not claim resource, draw-range or same-instance identity;\n- Phase 570 propagates exact archive-local IMB path + decoded payload SHA-256 plus source-backed primitive first/index counts into the ranking/target contracts; all 428 Silverstone primitive bindings pass the new `same_instance_match_ready` static gate;\n- Phase 571 adds source Type/Usage/Channel declaration descriptors, preserves every static VS/PS candidate variant behind each deduplicated prefilter hash, and emits `SHIFT.IMBRuntimeResourceEvidenceSet/1` for D3D9 runtime binding correlation without claiming IMB/MEB equivalence;
- OBJECT MatrixNumber=-1 produces a source-equivalent numeric 4x4 from WXYZ quaternion, XYZ offset and uniform scale; MatrixNumber>=0 selects a 0x40-byte parent MultiMatrix slot.
- `SHIFT.SGBMultiMatrixEvaluation/1` reconstructs static mode-1 hierarchy arithmetic: the owner overwrites world slot 0 from its runtime root input, then evaluates slots 1..N-1 as `local * parent_world` using the low byte of the serialized parent dword.
- `SHIFT.SGBRootTransformState/1` reconstructs the root lifecycle: constructor world slot 0 equals serialized local slot 0; SceneGraph immediate/deferred transform updates replace it with the exact transported 0x40-byte matrix. Unknown per-instance update history remains blocked.
- `SHIFT.SGBRenderBindingAdmission/1` joins source-backed placement rows to recursive OBJECT resource/world transforms without promoting blocked rows.
- `SHIFT.SGBRenderBindingBridge/1` resolves scene-admitted MEB instances through the existing MEB/BMT/FXO path into generic `SHIFT.RenderBinding/1`, preserving the admitted numeric world matrix.

## Explicitly unresolved

The project does not invent:

- the concrete class behind populated FLAT +0x38 runtime object pointers;
- higher-level roles of individual LOD/HIERARCHY objects;
- full scene streaming and LOD behavior.

Track placement identity, culling geometry, MultiMatrix arithmetic, root-transform transport, placement→OBJECT admission, retail MeshType/MeshInst factory selection, MeshInst runtime lifecycle, IMB version/prefix/header/stream/primitive payload plus neutral geometry adaptation, admitted MEB/IMB integration with generic RenderBinding, complete Silverstone Era3 IMB binary-geometry coverage, same-archive BMT identity, track-local BMT/DDS dependency closure, all five referenced global FX source families and their compiled FXO cache inventory are source-backed. The material/geometry-aware ranking stage is production-frozen across all 428 primitive bindings; exact FXO/VS-PS attribution remains runtime-gated. Phase 568 converts the complete tied surface into a production-validated 51-pixel-hash capture whitelist covering all 428 primitive bindings, Phase 569 provides the raw D3D9 shader/draw prefilter, Phase 570 closes the static resource/draw side of same-instance matching for all 428 bindings, and Phase 571 adds declaration descriptors plus lossless VS/PS candidate-variant provenance and runtime-resource handoff. The IMX neutral adapter, concrete per-instance SceneGraph transform-update history and higher-level streaming behavior remain evidence questions.

## Next

`SHIFT.SGBRenderBindingBridge/1` now feeds admitted MEB and v0.4 IMB instances into generic `SHIFT.RenderBinding/1`; IMB is normalized through `SHIFT.IMBNeutralGeometry/1` without being relabeled as MEB. Phase 571 completes the static runtime-attribution handoff with exact resource/draw identity, declaration descriptors and lossless shader variants. The immediate next scene step is to execute `SHIFT.D3D9RuntimeBindingEvidence/1` for Phase 569 candidate resources/draws and join same-instance declaration + exact indexed range + observed VS/PS hashes against the preserved variants; after that come native scene loading, the IMX XML adapter, or recovery/capture of transform-update history for blocked MatrixNumber instances.
