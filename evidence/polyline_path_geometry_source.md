# SHIFT AIPolylinePath geometry: source and PE evidence

This note records the behavior of the retail `SHIFT.exe` path-geometry methods.
It extends the structural `AIPolylinePath`/`AIPolyPathNode` evidence used by
`tools/shift_live_dump/analyze_track_paths.py`. It does not claim that a
particular captured path instance belongs to a particular AIW resource.

## Source identity

- `SHIFT.exe`: SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`; PE32/i386, image base `0x00400000`, timestamp `2009-11-05 17:14:39` UTC.
- `SHIFT.exe.c`: SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.
- The function entry points in the decompilation agree with executable code at the same virtual addresses, verified with `objdump -d -Mintel`.

## Confirmed layout and defaults

`FUN_006cc200` (`SHIFT.exe.c:642122`, PE `0x006cc200`) resolves element `i` as
`path.array + i * 0x24`. `FUN_006cc730` allocates this count-prefixed array and
sets each element's vtable to `0x00afbfa8`. The geometry methods read these
fields from an element:

| Offset | Observed role |
|---:|---|
| `+0x10`, `+0x14` | 2D position `p` |
| `+0x18`, `+0x1c` | 2D direction/tangent `t` |
| `+0x20` | cumulative path distance `d` |

`FUN_006cc900` (`SHIFT.exe.c:642431`, PE `0x006cc900`) initializes the
`AIPolylinePath` count and array pointer to zero, node spacing at `+0x24` to
`2.0f`, and default width at `+0x28` to `6.0f`. The binary stores the values
`2.0f` at `0x00aa9af8` and `6.0f` at `0x00ac4240`. `FUN_006ccb20`
(`SHIFT.exe.c:642556`) names the reflected `length` (`+0x18`), `width`
(`+0x1c`), `cyclic` (`+0x20`), spacing (`+0x24`), default width (`+0x28`),
and node-array (`+0x14`) fields.

## Projection onto a segment

`FUN_006cc600` (`SHIFT.exe.c:642318`, PE `0x006cc600`) accepts a query point
`x` and consecutive nodes `a`, `b`. It computes and writes the **unclamped**
projection

```text
s = dot(x - a.position, a.tangent)
```

It selects the comparison point `q` as follows:

```text
if s < 0:                    q = a.position
elif a.distance + s > b.distance: q = b.position
else:                        q = a.position + s * a.tangent
```

The returned value is the Euclidean 2D distance `|q - x|`. PE instructions at
`0x006cc639-0x006cc64f` store `s` before either clamp branch;
`0x006cc675-0x006cc6a4` compares `a.distance + s` with `b.distance`; and
`0x006cc6f1-0x006cc720` computes the final square root. The upper clamp uses
the **next node's cumulative distance**, rather than measuring the geometric
length between the two positions.

`FUN_006cca90` (`SHIFT.exe.c:642517`, PE `0x006cca90`) checks pairs
`(node[i-1], node[i])` for `i = 1..count-1`, chooses the pair with the smallest
returned `|q - x|`, and returns `node[i-1].distance + s` for that pair. The
comparison is strict, so equal-distance pairs keep the earlier winner. The
pair loop does not include a closing last-to-first pair, even if the path is
marked cyclic. For fewer than two nodes, the function returns `0.0f`.

The reported path distance uses **unclamped `s`**. For example, with one
segment from `(0,0)` to `(10,0)`, tangent `(1,0)`, and distances `0` and `10`,
a query at `(-2,1)` compares against the clamped first endpoint but returns
path distance `-2`. A query at `(12,1)` compares against the last endpoint but
returns `12`. This follows directly from the separate output scalar in
`FUN_006cc600` and the addition at PE `0x006ccaf8-0x006ccb01`.

`FUN_006cc980` (`SHIFT.exe.c:642464`, PE `0x006cc980`) uses the same nearest
pair search. For the winning pair it writes the tangent at output `+0x10/+0x14`
and calculates a signed lateral component from `x - q` and that tangent. It
writes the signed component at output `+0x1c` and
`abs(signed_component) - path.width` at output `+0x18` (PE
`0x006cca21-0x006cca7c`). The decompiler types one of these stores as a
pointer; the PE instruction is a 32-bit float store.

## Distance-to-position behavior and limits

`FUN_006cc410` (`SHIFT.exe.c:642229`, PE `0x006cc410`) is the inverse-style
path query. For a noncyclic path, it returns the first position for negative
distance and the last position at or beyond the virtual length. With the
`cyclic` field set, it calls the floating-point remainder routine at
`0x0090328a` before walking node distances. Interior positions are built from
the previous node's position and tangent, using the surrounding cumulative
distance values. Exact behavior for malformed, zero-length, or nonmonotonic
node arrays has not been established.

## Use in the project

The current live-dump analyzer already exports node position, tangent and
cumulative distance to `aipolylinepath_nodes.csv`. A captured instance can now
be checked against these source-backed relations before joining it to AIW:

1. Verify node stride `0x24`, count and vtable as the analyzer already does.
2. Compare adjacent `distance` values and the position/tangent relation. Do
   not assume unit tangents or monotonic distances without captured evidence.
3. For a chosen query position, compare the projected nearest segment and
   reported path distance with a runtime observation. In particular, retain
   extrapolated values outside endpoints instead of clamping them silently.

The source proves the method calculations. It does not yet prove which
gameplay caller uses each method, or exact numeric parity on a retail frame.
