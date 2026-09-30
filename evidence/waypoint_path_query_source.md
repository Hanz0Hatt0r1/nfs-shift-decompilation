# SHIFT FUN_007189a0 waypoint path query: source and x86 evidence

This note records the retail nearest-path waypoint query used by AIDatabase.
The routine is sufficiently constrained at the machine-code level to reproduce
without replacing its unusual metric with a conventional distance function.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function and storage

`FUN_007189a0` begins at PE `0x007189a0`. It scans the AIDatabase
`WayPointBase[]` using the already proven:

- count at database `+0x68`;
- pointer at database `+0x70`;
- exact element stride `0x1bc`.

Within each record the query reads:

| Record offset | Width | Role in this consumer |
|---|---:|---|
| `+0x6c` | 4 | reflected `Branch ID` |
| `+0x8c/+0x90/+0x94` | 3 × float | query-position vector used by this routine |
| `+0x13c` | float | X coefficient used by final orientation test |
| `+0x144` | float | Z coefficient used by final orientation test |
| `+0x180` | pointer | next-link return target |
| `+0x18e` | 16-bit | nonzero candidate gate |

Only `+0x6c` and `+0x180` already have stronger reflected/link evidence.
The remaining offsets keep structural names in the implementation.

## Branch selector is integer, not float

The Ghidra C signature types the third logical argument as a float, but retail
x86 proves that this is an integer selector.

At `0x00718a44` the routine performs:

```text
mov eax,[ebp+0x0c]
cmp eax,0xffffffff
je  accept-any
cmp eax,[record+0x6c]
jne reject
```

The scalar remainder loop repeats the same integer behavior at
`0x00718c6e`.

Therefore:

- selector `-1` accepts any Branch ID;
- every other selector is compared as an integer against
  `WayPointBase::Branch ID +0x6c`.

The runtime API consequently rejects Python floats rather than preserving the
decompiler's misleading signature.

## Candidate metric

The record is eligible only when the 16-bit value at `+0x18e` is nonzero.
For an eligible record the retail function loads the vector at
`+0x8c/+0x90/+0x94`.

The x87 instruction sequence from `0x00718a11` through `0x00718a30`
(and repeated in the scalar tail at `0x00718c3b..0x00718c5a`) computes:

```text
score = dx² + dz² + dy⁴
```

This is not a transcription mistake. The Y delta is duplicated and multiplied
twice to form `dy⁴`, while X and Z are squared once. The resulting score is
stored through a 32-bit float local before comparison.

The initial best-score constant is read from PE `0x00b04778`:

- raw bits `0x7cf0bdc2`;
- decoded float approximately `1.0e37`.

The comparison is strict, so equal scores retain the earlier record.

## Final orientation/link switch

After selecting the best record, the block at `0x00718c9a` computes:

```text
dot =
    record[+0x13c] * (record[+0x8c] - query.x)
  + record[+0x144] * (record[+0x94] - query.z)
```

The compare instruction at `0x00718cd7` reads PE `0x00aa9a08`.
That address contains raw `0x00000000`, exactly `0.0f`.

The x87 status-word branch then implements:

- `dot < 0.0f` → return the pointer stored at record `+0x180`;
- otherwise → return the selected record itself.

There is no null guard on the first case. If `+0x180 == 0`, the retail
routine returns null. The runtime contract preserves this behavior.

## Four-record optimization

The first part of retail `FUN_007189a0` evaluates four records per loop
iteration and advances by `4 * 0x1bc = 0x6f0`. A scalar tail handles the
remainder. The reconstructed implementation uses a linear loop because the
visible ordering, strict-min comparison, predicates, score and return value are
the same.

## Runtime implementation

`src/ai/waypoint_path_query_runtime.py` exposes:

- the exact integer Branch-ID selector contract;
- the `+0x18e` nonzero gate;
- the source/x86-backed `dx² + dz² + dy⁴` score;
- the exact initial-score constant;
- single-precision observable store boundaries;
- the final X/Z orientation dot and `+0x180` return switch;
- selected and returned record/pointer evidence separately.

This does not assign gameplay names to the unreflected `+0x8c`,
`+0x13c`, or `+0x144` storage and does not yet reproduce
`FUN_00718d00`'s linked local search.
