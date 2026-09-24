# Phase 124 — D3D9 shader runtime lifecycle

`SHIFT.D3D9ShaderLifecycleEvidence/1` records the source-backed shader state flush
around `FUN_0084f000`. The recovered wrapper applies cached pixel and vertex shader
objects through the D3D9 device, alongside declaration, stream and index state.

Observed source boundaries:

- `SetPixelShader` at vtable byte offset `0x1ac`;
- `SetVertexShader` at `0x170`;
- `SetVertexDeclaration` at `0x15c`;
- `SetStreamSource` at slot offset `0x190`;
- `SetIndices` at `0x1a0`.

The report deliberately remains source-static. A runtime capture is still required to
identify the exact shader objects and their relationship to a concrete BMW draw.

## Runtime extension

`SHIFT.D3D9RuntimeBindingEvidence/1` now accepts:

- `create_vertex_shader` / `create_pixel_shader` with exact shader bytes;
- `set_vertex_shader` / `set_pixel_shader` with object pointers.

When both stages are available in one frame, the capture derives the same
`SHIFT.ShaderPermutationIdentity/1` used by the offline material linker.

## Next

Correlate the captured shader permutation identity with the selected BMW material
slice, then require sampler/constants/interface parity before the first real material render is accepted as golden.

## Phase 125 integration

The runtime shader capture is now consumed by `SHIFT.BMWRuntimeShaderJoin/1`, which matches the captured VS/PS permutation identity and exact BMW resource identity against the offline material slice before checking sampler parity.
