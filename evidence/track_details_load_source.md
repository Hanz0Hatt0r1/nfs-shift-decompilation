# SHIFT TrackDetails load and discovery lifecycle

This note extends the structural `TrackDetails` contract with the post-property
load behavior recovered from `FUN_0049c050`, its allocation wrapper, and the
recursive `.trd` discovery path.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

The class identity, exact `0x1d4` allocation and 44-field direct reflection
layout are documented separately in
[track_details_source.md](track_details_source.md).

## Two-stage load gate

`FUN_0049c050` first constructs a property-load context and invokes two
virtual stages:

- vtable offset `+0x20`: load the requested properties;
- vtable offset `+0x24`: require the resulting data stage to be available.

The source contains separate failure text for the two gates:

- `Failed to load the properties for: `
- `Failed to load the data for: `

Post-load normalization occurs only after both gates succeed.

## Comma-token collections

Five reflected source strings are split on commas and copied into internal
collection-like members through `FUN_0049bf70`:

| Reflected source | Source offset | Destination offset |
|---|---:|---:|
| Track Type | `+0xa0` | `+0x7c` |
| Allowed Weather | `+0x110` | `+0xa4` |
| Allowed TimeOfDay | `+0x114` | `+0xc8` |
| Event Types | `+0x118` | `+0xec` |
| Class | `+0x13c` | `+0x140` |

The split loop is explicit:

1. find the next comma;
2. copy the prefix;
3. append it only when non-empty;
4. remove the consumed prefix plus comma;
5. after the loop, append the final remainder unconditionally.

Consequences preserved by the runtime helper include:

- `A,B,C` → `A`, `B`, `C`;
- `A,,B` → `A`, `B`;
- a trailing comma leaves an empty final entry.

The destination members are kept as opaque token collections. Their concrete
container implementation is not inferred from `FUN_0049bf70` in this pass.

## Year bucket

The reflected `Year` field at `+0x124` is converted to one string and
appended to the internal member at `+0x58`:

| Condition | Stored value |
|---|---|
| year == 0 | `UNSET` |
| year < 1901 | `50BC` |
| year < 1970 | `1930-1969` |
| year < 2000 | `1970-1999` |
| year < 2020 | `2000-2019` |
| year < 2101 | `2020-2100` |
| otherwise | `ERROR` |

The labels are recorded exactly as found in retail source; no attempt is made
to “correct” the `1930-1969` label for the 1901–1929 numerical range.

## Source-path normalization and hash

Before finishing, `FUN_0049c050` copies the source path, calls
`FUN_00631a10` (lower-case conversion), replaces `/` with `\` through
`FUN_00631410`, and passes the resulting byte string to:

```text
FUN_0063ad50(object + 0x120, normalized_path, length, 0, 1)
```

`FUN_0063ad50` is now reconstructed with source/PE-equivalent 32-bit
arithmetic for the case-sensitive raw-byte path. The retail PE proves signed
byte loads through `MOVSX` and big-endian-style four-byte accumulation. For
the normalized ASCII path `tracks\\silverstone\\era3.trd`, the recovered
hash is `0x0a1a5c1e`. See
[SHIFT hash32 evidence](shift_hash32_source.md).

## Allocation and ownership handoff

`FUN_0049ef4d` allocates and constructs one `TrackDetails`, then invokes
`FUN_0049c050`.

- On failure it logs `Tracklist: Failed to load: ` and invokes the new
  object's virtual destructor.
- On success it inserts the pointer into the caller-owned member at `+0x10`
  through `FUN_004f5e60`.

The caller type behind that `+0x10` collection is not assigned here merely
from the log string.

## Recursive .trd discovery

`FUN_0049f010` walks a supplied directory using `FindFirstFileA` /
`FindNextFileA`:

- `.` and `..` are skipped;
- subdirectories are visited recursively;
- regular files are accepted only when their final four bytes match `.trd`
  case-insensitively;
- accepted paths are forwarded into the allocation/load wrapper.

This proves a recursive retail `TrackDetails` discovery path independent of
higher-level track selection.

## Runtime implementation

`src/track/track_details_load_runtime.py` exposes:

- source-equivalent comma tokenization;
- exact year bucketing;
- lower-case/backslash path normalization;
- the source hash call contract;
- reflected-source → internal-token destination offsets;
- recursive `.trd` discovery semantics;
- allocation/load success/failure ownership handoff.

The boundary remains conservative: internal container types, property-parser
internals, non-ASCII CRT locale behavior for the optional uppercase hash mode,
the text track-list format handled by `FUN_0049f2c0`, and higher-level
track-selection policy remain open.
