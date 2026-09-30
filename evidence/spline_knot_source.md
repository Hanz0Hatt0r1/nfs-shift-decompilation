# SHIFT AISpline Knot arrays: source and PE evidence

The supplied retail executable has an `AISpline` class with a reflected
count-prefixed array of `Knot` elements. This note records the layout used
by the live-memory track analyzer.

## Source identity

The evidence is from `SHIFT.exe` SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
and `SHIFT.exe.c` SHA-256
`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

## Container and array

`FUN_00a84460` (`SHIFT.exe.c:1415189`) registers `AISpline`.
`FUN_00a843d0` (`SHIFT.exe.c:1415170`) registers `Knot`; the
registration's string is at PE address `0x00afc8dc`. The `AISpline`
reflection builder `FUN_006ce2f0` (`SHIFT.exe.c:643685`) gives:

| AISpline offset | Reflected name | Type |
|---:|---|---|
| `+0x10` | knot array | array pointer |
| `+0x14` | length | float |
| `+0x18` | knot count | integer |
| `+0x1c` | StepDist | float |

`FUN_006cdf70` (`SHIFT.exe.c:643478`, PE `0x006cdf70`) writes the
serialized element count to `AISpline+0x18`, allocates
`count * 0x48 + 4` bytes, writes the count as a four-byte prefix, and
stores the first element address at `AISpline+0x10`. It initializes each
element with vtable `0x00afbe28` and advances by `0x48`. The PE
instruction at `0x006ce034` writes that exact vtable. The array destructor
`FUN_006cdcd0` also advances by `0x48`.

## Knot fields

`FUN_006cdb30` (`SHIFT.exe.c:643320`, PE `0x006cdb30`) reflects:

| Knot offset | Reflected name | Type |
|---:|---|---|
| `+0x10` | Pos | 3D vector |
| `+0x1c` | ConstantA | 3D vector |
| `+0x28` | ConstantB | 3D vector |
| `+0x34` | ConstantC | 3D vector |
| `+0x40` | Length | float |
| `+0x44` | InvLength | float |

The names at PE `0x00afc88c-0x00afc8bf` and reflection calls show
these offsets; `+0x10` and `+0x1c` are also visible in PE calls at
`0x006cdb63` and `0x006cdba5`.

## Analyzer boundary

`analyze_track_paths.py` identifies `Knot` elements using the concrete
vtable and finite reflected fields. It groups only complete 0x48-stride
sequences whose count prefix agrees across all supplied snapshots and exports
the reference snapshot to `aispline_knot_arrays.csv` and
`aispline_knots.csv`.

The reflected `AISpline+0x10` pointer and `+0x18` count provide an owner
test. The analyzer reports `aispline_knot_links.csv` only when a candidate
object points exactly to a validated array, its count equals the array
prefix, its first word points into mapped game code, and the header/pointer/count
remain consistent across every snapshot.

The PE-level RTTI scan in
[track_path_rtti_vtables.md](track_path_rtti_vtables.md) establishes the
important negative boundary: unlike `Knot`, `AISegmentPath`,
`AIPolylinePath`, `AIPathNode`, and `AIPolyPathNode`, retail
`AISpline` has no dedicated descriptor-returning virtual RTTI getter, so no
concrete AISpline vtable is asserted. These remain structural owner candidates.
`owner_candidate_count` exposes ambiguity and `unique_owner` is true only
when exactly one surviving structural object owns a validated array.

The currently available reduced track captures contain no matching
`AISpline` or `Knot` objects; they cannot confirm live retail ownership.
