# Phase 127 — runtime shader constant capture

Phase 127 extends `SHIFT.D3D9RuntimeBindingEvidence/1` with floating-point shader
constant writes:

- `set_vertex_shader_constant_f`;
- `set_pixel_shader_constant_f`.

Each event records frame, stage, start register, Vector4 count, exact float values and
source line number from the capture. Invalid register/count/value shapes are explicit blockers.

`SHIFT.BMWRuntimeParity/1` can now compare captured final-register values against the
material uniform values with a small floating-point tolerance. `--require-constant-values`
turns missing capture values into a hard blocker, which is intended for the final golden gate.

Source evidence is also fixed in `SHIFT.D3D9ShaderConstantBindEvidence/1`: recovered
SHIFT wrappers dispatch vertex float constants at vtable offset `0x178` and pixel float
constants at `0x1b4`, matching the documented D3D9 API signatures for start register,
float4 data pointer and vector count.

## CLI

```bash
python shift_importer.py bmw-runtime-parity bmw-paint-slice.json runtime-evidence.json parity.json --usage-map usage-map.json --require-constant-values
```

## Next

Capture one concrete BMW frame, then use the parity output to drive the exact
`RenderCommand/1` through the desktop shader-reference renderer and record the first
real-material golden image.