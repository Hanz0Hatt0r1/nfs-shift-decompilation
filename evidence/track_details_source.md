# SHIFT TrackDetails: identity, exact size, reflection, and constructor evidence

This note records the retail `TrackDetails` class used by the track-list
configuration loader.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Class identity

`FUN_00a78170` registers `TrackDetails` at descriptor
`0x00bcce48`, parent `BPersistent` (`0x00bfa608`), with reflection
metadata `DAT_00b81eb0`.

The retail PE contains exactly one descriptor-returning getter:

```text
0049bce0  b8 48 ce bc 00    mov eax,0x00bcce48
0049bce5  c3                ret
```

The unique matching vtable is `0x00abb208`. Its first two entries are
`0x0049bf00` and `0x0049bce0`, tying the destructor and RTTI getter to
the same concrete table.

`FUN_0049b9c0` independently writes `PTR_FUN_00abb208` during
construction, so the class identity is supported by both source and PE
evidence.

## Exact allocation size

`FUN_0049ef40` enters a cold block at `0x00432446`. The PE bytes are:

```text
00432446  68 d4 01 00 00    push 0x1d4
0043244b  eb 0c             jmp  0x00432459
00432459  e9 ef ca 06 00    jmp  0x0049ef4d
```

The continuation calls `FUN_008868c0` and then `FUN_0049b9c0`.
Therefore the recovered retail allocation is exactly
`sizeof(TrackDetails) = 0x1d4`.

This also agrees with the last direct reflected field at `+0x1d0` and the
constructor write to that dword.

## Reflection builder

The corrected reflection extractor collapses the duplicated Ghidra functions
`thunk_FUN_00d67c70` and `FUN_00d67c70` into one canonical builder.
The pair contains 88 raw `FUN_0063a280` calls but only **44 semantic direct
fields**.

| Field | Offset | Type | Flags |
|---|---:|---:|---:|
| `ScenegraphFile` | `0x020` | `0x0` | 3 |
| `LeaderboardID` | `0x034` | `0xd` | 3 |
| `Length` | `0x038` | `0xd` | 3 |
| `XLASTID` | `0x03c` | `0x3` | 3 |
| `TrackName` | `0x040` | `0x0` | 3 |
| `ShortTrackName` | `0x044` | `0x0` | 3 |
| `Track_Location` | `0x048` | `0x0` | 3 |
| `Track_Variation` | `0x04c` | `0x0` | 3 |
| `Location` | `0x050` | `0x0` | 3 |
| `Track Type` | `0x0a0` | `0x0` | 3 |
| `Allowed Weather` | `0x110` | `0x0` | 3 |
| `Allowed TimeOfDay` | `0x114` | `0x0` | 3 |
| `Event Types` | `0x118` | `0x0` | 3 |
| `Track Description` | `0x11c` | `0x0` | 3 |
| `Year` | `0x124` | `0xd` | 3 |
| `Sun Angle(DEG)` | `0x128` | `0x1` | 3 |
| `Track Surface` | `0x12c` | `0x0` | 3 |
| `Track Group` | `0x130` | `0x0` | 3 |
| `PreRace Allowed (true/false)` | `0x134` | `0x2` | 3 |
| `Max AI participants` | `0x138` | `0x3` | 3 |
| `Class` | `0x13c` | `0x0` | 3 |
| `DirtSkidmarks` | `0x164` | `0x0` | 3 |
| `DrySkidmarks` | `0x168` | `0x0` | 3 |
| `GrassSkidmarks` | `0x16c` | `0x0` | 3 |
| `GravelSkidmarks` | `0x170` | `0x0` | 3 |
| `SandSkidmarks` | `0x174` | `0x0` | 3 |
| `GravelDustParticles` | `0x178` | `0x0` | 3 |
| `GravelChunkParticles` | `0x17c` | `0x0` | 3 |
| `GrassParticles` | `0x180` | `0x0` | 3 |
| `AutograssMaterial` | `0x184` | `0x0` | 3 |
| `AutograssDensities` | `0x188` | `0x0` | 3 |
| `AutograssHeights` | `0x18c` | `0x0` | 3 |
| `AI Grip` | `0x190` | `0xa` | 3 |
| `AI drift score min` | `0x198` | `0x3` | 3 |
| `AI drift score max` | `0x19c` | `0x3` | 3 |
| `Rolling Start` | `0x1a0` | `0x2` | 3 |
| `Setup group` | `0x1a4` | `0x0` | 3 |
| `ZoneName` | `0x1a8` | `0x0` | 3 |
| `Post race position` | `0x1ac` | `0x10` | 3 |
| `Post race orientation` | `0x1b8` | `0x10` | 3 |
| `Post race steering` | `0x1c4` | `0xa` | 3 |
| `Time Attack duration short` | `0x1c8` | `0x3` | 3 |
| `Time Attack duration medium` | `0x1cc` | `0x3` | 3 |
| `Time Attack duration long` | `0x1d0` | `0x3` | 3 |

The `Year` name is stored at `DAT_00abb1c4` in the PE rather than as a
literal; the reflection extractor resolves it from the executable.

## Constructor-visible defaults

`FUN_0049b9c0` directly establishes these reflected primitive/vector values:

| Field | Constructor value |
|---|---|
| `LeaderboardID` | `-1` |
| `Length` | `-1` |
| `Year` | `0` |
| `Sun Angle(DEG)` | `0.0f` |
| `PreRace Allowed (true/false)` | raw zero |
| `Max AI participants` | `15` |
| `AI Grip` | `1.0f` |
| `AI drift score min` | `400` |
| `AI drift score max` | `4000` |
| `Rolling Start` | raw zero |
| `Post race position` | `(0,0,0)` |
| `Post race orientation` | `(0,0,0)` |
| `Post race steering` | `0.0f` |
| short / medium / long Time Attack durations | `5 / 10 / 20` |

All 27 reflected type-code-0 members are passed through
`FUN_00533e70` during construction. This contract records that initializer
relationship without attempting to decode the dynamic string representation.

After initializing `Class +0x13c`, the constructor calls
`FUN_006329e0(..., &DAT_00aacbc0)`; the retail PE string at
`DAT_00aacbc0` is `"All"`. That assignment is kept separately from
primitive defaults.

`XLASTID +0x3c` is reflected but has no direct constructor write in
`FUN_0049b9c0`, so no default is invented for it.

## Destruction

Vtable slot 0 points to `FUN_0049bf00`, which calls cleanup body
`FUN_0049bd10`. The cleanup walks the high-offset string/container members
back toward the base object and finally calls `FUN_006383f0` for the
`BPersistent` teardown path.

This independently agrees with the registration parent.

## Runtime implementation

`src/track/track_details_runtime.py` exposes:

- descriptor / RTTI getter / vtable / constructor / destructor identity;
- exact `0x1d4` allocation size and allocation-site proof;
- all 44 de-duplicated direct reflected fields;
- direct primitive/vector constructor defaults;
- structural string-initializer evidence and the `Class="All"` assignment;
- decoding for the embedded numeric/vector fields whose byte interpretation is
  already supported by the recovered reflection/source usage.

## Boundary

The module does not decode the internal dynamic string/container objects or
infer the meaning of unreflected gaps. It also does not treat track-list
configuration values as live race-state fields. Those require their own
loader/consumer evidence.
