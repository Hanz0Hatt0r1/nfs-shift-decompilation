# SHIFT track/path RTTI getter and vtable evidence

This note records a PE-level cross-check for the concrete vtables used by the
live-memory track/path analyzer. It also defines the current evidence boundary
for `AISpline`.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Recovery method

The retail polymorphic track/path classes use a compact virtual RTTI getter.
The second vtable slot points at a six-byte function of the form:

```text
B8 <descriptor-address little endian> C3
mov eax, <descriptor>
ret
```

For each reflected class descriptor, the verifier:

1. searches `.text` for that exact descriptor-returning getter;
2. searches aligned `.rdata` words for a pointer to the getter;
3. treats the preceding word as the first vtable slot;
4. requires that first slot to point back into `.text`;
5. compares the resulting vtable address with `KNOWN_VTABLES`.

This is implemented by
`tools/shift_live_dump/verify_track_path_source_anchors.py --exe SHIFT.exe`.

## Retail results

| Class | Reflection descriptor | RTTI getter | Dedicated vtable |
|---|---:|---:|---:|
| `AIPathInfo` | `0x00c0d5a4` | `0x006bc3e0` | `0x00afb150` |
| `AIPolylinePath` | `0x00c0d608` | `0x006cc3b0` | `0x00afc678` |
| `Knot` | `0x00c0d638` | `0x006c3000` | `0x00afbe28` |
| `AISpline` | `0x00c0d648` | not present | not established |
| `AISplineInfo` | `0x00c0d658` | not present | not established |
| `AISegmentPath` | `0x00c0d668` | `0x006ce680` | `0x00afc930` |
| `AIPolyPathNode` | `0x00c0d678` | `0x006c3950` | `0x00afbfa8` |
| `AIPathNode` | `0x00c0d688` | `0x006c3940` | `0x00afbf60` |

The six recovered concrete vtables, including the legacy `Path` profile's
retail `AIPathInfo` identity, match both the constructor/loader source anchors
and the analyzer constants.

## AISpline boundary

`FUN_00a84460` registers `AISpline` at descriptor `0x00c0d648`, and
`FUN_006ce2f0` reflects the container fields, but the retail PE does not
contain a dedicated `mov eax, 0x00c0d648; ret` RTTI getter. No vtable is
therefore assigned to `AISpline` merely by proximity to the neighboring
`Knot`, `AISegmentPath`, or node tables.

The live-memory analyzer consequently treats an `AISpline` hit as a
**structural owner candidate**. A reported link requires:

- the reflected `+0x10` pointer to equal a fully validated `Knot[]` array;
- the reflected `+0x18` count to equal the stable count prefix;
- the object's first word, pointer, count, length, and StepDist to remain
  consistent across every supplied snapshot;
- ambiguity to remain explicit through `owner_candidate_count` and
  `unique_owner`.

This boundary is deliberately stricter than assigning an unproven concrete
vtable.
