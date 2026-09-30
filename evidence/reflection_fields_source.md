# SHIFT reflected field extraction evidence

This note records the repository-wide pass over recovered reflection metadata
builder calls rooted at `FUN_0063a280`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Extractor

`tools/shift_live_dump/extract_shift_reflection_fields.py` joins each
`FUN_0063a280(&DAT_<metadata>, ...)` call to the class registry recovered by
`extract_shift_rtti_registry.py`. For each call it records:

- owning class and descriptor;
- reflection metadata symbol and builder function;
- field name and its original source token;
- reflection type code and original type expression;
- byte offset and original offset expression;
- reflection flags and original flags expression.

Names passed through `DAT_...` or `PTR_s_...` symbols are resolved from the
retail PE when available. Generated names and computed offsets are kept as
expressions rather than being guessed.

## Retail corpus summary

Running the extractor on the supplied retail source/executable pair produced:

| Metric | Count |
|---|---:|
| reflection metadata calls | 3122 |
| calls mapped back to a registered class | 3122 |
| resolved field names | 3109 |
| static reflection type codes | 3122 |
| static byte offsets | 3115 |
| static flags | 3122 |

The 13 unresolved field names are generated or indirect at runtime rather than
simple source/PE string constants. Seven calls use computed offsets in loops;
the extractor keeps their offset expressions instead of inventing constants.

The two observed top-level reflection flag values are:

| Flags | Calls |
|---:|---:|
| `2` | 929 |
| `3` | 2193 |

The most common recovered type codes are `10`, `0`, `3`, `1`, `6`,
`2`, and `13`. The extractor deliberately reports numeric codes without
assigning semantic type names unless separate source evidence establishes those
meanings.

## Track/path slice

The automated field counts for the current track/path classes are:

| Class | Reflected fields |
|---|---:|
| `AIPathInfo` | 8 |
| `AIArea` | 23 |
| `AISegmentPath` | 10 |
| `AIPathNode` | 7 |
| `AIPolylinePath` | 7 |
| `AIPolyPathNode` | 3 |
| `Knot` | 6 |
| `AISpline` | 4 |
| `AISplineInfo` | 4 |

Representative layouts reproduced automatically include:

- `AIPathInfo`: `tangent +0x10`, `outside +0x18`,
  `centreDist +0x1c`, `StartNode +0x20`, and the four byte-sized path
  flags at `+0x24..+0x27`;
- `AISegmentPath`: node count `+0x10`, track side `+0x14`, node array
  `+0x18`, length `+0x1c`, cyclic/narrow flags, spacing/path distance,
  current node, and edge step through `+0x34`;
- `AIPolylinePath`: count `+0x10`, node array `+0x14`, length
  `+0x18`, width `+0x1c`, cyclic `+0x20`, spacing `+0x24`, and
  default width `+0x28`;
- `Knot`: `Pos +0x10`, `ConstantA/B/C +0x1c/+0x28/+0x34`,
  `Length +0x40`, and `InvLength +0x44`;
- `AISpline`: knot array `+0x10`, length `+0x14`, knot count
  `+0x18`, and `StepDist +0x1c`.

This independently reproduces the manually curated offsets currently used by
the track-path analyzer and provides a reusable source for future subsystem
layout recovery.

## Scope

A reflected field is strong layout evidence, not automatically a complete
runtime semantic interpretation. Arrays, pointers, enums, ownership and update
behavior still require constructor, factory, call-site or live-capture evidence.
