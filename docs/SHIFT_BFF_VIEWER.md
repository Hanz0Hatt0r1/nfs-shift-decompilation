# SHIFT BFF Viewer

## Purpose

Linux desktop viewer for inspecting SHIFT BFF archives using the current project parsers.

It is a diagnostic preview, not a byte-for-byte D3D9/FXO replacement.

## Quick start

```bash
sudo apt install python3 python3-tk
./shift-bff-viewer /path/to/BMW_M3_E36.bff
./shift-bff-viewer /path/to/BMW_M3_E36.bff --render-bff /path/to/RENDER.bff
```

## Commands

```bash
./shift-bff-viewer extract /path/to/file.bff -o extracted
./shift-bff-viewer info /path/to/file.bff
python3 tools/shift_bff_viewer.py /path/to/file.bff
```

## Controls

LMB drag: orbit

Mouse wheel: zoom

R: reset camera

Material/shader preview: toggle textured preview

Open Render BFF: attach another shader library

Extract all: decode and export manifest

## Scope

The viewer uses the project's BFF/XMem-LZX, MEB/VHF, BMT/MTX, DDS and shader metadata implementations. Unsupported full-runtime shader behavior may be approximated or omitted by design.
