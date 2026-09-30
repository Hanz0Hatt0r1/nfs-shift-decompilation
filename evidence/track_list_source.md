# SHIFT TrackList: singleton, loader, taxonomy and lookup evidence

This note records the retail `TrackList` owner that loads and indexes
`TrackDetails` records.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Concrete class identity

`FUN_00a78200` registers `TrackList` at descriptor
`0x00bcd48c`, parent `BPersistent` (`0x00bfa608`), with reflection
metadata `DAT_00b81ee4`.

The retail PE has one descriptor-returning getter:

```text
0049eea0  b8 8c d4 bc 00    mov eax,0x00bcd48c
0049eea5  c3                ret
```

The unique aligned vtable candidate is `0x00abb4d0`. Its first two entries
are `0x0049ef10` and `0x0049eea0`, so slot 0 is the destructor and slot 1
is the RTTI getter.

The recovered constructor `FUN_00d6aee0` (also emitted by Ghidra as
`thunk_FUN_00d6aee0`) writes the same `PTR_FUN_00abb4d0` table.

## Singleton and exact size

`FUN_0049f940` is the lazy singleton initializer. It checks pointer global
`DAT_00bcd484`; when null it calls:

```text
FUN_008868c0(0xe4)
  -> FUN_00d6aee0(...)
  -> DAT_00bcd484
```

Therefore the retail singleton allocation establishes exact
`sizeof(TrackList) = 0xe4`.

The shutdown path calls the object destructor through the singleton pointer and
then clears `DAT_00bcd484`.

## Direct reflected fields

After Ghidra thunk/non-thunk deduplication, canonical builder
`FUN_00d6a940` emits four direct fields:

| Field | Offset | Type | Flags |
|---|---:|---:|---:|
| `Era Names` | `0xd4` | 0 | 3 |
| `Track Types` | `0xd8` | 0 | 3 |
| `Track Locations` | `0xdc` | 0 | 3 |
| `Track Groups` | `0xe0` | 0 | 3 |

The constructor initializes all four dynamic strings, loads the track corpus,
then replaces an empty value with `"All"`.

`thunk_FUN_00d6ad30` splits each string on comma and inserts tokens via
`FUN_0049bf70` into these constructor-owned containers:

| Reflected taxonomy | Token container |
|---|---:|
| `Track Types` | `+0x40` |
| `Track Locations` | `+0x64` |
| `Era Names` | `+0x88` |
| `Track Groups` | `+0xb0` |

The internal node ABI of those containers is not named by this evidence.

## TrackDetails ownership and load flow

The main owner container begins at `TrackList +0x10`.

The constructor first tries:

```text
tracks/_Data/tracklist.lst
  -> FUN_0049f2c0
```

If that load returns false it falls back to:

```text
FUN_0049f010("Tracks")
  -> recursive FindFirstFileA / FindNextFileA scan
  -> case-insensitive .trd suffix
```

Both routes eventually call `FUN_0049ef40` for each TrackDetails request.
That path:

1. allocates the previously proven `0x1d4` `TrackDetails`;
2. runs `FUN_0049b9c0`;
3. loads its properties through `FUN_0049c050`;
4. inserts successful objects into `TrackList +0x10` with `FUN_004f5e60`;
5. destroys failed objects instead of inserting them.

`FUN_0049edb0` iterates the same `+0x10` owner container and invokes the
virtual destructor for every surviving TrackDetails before tearing down the
remaining TrackList containers and finally calling the `BPersistent`
destructor path.

This establishes ownership rather than a loose pointer index.

## tracklist.lst records

`FUN_0049f2c0` loads the list as text and processes newline-terminated
records. The observed retail grammar assumes CRLF: the byte before LF is
removed before the request is sent to `FUN_0049ef40`.

When a record contains `@`, the text before and after the first separator is
concatenated before loading. The runtime helper
`parse_tracklist_requests()` reproduces that contract for CRLF input and
fails closed on LF-only or unterminated records rather than silently dropping a
filename character.

## TrackDetails derived taxonomy

After `FUN_0049c050` loads one TrackDetails, it builds unreflected token
containers used by TrackList/gameplay consumers:

| Source | Derived container |
|---|---:|
| `Year` | `+0x58` |
| `Track Type +0xa0` | `+0x7c` |
| `Allowed Weather +0x110` | `+0xa4` |
| `Allowed TimeOfDay +0x114` | `+0xc8` |
| `Event Types +0x118` | `+0xec` |
| `Class +0x13c` | `+0x140` |

The year bucket inserted at `+0x58` is selected exactly as:

- `0` -> `UNSET`
- below 1901 -> `50BC`
- 1901..1969 -> `1930-1969`
- 1970..1999 -> `1970-1999`
- 2000..2019 -> `2000-2019`
- 2020..2100 -> `2020-2100`
- 2101+ -> `ERROR`

The labels above intentionally reproduce the retail strings even where the
first range label is broader/narrower than its numeric threshold suggests.

## Lookups and Class matching

`FUN_0049ed00` walks the owned TrackDetails container and performs a
case-insensitive lookup against `TrackDetails +0x10`. The TrackDetails loader
chain now identifies that field independently as the lower-case
basename-without-extension of the resolved reflected `ScenegraphFile`, i.e.
the **scenegraph stem**. Empty queries are rejected.

A second consumer, `thunk_FUN_00406a90`, performs the same scenegraph-stem
lookup and returns the source-path hash at `TrackDetails +0x120`.

The TrackDetails vtable slot at `+0x10` points to `FUN_0049bcf0`. That
accessor returns reflected `TrackName +0x40` when non-empty and otherwise
returns the scenegraph stem at `+0x10`. This provides an independent
preferred-name/fallback consumer for the recovered field identity.

`thunk_FUN_00480cb0` returns the first TrackDetails owner entry when the
container is non-empty.

`thunk_FUN_00d6abc0` returns the first TrackDetails for which
`thunk_FUN_00d696c0` accepts a Class filter. The filter rules are recovered
directly:

- a TrackDetails reflected `Class` equal to `All` matches every query;
- a query equal to `All` matches every TrackDetails;
- ordinary queries match case-insensitively against tokens in the derived
  `+0x140` Class container;
- a query beginning with `!` matches only when the remainder is absent from
  that Class token container.

## Runtime implementation

`src/track/track_list_runtime.py` reuses the already-source-backed helpers in
`track_details_load_runtime.py` for comma tokenization, year bucketing and
`.trd` admission instead of duplicating those semantics. It exposes:

- singleton pointer, exact `0xe4` size, descriptor/getter/vtable and lifecycle;
- all four direct reflected taxonomy strings;
- main TrackDetails owner and taxonomy-container offsets;
- source-equivalent CSV token splitting and empty-to-`All` constructor
  fallback;
- the year-to-era bucket;
- Class include/exclude matching;
- case-insensitive scenegraph-stem matching plus source-hash lookup identity;
- `TrackName` → scenegraph-stem preferred-name fallback;
- CRLF `tracklist.lst` request parsing;
- case-insensitive `.trd` extension admission.

## Boundary

The internal ordered/tree node ABI is intentionally not reconstructed here.
The contract now proves the `TrackDetails +0x10` scenegraph-stem identity,
ownership, loading, filtering and lookup control flow, while higher-level
event-selection policy remains outside this layer.
