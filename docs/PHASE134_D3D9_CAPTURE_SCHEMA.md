# Phase 134 — D3D9 runtime capture schema

`SHIFT.D3D9RuntimeCaptureSchema/1` is the ingestion contract for external runtime
captures. It validates event names, frame identity, object pointers, declaration/
shader byte hex, stream geometry, indexed-draw numeric fields, and shader constant
vector lengths before the trace enters `SHIFT.D3D9RuntimeBindingEvidence/1`.

## Events

`create_vertex_declaration`, `set_vertex_declaration`, `set_stream_source`,
`set_indices`, `create_vertex_shader`, `create_pixel_shader`,
`set_vertex_shader`, `set_pixel_shader`, `set_vertex_shader_constant_f`,
`set_pixel_shader_constant_f`, and `draw_indexed_primitive`.

The schema validates shape only. It does not infer resource identities, Usage mappings,
shader permutations, or any rendering semantics.

## CLI

```bash
python shift_importer.py validate-d3d9-capture runtime.jsonl capture-schema.json
python shift_importer.py d3d9-runtime-trace runtime.jsonl runtime-evidence.json
```

`d3d9-runtime-trace` runs the same schema checks automatically through `load_events`.

## Capture requirements for the BMW golden path

For the first real BMW frame, capture at minimum:

- declaration creation + bind, including exact declaration bytes;
- VS/PS creation + bind, including exact shader bytes;
- stream source and index binding;
- `SetVertexShaderConstantF` / `SetPixelShaderConstantF` writes;
- `DrawIndexedPrimitive` range;
- resource SHA/path on the declaration bind.

This schema still does not authenticate the capture or prove that the trace belongs
to the original retail process; that remains an explicit evidence boundary.