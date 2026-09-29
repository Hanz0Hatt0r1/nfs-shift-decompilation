# SHIFT Track / Scene status

## Current boundary

`SGB container → NODE/PART/SUMM/OCCL/FLAT runtime records → partial scene/object IR`

The top-level SGB parser preserves header, reversed FourCC tags, chunk sizes, payload hashes and trailing bytes.

## Runtime reconstruction

Covered boundaries include:

- NODE;
- PART;
- SUMM;
- OCCL fixed 0x38-byte source records with source-backed Name/Resource and PositionTL/TR/BL/BR semantics;
- OCCL concrete 0x120-byte runtime objects plus header-bit1 wrapper/batch admission modes;
- FLAT;
- NODE object payload routing into OBJECT/HIERARCHY/DAMAGE;
- recursive FLAT tree structure with 0x40-byte leaf records.

## Explicitly unresolved

The project does not invent:

- FLAT leaf semantics;
- deeper object field meanings;
- complete NODE placement/transform semantics;
- full scene streaming and LOD behavior.

Track placement remains an evidence question.

## Next

Continue with PART consumers and FLAT leaf semantics, then correlate those mappings against real SGB samples before joining proven scene data into RenderBinding.
