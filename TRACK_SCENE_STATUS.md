# SHIFT Track / Scene status

## Current boundary

`SGB container → NODE/PART/SUMM/OCCL/FLAT runtime records → partial scene/object IR`

The top-level SGB parser preserves header, reversed FourCC tags, chunk sizes, payload hashes and trailing bytes.

## Runtime reconstruction

Covered boundaries include:

- NODE;
- PART;
- SUMM;
- OCCL;
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

Correlate real SGB samples with the runtime consumers, close deeper object/leaf semantics, then join proven scene data into RenderBinding.
