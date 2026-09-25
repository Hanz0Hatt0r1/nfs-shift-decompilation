# Phase 202 — evidence-aware COLOR vertex layout

Phase 202 carries a verified `SHIFT.MEBD3D9ColorBridgeEvidence/1` report into `SHIFT.VertexLayout/1` when the BMW render slice is built.

## Behavior

The default layout remains conservative: MEB properties 460/461 are still reported as `ambiguous` when no color evidence is supplied.

When a verified bridge is explicitly supplied, the layout records:

- D3D9 type `D3DCOLOR` (Type 4);
- BGRA memory order;
- RGBA shader order;
- Android candidate `UINT8x4_BGRA`;
- `abi_status = proven`.

The evidence is passed explicitly from `bmw_real_material_slice.py` through the new `color_abi_report` input. No global environment switch or implicit inference is used.

## Boundary

This changes only the **static vertex-layout contract**. It does not claim that a retail runtime declaration instance used Type 4 for the target draw. That remains part of the external D3D9 same-instance gate.

## Regression coverage

`tests/test_vertex_layout.py` verifies both sides of the boundary: the default ambiguous state and the verified evidence-aware state.
