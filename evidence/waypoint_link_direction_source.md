# SHIFT WayPointBase link-direction pass evidence

This note records the source-backed post-link waypoint pass implemented by
`FUN_007ad8c0`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function and call sites

`FUN_007ad8c0` begins at retail PE `0x007ad8c0`.

Both recovered AIW load/rebuild paths call it across the complete logical
WayPointBase array:

- `FUN_0071e3ba`;
- `FUN_0071f099`.

In both paths, `FUN_00717b90` runs first to convert reflected Prev/Next/Branch
indices into runtime pointers. `FUN_007ad8c0` then consumes those runtime
links, so its output is a post-link derived field rather than serialized AIW
data.

## Inputs and output

The function reads:

| Role | Offset |
|---|---:|
| reflected `Position` | `+0x10/+0x14/+0x18` |
| runtime previous link | `+0x17c` |
| runtime next link | `+0x180` |

It writes one unreflected three-float vector to:

- `+0xf0/+0xf4/+0xf8`.

No `+0x18e` active-marker check is performed in this function or in the
surrounding per-record caller loop.

## Exact selection order

The recovered C is:

```text
next = self->link_180
left = self

if next == 0:
    right = self->link_17c
    next = self
    if right == 0:
        out_f0_f8 = (0, 0, -1)
        return

out_f0_f8 = Position(next) - Position(right_or_self)
```

Expressed by link case:

1. if `next +0x180` exists:
   `output = next.Position - self.Position`;
2. otherwise, if `previous +0x17c` exists:
   `output = self.Position - previous.Position`;
3. otherwise:
   `output = (0.0, 0.0, -1.0)`.

When both links exist, next has priority.

## Vector subtraction helper

`FUN_007ad8c0` delegates the non-default cases to `FUN_004a7870`.

That helper is directly recovered as:

```text
dst.x = a.x - b.x
dst.y = a.y - b.y
dst.z = a.z - b.z
```

so the direction formulas above do not depend on inferred vector-library
semantics.

## Runtime implementation

`src/ai/waypoint_link_direction_runtime.py` exposes:

- one-record source-equivalent direction derivation;
- one-record byte update of `+0xf0..+0xf8`;
- the observed full-array post-link pass;
- exact next/previous/default priority;
- bounded runtime-pointer validation for offline arrays.

Retail code dereferences the non-null runtime pointers directly. The offline
model rejects pointers outside the supplied contiguous WayPointBase array
instead of treating arbitrary process-memory reads as valid evidence.

## Evidence boundary

The dataflow and raw vector are proven, but downstream semantics for
`+0xf0..+0xf8` are not assigned a stronger gameplay name yet. Later geometry
consumers should establish whether this vector is normalized, re-scaled, or
used as a tangent/direction before the project promotes a semantic label.
