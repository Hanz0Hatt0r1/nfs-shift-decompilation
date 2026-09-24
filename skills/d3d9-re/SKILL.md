---
name: d3d9-re
description: >-
  Reverse-engineer the SHIFT Direct3D 9 declaration, stream, shader and binding ABI
  with explicit static/runtime evidence layers. Use for D3D9 vtable calls, declaration
  records, Type/Usage, stream/draw capture, shader identity, MEB descriptor bridges,
  material contracts and golden-render gates.
---
# D3D9 reverse-engineering workflow

Keep static source/evidence separate from runtime capture. Same-instance claims require
an explicit resource/frame/object correlation.

## BMW asset contract

`bmw_m3_paint_asset_contract.py` locks the exact M3 golden MEB identity, paint primitive
ranges and manifest provenance before material/shader/runtime joins.