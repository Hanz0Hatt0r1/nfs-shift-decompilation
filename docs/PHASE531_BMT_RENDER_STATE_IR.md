# Phase 531 — typed BMT depth/alpha render-state IR

Phase 531 extends the material parser and neutral render path with source-backed
BMT depth/alpha state. It does **not** enable new Vulkan behavior yet.

## Retail source evidence

The retail material loader reads the following groups:

- `material/depthparams`
- `material/alphatestparams`
- `material/alphablendparams`
- `material/stencilparams`

The recovered field contracts are:

### depthparams

- `enabled`
- `function`
- `writeenabled`
- `bias`
- `slopebias`

### alphatestparams

- `enabled`
- `function`
- `value`

The retail loader divides the alpha-test value by `255.0` before use.

### alphablendparams

- `enabled`
- `sourceblend`
- `destblend`
- `blendop`
- `seperatealpha` (retail spelling)
- `alphasourceblend`
- `alphadestblend`
- `alphablendop`

### stencilparams

The source also exposes the stencil and two-sided CCW stencil fields. Phase 531
records that source contract but does not assign BLMY Resource IDs to fields
that have not yet been observed in the supplied BMT corpora.

## Stable real-BMT Resource IDs

The attached vehicle and Silverstone archives were scanned with the project
XMem/LZX decoder: 1,714 BMTs across 16 render BFFs.

Observed stable group IDs:

| Resource ID | BMT group | Occurrences |
|---:|---|---:|
| `3396092427 / 0xCA6C420B` | `depthparams` | 1,708 |
| `14911235 / 0x00E38703` | `alphablendparams` | 1,708 |
| `624549390 / 0x2539DE0E` | `alphatestparams` | 210 |

Observed stable field IDs:

| Resource ID | Field |
|---:|---|
| `3875134881 / 0xE6F9DDA1` | `enabled` |
| `2101237497 / 0x7D3E56F9` | `writeenabled` |
| `367069359 / 0x15E108AF` | `function` |
| `1773598955 / 0x69B6F8EB` | `value` |
| `3982835436 / 0xED653EEC` | `sourceblend` |
| `3277320897 / 0xC357F2C1` | `destblend` |
| `486381061 / 0x1CFD9605` | `blendop` |

No supplied corpus material exercised separate-alpha fields, depth bias fields
or stencil groups, so their Resource IDs remain unresolved rather than guessed.

## Retail enum order

The PE string tables establish exact engine enum indices.

Test function table at `0x00B173F8`:

```text
0 ETF_FAIL
1 ETF_LESS_THAN
2 ETF_EQUAL
3 ETF_LESS_THAN_OR_EQUAL
4 ETF_GREATER_THAN
5 ETF_NOT_EQUAL
6 ETF_GREATER_THAN_OR_EQUAL
7 ETF_PASS
```

Blend-factor table at `0x00B17418` has 11 entries, from `EBF_ZERO` through
`EBF_SOURCE_ALPHA_SATURATED`.

Blend-op table at `0x00B17444`:

```text
0 EBO_ADD
1 EBO_DEST_MINUS_SOURCE
2 EBO_MIN
3 EBO_MAX
4 EBO_SOURCE_MINUS_DEST
```

Stencil-op table at `0x00B17458` has eight entries, from
`ESO_NO_CHANGE` through `ESO_DECREMENT_WRAP`.

## IR output

`parse_bmt_material()` now emits:

```text
material.render_state
  format: SHIFT.BMTRenderState/1
  depth: SHIFT.BMTDepthState/1 | null
  alpha_test: SHIFT.BMTAlphaTestState/1 | null
  alpha_blend: SHIFT.BMTAlphaBlendState/1 | null
```

Known enum strings are accompanied by their exact `engine_enum_index`.
Unknown enum strings and unrecognized child Resource IDs remain explicit and
are not converted to plausible values.

The state is propagated through:

```text
BMT -> compile_material -> DrawPacket material -> StaticDraw
    -> RenderCommand submesh.render_state
```

## Execution boundary

Phase 530 remains the only new BMT render-state behavior executed by the native
Vulkan path: `cull`.

Depth, alpha-test, alpha-blend and stencil execution remain disabled until their
D3D9 values/default behavior and Vulkan translation are proven independently.
