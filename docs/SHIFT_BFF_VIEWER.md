# SHIFT BFF Viewer

`tools/shift_bff_viewer.py` is an interactive Linux/Tk viewer for the decompilation project's current BFF/MEB/VHF resource boundary.

## Usage

```bash
python3 tools/shift_bff_viewer.py /path/to/BMW_M3_E36.bff --render-bff /path/to/RENDER.bff
```

When `RENDER.bff` is placed beside the vehicle archive, the UI attaches it automatically.

## Shader/material path

`MEB primitive → BMT/MTX → shader reference → RENDER.bff .fx → matching .fxo cache → DDS texture`

The viewer reads the recovered FX source and inspects an FXO cache program for D3D9 stage/CTAB/sampler metadata. Diffuse/specular DDS resources are decoded through the project's `texture_reference` implementation and sampled during the CPU preview.

The viewport lighting is deliberately a preview approximation. It uses real BMT scalar parameters such as fresnel/specular factors, but does not claim byte-for-byte execution of the original D3D9 FXO program.

## Controls

LMB drag rotates the model, the mouse wheel changes zoom, and `R` resets the camera. The material checkbox switches between shader-aware textured rendering and the faster geometry-only path.

## Dependencies

The project modules already provide BFF/XMem-LZX, MEB/VHF, BMT, DDS and shader parsing. The UI itself uses Python's standard `tkinter` only.
