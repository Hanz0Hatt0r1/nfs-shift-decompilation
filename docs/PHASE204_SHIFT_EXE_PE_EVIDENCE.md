# Phase 204 — exact SHIFT.exe PE/D3D9 table evidence

The supplied retail SHIFT.exe (PE32) was inspected directly and the recovered
virtual addresses from SHIFT.exe.c were mapped to file-backed bytes.

## Exact executable identity

- Size: 8,801,792 bytes
- SHA-256: eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1
- Machine: PE32 x86 (0x014c)
- Image base: 0x00400000
- Recovered Type table: DAT_00b90088
- Recovered Usage table: DAT_00b9011c
- Recovered Type-name pointers: PTR_DAT_00b901d0

## Results

The executable contains file-backed D3D9 declaration lookup tables.

### Type

The recovered Type code table contains the expected 0..16 D3D9 declaration Type order.
The size and source-component tables exactly match the existing
SHIFT.D3D9TypeProfile/1 validation for all 17 meaningful types.

Type ordinal 4 has:
- internal executable name: RGBA32;
- element size: 4 bytes;
- source components: 4;
- profile identity: D3DDECLTYPE_D3DCOLOR.

### Usage

The nine recovered Usage entries are:

    ordinal: 0 1 2 3 4 5 6  7  8
    value:   0 1 3 5 6 7 10 12 2

The source-side Usage table names ordinal 6 Colour. Therefore the actual numeric
D3D9 Usage value in this executable is 10, not merely the internal ordinal 6.

## Consequence for the BMW COLOR bridge

The previously established real MEB descriptors are:

    property 460 -> [Type 4, Usage 6, Channel 0]
    property 461 -> [Type 4, Usage 6, Channel 1]

The supplied executable independently provides:

    Type 4  -> D3DDECLTYPE_D3DCOLOR / RGBA32
    Usage 6 -> D3DDECLUSAGE_COLOR (numeric value 10)

Together with the recovered Type-4 packed-color conversion path, this strengthens
the static ABI chain to:

    MEB 460/461
      -> descriptor Type 4 / Usage 6 / Channel
      -> D3D9 Type 4 / D3DCOLOR
      -> D3D9 Usage COLOR (10)
      -> BGRA memory / RGBA shader order

This is still static executable/resource evidence. It does not prove that a retail
runtime bound this declaration to the target BMW draw. That final step still requires
the authentic same-instance D3D9 capture.

The compact evidence artifact is stored at
docs/artifacts/evidence/shift_exe_102_d3d9_tables.json; the executable itself is not
committed to the repository.
