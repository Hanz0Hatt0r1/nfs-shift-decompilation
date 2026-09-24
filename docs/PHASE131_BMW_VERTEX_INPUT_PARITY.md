# Phase 131 — BMW vertex-input parity

`SHIFT.BMWVertexInputParity/1` closes the semantic vertex-input join between the
runtime D3D9 declaration and the target `VertexLayout/1` + shader `DCL` contract.

## Checks

- shader input `(usage,index)` must exist in the MEB-derived target layout;
- the target property must have an evidence-backed D3D9 Type code;
- when its MEB Usage ordinal is known, the supplied Usage map must resolve it to
  the runtime D3D9 Usage byte and the captured declaration record must match;
- `UsageIndex` must match;
- shader register `vN` must match the target attribute location when both are explicit.

Physical `Stream/Offset` is reported but not falsely equated with the target repacked
interleaved buffer: `RenderCommand/1` deliberately repacks MEB payloads, so those
physical layouts remain `not-comparable-by-design` until a source/runtime capture
proves the original buffer packing.

The current golden gate consumes this semantic parity report when an explicit Usage
map is supplied.

## CLI

```bash
python shift_importer.py bmw-vertex-input-parity bmw-paint-slice.json runtime-evidence.json vertex-parity.json --usage-map usage-map.json
```

## Next

The next blocker is the first real runtime capture itself. Once the runtime
declaration/shader/constants/draw range all join to the exact BMW paint primitive,
`bmw-runtime-golden-gate` can hand the accepted `RenderCommand` to the desktop
reference renderer for the first real-material golden image.