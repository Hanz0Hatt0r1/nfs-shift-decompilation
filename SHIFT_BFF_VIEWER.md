# SHIFT BFF Viewer

Full Linux utility included directly in this repository.

## Quick start

From the repository root:

    sudo apt install python3 python3-tk
    ./shift-bff-viewer /path/to/BMW_M3_E36.bff

If `RENDER.bff` is next to the vehicle archive it is detected automatically.
To specify it explicitly:

    ./shift-bff-viewer /path/to/BMW_M3_E36.bff --render-bff /path/to/RENDER.bff

The viewer uses the current project implementations for BFF v3, zlib/XMem-LZX,
MEB, VHF scene assembly, BMT/MTX materials, DDS textures and FX/FXO shader
metadata. The viewport is a deterministic software preview using the recovered
material parameters; it is not a byte-for-byte D3D9 FXO executor yet.

## Other commands

    ./shift-bff-viewer extract /path/to/file.bff -o extracted
    ./shift-bff-viewer info /path/to/file.bff

Or invoke the implementation directly:

    python3 tools/shift_bff_viewer.py /path/to/file.bff

## Controls

- LMB drag: orbit
- Mouse wheel: zoom
- R: reset camera
- Shader/material preview checkbox: toggle textured material path
- Open Render BFF: attach another shader library
- Extract all: decode the archive and write manifest.json
