# NFS SHIFT Decompilation — GitHub upload package

This archive contains project source code, tests, and documentation intended for manual upload to `Hanz0Hatt0r1/nfs-shift-decompilation`.

## Intentionally excluded
- Original game files: `.bff`, `.dds`, `.meb`, `.fxo`, `.exe`, track/vehicle archives, etc.
- Extracted game resources and binary fixtures derived from the game.
- Build artifacts (`build/`, `.so`, executables, CMake cache files).
- Large generated analysis reports.

## Main files
- `shift_importer.py` — current universal importer entry point.
- `shader_ir.py` — shader source/cache IR analysis.
- `shader_asm.py` — D3D9 shader token decoder + first-pass GLSL ES backend.
- `resource_formats.py`, `meb_format.py`, `csm_format.py` — resource format parsing.
- `native_ir/` — native IR/LZX source and tests, where available.
- `tests/` — source-level tests without original game binary fixtures.
- `docs/` — implementation/status notes.

`shift_importer_v3_reference.py` is kept only as a historical reference for the v3 importer; the active file is `shift_importer.py`.
