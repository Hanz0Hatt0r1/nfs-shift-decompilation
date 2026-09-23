# Desktop reference renderer

`reference_renderer.py` is the first renderer executable that consumes only neutral mesh IR. It rasterizes indexed triangles with a deterministic orthographic MVP, optional per-vertex RGBA, depth testing and a PPM output path. It deliberately omits material/shader execution; its role is to be a geometry oracle before the GLES 3.1 backend.

Inputs can be the JSON emitted by `meb_format.mesh_to_jsonable()` after BFF decoding has already happened. The renderer itself has no dependency on `BFF`, `LZX`, `MEB` parsing or the original game runtime.

## Phase 35: RenderCommand execution

The reference renderer now consumes `SHIFT.RenderCommand/1` directly. It validates the final submission contract, verifies command vertex count/index ranges against the supplied neutral mesh, then reuses the deterministic geometry rasterizer. Shader source and material state remain validation inputs, not software shader execution.
