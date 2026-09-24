# Phase 117 — runtime D3D9 capture bridge

The next evidence gate after the 1.02 corpus bridge is a **runtime declaration
instance for the same mesh/resource**. Phase 117 adds the project-side consumer for
that evidence without requiring the original game runtime inside the renderer.

## New contract

`SHIFT.D3D9RuntimeBindingEvidence/1` is produced from JSONL runtime capture events.
It records:

- declaration pointer creation and exact declaration bytes;
- `SetVertexDeclaration` binding per frame;
- `SetStreamSource` and index-buffer bindings;
- indexed draw parameters;
- optional MEB resource SHA/path identity;
- optional explicit MEB Usage-ordinal → D3D9 Usage-byte mapping.

The tool joins those records but does not authenticate the capture source. It also
never guesses a missing Usage mapping.

## Capture event format

```json
{"event":"create_vertex_declaration","frame":7,"declaration_ptr":"0x1234","bytes_hex":"..."}
{"event":"set_vertex_declaration","frame":7,"declaration_ptr":"0x1234","resource_sha256":"...","resource_path":"vehicles/bmw/body.meb"}
{"event":"set_stream_source","frame":7,"stream":0,"vertex_buffer_ptr":"0x7777","offset_in_bytes":0,"stride":32}
{"event":"set_indices","frame":7,"index_buffer_ptr":"0x8888"}
{"event":"draw_indexed_primitive","frame":7,"primitive_count":94,"start_index":0,"base_vertex_index":0}
```

## CLI

```bash
python d3d9_runtime_trace.py capture.jsonl runtime-evidence.json
python d3d9_runtime_trace.py capture.jsonl runtime-evidence.json \
  --meb-resource body-resource.json \
  --usage-map usage-ordinal-map.json
```

The usage map is deliberately external because the recovered source exposes the
ordinal table and its `Colour = 6` entry, but the project must not invent the numeric
D3D9 Usage byte without evidence.

## Acceptance gate

For a same-instance bridge, require:

1. captured declaration pointer decodes as `SHIFT.D3D9DeclarationInstanceEvidence/1`;
2. `SetVertexDeclaration` references the same pointer;
3. the capture identifies the same MEB resource by SHA-256 or exact normalized path;
4. the declaration record matches the MEB descriptor triple after an explicit Usage
   ordinal map is supplied.

Until all four are present, the runtime proof remains `not-proven`/`partial`.


## Shader events (Phase 124)

The same JSONL trace accepts `create_vertex_shader`, `create_pixel_shader`, `set_vertex_shader` and `set_pixel_shader`. Creation events may carry the complete D3D9 bytecode in `bytes_hex`; when both stages are bound in one frame, the bridge emits `shader_permutation_identity` using `SHIFT.ShaderPermutationIdentity/1`.
