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
- NODE object payload routing into LOD/HIERARCHY/OBJECT/DAMAGE;
- DAMAGE wrapper two-child ownership, symmetric proxy dispatch, matrix-array and MatrixNumber runtime consumers;
- recursive FLAT tree structure with 0x40-byte direct records;
- production signed-terminal FLAT span normalization controlled by SGB header bit2;
- FLAT +0x3c runtime index table joins and +0x38 direct-object lookup/refcount teardown consumers.

## Explicitly unresolved

The project does not invent:

- semantics of the remaining FLAT direct-record payload words and the concrete class behind populated +0x38 runtime object pointers;
- exact serialized DAMAGE child-offset table/slot roles and the unnamed NODE/object byte +0x21;
- complete NODE placement/transform semantics;
- full scene streaming and LOD behavior.

Track placement remains an evidence question.

## Next

Locate a DAMAGE-bearing SGB beyond the Silverstone corpus, or continue with the unnamed NODE/object byte and FLAT payload consumers; keep serialized DAMAGE child offsets fail-closed until observed.
