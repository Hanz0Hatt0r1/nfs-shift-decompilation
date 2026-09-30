# SHIFT FUN_007ade70 horizontal perpendicular evidence

This note records the retail vector helper used by waypoint geometry consumers
to derive a normalized horizontal perpendicular from the WayPointBase vector at
`+0x13c..+0x144`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function identity and consumers

`FUN_007ade70` begins at retail PE `0x007ade70`.

Recovered source call sites include:

- `FUN_00759210`;
- `FUN_007adf30`.

The latter calls the helper for both a current WayPointBase and its runtime
`next +0x180` record during later local geometry calculations.

## Cross product

The function constructs the local constant vector:

`world_up = (0.0, 1.0, 0.0)`

and calls:

`FUN_0047bdb0(out, world_up, record + 0x13c)`.

`FUN_0047bdb0` is directly recovered as the ordinary three-dimensional cross
product:

```text
out.x = a.y*b.z - a.z*b.y
out.y = a.z*b.x - a.x*b.z
out.z = a.x*b.y - a.y*b.x
```

Therefore for source vector `(x,y,z)` the intermediate vector is exactly:

`(z, 0, -x)`.

The source vector's Y component does not affect this helper's output.

## Length and normalization threshold

The Ghidra C output hides the explicit argument to its square-root intrinsic,
but the retail x86 at `0x007adeaf..0x007adec8` shows the full calculation:

1. square each of the three cross-product components;
2. sum the squares;
3. store the squared length through a float local;
4. call the square-root helper;
5. store the length through a float local.

The comparison constant loaded at `0x007aded6` comes from retail
`.rdata 0x00aab4ec` with bits:

`0x3c23d70a = 0.01f`.

The branch condition is strict:

- if `length > 0.01f`, compute `1.0f / length` and multiply all three
  components;
- otherwise return the fixed vector `(1.0f, 0.0f, 0.0f)`.

The fallback includes equality with the threshold.

## Runtime implementation

`src/ai/waypoint_horizontal_perpendicular_runtime.py` exposes:

- direct source-equivalent `FUN_0047bdb0` cross-product;
- float-local length and square-root boundaries visible in retail x86;
- exact `0.01f` threshold bits;
- exact degenerate fallback;
- a record decoder reading `WayPointBase +0x13c..+0x144`.

The module intentionally returns the vector rather than writing it into an
invented WayPointBase field: `FUN_007ade70` itself writes to a caller-provided
output buffer.

## Evidence boundary

The helper's math is proven independently of the larger geometry pass. The
record field at `+0x13c..+0x144` remains structural in this module until its
producer in `FUN_007ada70` is reconstructed and verified separately.
