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
- recursive FLAT tree structure with 0x40-byte direct records;
- production signed-terminal FLAT span normalization controlled by SGB header bit2;
- FLAT +0x3c runtime index table joins and +0x38 direct-object lookup/refcount teardown consumers;
- one-based OCCL/NODE wrapper catalog used by PART child-object ids;
- source-backed PART→FLAT fallback builder with exact 0x20 node / 0x40 direct-record accounting and 0x28/0x40 runtime link tables;
- explicit prebuilt-FLAT mode for shipped retail scenes where PART conversion is skipped.

## Explicitly unresolved

The project does not invent:

- semantics of the remaining FLAT direct-record payload words and the concrete class behind populated +0x38 runtime object pointers;
- the unnamed common object byte +0x21 and higher-level roles of individual LOD/HIERARCHY objects;
- semantic names for the four dwords copied from scene-wrapper +0x0c object +0x10..+0x1c into generated FLAT direct records;
- full scene streaming and LOD behavior.

Track placement remains an evidence question.

## Next

Resolve the four source-backed generated-FLAT direct-record dwords from scene-wrapper +0x0c object +0x10..+0x1c, correlate them with the production prebuilt-FLAT payload, and expose only proven placement fields to RenderBinding.
