# Phase 530 — source-backed BMW BMT cull state

Phase 530 closes the first real per-draw raster-state difference in the native
BMW material path: the material `cull` enum.

## Retail static evidence

The supplied retail `SHIFT.exe` / decompilation provides both halves of the
mapping.

The material loader compares the BMT `cull` string against the three-entry
table at `0x00b173e0`. The pointer order is:

| Engine index | String |
|---:|---|
| 0 | `EBFCT_NONE` |
| 1 | `EBFCT_CLOCKWISE` |
| 2 | `EBFCT_ANTICLOCKWISE` |

`FUN_0083f610(index)` reads a DWORD from `0x00b8ecd8 + index*4`. The retail
table bytes decode to:

```text
index 0 -> 1
index 1 -> 2
index 2 -> 3
```

Those are the D3D9 `D3DCULL` values:

| BMT enum | D3D9 |
|---|---|
| `EBFCT_NONE` | `D3DCULL_NONE = 1` |
| `EBFCT_CLOCKWISE` | `D3DCULL_CW = 2` |
| `EBFCT_ANTICLOCKWISE` | `D3DCULL_CCW = 3` |

## Vulkan mapping

Both native Vulkan consumers use
`VK_FRONT_FACE_COUNTER_CLOCKWISE`. Therefore:

| D3D9 behavior | Vulkan cull mode |
|---|---|
| none | `VK_CULL_MODE_NONE` |
| cull clockwise triangles | `VK_CULL_MODE_BACK_BIT` |
| cull counter-clockwise triangles | `VK_CULL_MODE_FRONT_BIT` |

The mapping is emitted as `SHIFT.MaterialCullState/1` in
`pipeline_state.json` for every atomic BMW Vulkan bundle.

Unknown supplied BMT cull values fail closed. Synthetic/legacy commands that do
not supply a cull value are explicitly marked `not-supplied` and retain the
previous no-cull material behavior without claiming retail evidence.

## Pipeline propagation

```text
BMT material.render_state.cull
  -> RenderCommand submesh.render_state.cull
  -> SHIFT.MaterialCullState/1
  -> pipeline_state.json
  -> direct Vulkan executor / native multi-draw runtime
  -> VkPipelineRasterizationStateCreateInfo.cullMode
```

Each Phase 529 primitive slice can therefore carry its own independently proven
cull mode into the Phase 527 bundle set and Phase 526 native multi-draw frame.

## Boundary

Phase 530 does not infer blend, depth-write, depth-compare, alpha-test or
color-write behavior from the BMT cull enum. Those states remain separate
evidence tasks.
