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

Track placement identity, culling geometry, MultiMatrix arithmetic, root-transform transport, placement→OBJECT admission, retail MeshType/MeshInst factory selection, MeshInst runtime lifecycle, IMB version/prefix/header/stream schema and admitted-MEB integration with generic RenderBinding are source-backed. Full IMB vertex/primitive payload consumption, the IMX neutral adapter, concrete per-instance SceneGraph transform-update history and higher-level streaming behavior remain evidence questions.

## Next

`SHIFT.SGBRenderBindingBridge/1` feeds admitted MEB instances into generic `SHIFT.RenderBinding/1`; Phase 557 now auto-decodes the source-backed IMB prefix before the Phase 556 schema. Next scene work is to close remaining vertex/primitive payload consumption, build the IMX XML adapter, or recover/capture transform-update history for blocked MatrixNumber instances.
