# D3D9 primitive type semantics status

Phase 78 turns the recovered FUN_00854e70 type switch into a reusable, machine-readable evidence layer.

## Source evidence

The recovered SHIFT.exe.c contains one declaration conversion switch with all 17 case codes 0..16. The numeric codes align exactly with the documented D3D9 D3DDECLTYPE enumeration.

The important source behaviors are retained in the report rather than inferred from the enum name:

- 0..3 share the float payload copy path.
- 4 packs four floats through FUN_008310c0.
- 5 rounds source components directly to bytes.
- 8 rounds components after multiplying by 255.0.
- 11..12 round after multiplying by 65535.0.
- 13..14 use a 10-bit packed conversion path.
- 15..16 use the recovered 16-bit-float encoder FUN_0064fcb0.

The report records the exact decompiled line containing each case label.

## COLOR boundary

The source evidence now makes the following chain much stronger:

Type code 4 -> packed-color conversion -> 0xAARRGGBB -> BGRA memory bytes on little-endian Windows

It still does not establish:

MEB property 460/461 -> Type code 4

Therefore COLOR0/1 remains ambiguous in the renderer ABI. The type-semantics module deliberately reports meb_property_mapping.status = not-proven.

## CLI

Run:

    python shift_importer.py source-d3d9-type-evidence SHIFT.exe.c d3d9-types.json

This command is intentionally separate from MEB property mapping so an observed D3D9 primitive type cannot silently become a mesh ABI selection.


## Phase 83: MEB linkage

Type semantics are now consumed by a source-correlated MEB linkage module. Type 4 is no longer an isolated enum observation: 460/461 map to `(4,6,0/1)` through the same three-DWORD property descriptor used by the original binary loader. The type-table initializer bytes remain opaque, but they are no longer needed to establish the 460/461 declaration type.
