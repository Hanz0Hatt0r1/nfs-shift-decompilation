# Phase 224 — PE-backed D3D9 semantic declaration map

Phase 224 normalizes the file-backed D3D9 declaration tables from the supplied SHIFT.exe into SHIFT.D3D9PESemanticMap/1. The map exposes all 17 Type records with the executable's internal names and all 9 Usage ordinals with their numeric D3D9 values.

A separate SHIFT.D3D9RuntimePESemanticParity/1 validator can compare a runtime declaration instance against this map. This proves numeric Type/Usage consistency with the exact executable without assigning a runtime declaration to an MEB property by number alone.

For the supplied executable, the COLOR ABI remains Type 4 / D3DCOLOR and Usage ordinal 6 / numeric Usage 10. Same-instance MEB -> declaration -> indexed draw proof remains a separate gate.
