# SHIFT Track / Scene status

## Current boundary

`SGB container → NODE/PART/SUMM/OCCL/FLAT runtime records → partial scene/object IR`

The top-level SGB parser preserves header, reversed FourCC tags, chunk sizes, payload hashes and trailing bytes.

## Runtime reconstruction

Covered boundaries include:

- NODE;
- PART corrected 0x30-byte fixed layout plus variable child-object table;
- PART runtime partition tree: AABB nodes, four child-partition ID/pointer slots, mask-driven insertion and scene-wrapper partition pointers;
- SUMM;
- OCCL fixed 0x38-byte source records with source-backed Name/Resource and PositionTL/TR/BL/BR semantics;
- OCCL concrete 0x120-byte runtime objects plus header-bit1 wrapper/batch admission modes;
- FLAT;
- NODE object payload routing into OBJECT/HIERARCHY/DAMAGE;
- recursive FLAT tree structure with 0x40-byte direct records;
- production signed-terminal FLAT span normalization controlled by SGB header bit2;
- FLAT +0x3c runtime index table joins and +0x38 direct-object lookup/refcount teardown consumers.

## Explicitly unresolved

The project does not invent:

- semantics of the remaining FLAT direct-record payload words and the concrete class behind populated +0x38 runtime object pointers;
- deeper object field meanings;
- complete NODE placement/transform semantics;
- full scene streaming and LOD behavior.

Track placement remains an evidence question.

## Next

Continue with deeper OBJECT/HIERARCHY consumers and the remaining FLAT float payload fields, using the Silverstone production corpus as the regression oracle before joining proven scene data into RenderBinding.
