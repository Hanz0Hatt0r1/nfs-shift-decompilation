# D3D9 COLOR source-evidence status

Phase 75 extends the SHIFT.exe.c evidence scanner with source-location tracking and the type-table chain used by the original Win renderer.

## Newly recorded observations

The recovered C source explicitly shows:

- FUN_00853c20 reading the opaque DAT_00b90088 table by ordinal.
- The XML stream loader comparing Type text against PTR_DAT_00b901d0, then passing the matching ordinal through FUN_00853c20 into the declaration record.
- XML Usage resolving through FUN_00853c40 and Channel being copied into the declaration record.
- XML stream-data family 6 being named Colour.
- FUN_00854e70 handling declaration type 4 through FUN_008310c0.

The scanner also reports the 1-based line number of matched source markers and keeps the SHA-256, byte size and line count of the analyzed decompilation.

## ABI boundary

This still does not prove:

MEB 460/461 -> XML/Type ordinal -> D3D9 type 4

and therefore does not select D3DCOLOR over UBYTE4N.

The authoritative runtime status remains:

selection = not-selected
verified_abi = false

## Reproducibility

Run:

    python shift_importer.py source-d3d9-evidence SHIFT.exe.c evidence.json

The report now contains source_line fields, making the evidence trace auditable against the exact decompilation snapshot.
