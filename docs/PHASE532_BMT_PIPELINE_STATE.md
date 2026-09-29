# Phase 532 — source-backed BMT pipeline state

Phase 532 turns the typed BMT render-state IR from Phase 531 into an executable
native Vulkan subset. The implementation stays fail-closed where D3D9 behavior
cannot be represented faithfully yet.

## Retail numeric evidence

The retail executable exposes exact engine-enum → D3D9 lookup tables:

| State | Retail function | Table | Mapping |
|---|---|---|---|
| compare/test | `FUN_0083f630` | `0x00b8ecf4` | engine 0..7 → D3D 1..8 |
| blend factor | `FUN_0083f650` | `0x00b8ed38` | engine 0..10 → D3D 1..11 |
| blend op | `FUN_0083f670` | `0x00b8eda8` | `[1,3,4,5,2]` |
| stencil op | `FUN_0083f690` | `0x00b8edd4` | engine 0..7 → D3D 1..8 |

The recovered constructor `FUN_00839d70` supplies the defaults before BMT
overrides:

- depth test enabled;
- depth write enabled;
- depth compare `ETF_LESS_THAN_OR_EQUAL`;
- alpha test disabled, compare `ETF_PASS`, reference 0;
- alpha blend disabled, source `EBF_ONE`, destination `EBF_ZERO`, op
  `EBO_ADD`;
- separate alpha disabled;
- stencil disabled with full masks, compare `ETF_PASS` and no-change ops.

## Vulkan translation

`SHIFT.MaterialPipelineState/1` carries explicit Vulkan-ready fields for:

- cull mode from Phase 530;
- depth-test enable;
- depth-write enable;
- depth compare operation;
- blend enable;
- source/destination color and alpha blend factors;
- color and alpha blend operations.

The bundle sidecar is consumed independently by both:

- `native_vulkan/shift_vulkan_bundle_execute`;
- `native_runtime/shift_native_runtime` in single- and multi-draw modes.

Legacy `SHIFT.MaterialCullState/1` sidecars remain readable and keep the
previous depth/blend defaults.

## Fail-closed boundary

Enabled D3D9 alpha test is **not** emulated as a Vulkan fixed-function state.
Vulkan has no equivalent fixed alpha-test stage, so a material with
`alphatestparams/enabled=true` is blocked until the fragment shader path can
perform the evidence-backed discard/compare operation.

Likewise, unresolved depth-bias, separate-alpha and stencil Resource IDs are
not guessed. If such an unknown nested BMT state group or state field appears,
native admission is blocked.

This makes the executable subset:

```text
BMT cull + depth + ordinary alpha blend
  -> exact engine enum index
  -> exact retail D3D9 value
  -> lossless Vulkan pipeline state
```

while alpha-test/bias/stencil remain explicit future work.
