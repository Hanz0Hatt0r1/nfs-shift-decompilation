# Direct PE evidence status

Phase 82 adds a pure-Python PE32/PE32+ resolver for the virtual addresses recovered from `SHIFT.exe.c`.

## Supported evidence path

`SHIFT.exe` -> PE header -> image base -> section table -> virtual address -> file offset -> D3D9 table bytes

The resolver covers the recovered regions around `DAT_00b90088`, `DAT_00b900d8`, `DAT_00b9011c`, `DAT_00b90140`, `DAT_00b90178`, and `PTR_DAT_00b901d0`. It also follows the 17 type-name pointers when their target strings are file-backed and printable ASCII.

## Important limitation

An executable may contain only loader-initialized/BSS storage for these globals. The resolver therefore reports `file_backed = false` when bytes are not present in the PE file rather than treating zeros or absence as recovered initializer data.

The COLOR ABI remains separate:

`MEB 460/461 -> Type ordinal -> D3D9 type`

must still be evidenced before changing the renderer's ambiguous state.

## CLI

    python shift_importer.py source-d3d9-pe-evidence SHIFT.exe d3d9-pe.json

Use `--image-base 0x400000` only when an external artifact requires overriding the image base parsed from the PE header.
