# Phase 200 — COLOR0/COLOR1 descriptor-to-Type bridge

Phase 200 joins the existing MEB descriptor-triple evidence with the D3D9 source evidence at the main color ABI bridge.

## Evidence chain

For the real BMW color properties the MEB descriptors are:

- `460` → `[4, 6, 0]`
- `461` → `[4, 6, 1]`

The recovered binary mesh loader consumes the 12-byte record as:

`[Type ordinal, Usage ordinal, Channel]`

The source-level D3D9 conversion path separately observes:

- declaration Type `4` enters the packed-color conversion path;
- the packed helper constructs `0xAARRGGBB`;
- on the original little-endian target that packed value has BGRA byte order in memory.

The integrated bridge now promotes the ABI only when both color descriptors are present and the source-side Type-4 path is observed. A partial or malformed descriptor set remains `not-proven`.

## Result

The resolved candidate is recorded as:

- D3D9 Type code: `4`
- D3D9 name: `D3DCOLOR`
- memory order: `BGRA`
- shader-visible order: `RGBA`

This resolves the **static MEB descriptor → D3D9 Type** boundary. It does not replace runtime same-instance capture evidence; a retail D3D9 draw is still required to prove that the selected declaration was used for the target draw.

## Regression coverage

`tests/test_d3d9_color_bridge_evidence.py` now covers:

1. promotion when both `[4,6,0]` and `[4,6,1]` descriptors are present;
2. fail-closed behavior when only one color descriptor is available.

The bridge exposes the full nested `SHIFT.MEBD3D9DescriptorTripleEvidence/1` result so downstream gates can audit exactly which evidence promoted the selection.
