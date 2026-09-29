# Phase 532 — execute proven BMT depth/blend state in Vulkan

Phase 532 turns the Phase 531 typed BMT render-state IR into native Vulkan
pipeline state for the subset whose retail D3D9 semantics are statically
recoverable.

## Proven retail mappings

The retail material-state constructor `FUN_00839d70` provides these defaults:

- depth test enabled;
- depth writes enabled;
- depth compare = `ETF_LESS_THAN_OR_EQUAL`;
- alpha test disabled;
- alpha blend disabled;
- source blend = `EBF_ONE`;
- destination blend = `EBF_ZERO`;
- blend operation = `EBO_ADD`.

The retail conversion paths `FUN_0083f920`, `FUN_0083f960` and
`FUN_0083f9c0` map the engine compare/blend enums through D3D9 lookup tables.
Phase 532 preserves those D3D9 values in `SHIFT.MaterialPipelineState/1` and
also emits the corresponding Vulkan enums.

## Native execution

Every atomic BMW Vulkan bundle now writes `pipeline_state.json` with:

- per-draw cull mode;
- depth-test enable;
- depth-write enable;
- depth compare operation;
- color blend enable;
- color source/destination factors and operation;
- alpha source/destination factors and operation.

Both native Vulkan consumers read the same sidecar and configure
`VkPipelineRasterizationStateCreateInfo`,
`VkPipelineDepthStencilStateCreateInfo` and
`VkPipelineColorBlendAttachmentState` independently for each draw.

The Phase 530 cull-only sidecar remains accepted for compatibility with older
prepared bundles.

## Fail-closed boundary

The following remain blocked rather than approximated:

- enabled alpha test, because D3D9 fixed-function alpha test requires an
  equivalent shader discard path in Vulkan;
- any unmapped BMT state fields;
- non-zero depth bias/slope bias until their exact BMT Resource IDs and runtime
  application are proven;
- unsupported or unknown compare/blend enum values.

This phase does not claim stencil, color-write-mask, MSAA/antialias or other
unobserved render state.
