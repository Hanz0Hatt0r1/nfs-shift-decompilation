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
- PART runtime → generated FLAT-like 0x40-byte record materialization through FUN_00689db0.

## Explicitly unresolved

The project does not invent:

- semantics of the remaining FLAT direct-record payload words and the concrete class behind populated +0x38 runtime object pointers;
- higher-level roles of individual LOD/HIERARCHY objects;
- full scene streaming and LOD behavior.

Track placement remains an evidence question.

## Next

Resolve only the remaining FLAT spatial/mask payload fields required to express the now-joined scene placement, then expose that neutral placement to RenderBinding.
