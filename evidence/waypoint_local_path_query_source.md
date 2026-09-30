# SHIFT FUN_00718d00 linked local waypoint query evidence

This note records the retail local waypoint query that searches around an
already-known WayPointBase pointer and falls back to the global
`FUN_007189a0` query at specific link boundaries.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Function identity

`FUN_00718d00` begins at retail PE `0x00718d00`.

Its logical arguments are:

- AIDatabase / owner object in `ecx`;
- query position pointer;
- optional current WayPointBase pointer;
- Branch-ID selector;
- byte-sized final-orientation adjustment flag.

The Ghidra signature types the Branch-ID selector as a float, but retail x86
uses ordinary integer compares. At `0x00718d29` the selector is loaded as a
DWORD and compared directly against WayPointBase `Branch ID +0x6c`. The same
raw DWORD is passed to `FUN_007189a0` on fallback.

## Null-current fallback

At `0x00718d08..0x00718d1c`, a null current pointer immediately calls
`FUN_007189a0(this, query, branch_selector)` and returns its result.

This is a direct fallback, not a local-array scan.

## Branch redirect

When the current waypoint's `Branch ID +0x6c` differs from the requested
selector, the block at `0x00718d29` checks runtime `branch +0x184`.

The anchor moves to that branch pointer only when:

1. `+0x184` is non-null; and
2. the target's `Branch ID +0x6c` exactly equals the requested selector.

There is no special `-1` any-branch case in this local redirect. The
`-1` behavior belongs to the global `FUN_007189a0` fallback.

## Local distance metric

Unlike `FUN_007189a0`, which uses `dx² + dz² + dy⁴`,
`FUN_00718d00` uses ordinary three-dimensional squared distance over the same
unreflected derived position at `+0x8c/+0x90/+0x94`:

`distance = dx² + dy² + dz²`.

The x87 blocks at `0x00718d44..` store each delta through a 32-bit local and
store the final score through a 32-bit float local before comparison.

## Previous-link search

The previous-link search starts from runtime `prev +0x17c`.

The first previous record is considered only when its distance is strictly
smaller than the current best. Once that decreasing walk starts:

- each accepted previous candidate must have the requested Branch ID;
- the walk continues only while the next previous record is strictly closer;
- equal distance stops the walk and keeps the earlier local candidate.

A source-level peculiarity is preserved: after a closer, branch-matching
previous candidate is encountered, the routine fetches that candidate's own
previous pointer before committing the candidate. If that pointer is null,
execution jumps to the global fallback block at `0x00718f6e`.

Thus a decreasing previous chain that reaches a null terminus falls back to
`FUN_007189a0` rather than returning the terminal local candidate.

## Next-link search

The forward search starts from the anchor waypoint's runtime
`next +0x180`, not from the best waypoint discovered by the previous pass.

The immediate next record must beat the best distance established so far.
After that, the routine follows `+0x180` while distance strictly decreases.

Important: the forward loop does **not** compare Branch ID. This asymmetry with
the previous loop is present in both the recovered C and x86 and is retained
literally.

As with the previous walk, if an improving forward chain reaches a null next
pointer, execution jumps to the global `FUN_007189a0` fallback instead of
returning the last improving local candidate.

## Optional final orientation advance

When the byte flag is nonzero, the block at `0x00718f14` reuses the same
X/Z orientation test established for `FUN_007189a0`:

`dot = record[+0x13c] * (record_x - query_x)
     + record[+0x144] * (record_z - query_z)`.

If `dot < 0.0` and `next +0x180` is non-null, the local query returns the
next pointer.

This differs subtly from `FUN_007189a0`: the global query can return null
when its selected record has a negative orientation dot and a null next link.
`FUN_00718d00` advances only when the next pointer is non-null; otherwise it
keeps the selected local record.

## Active-marker boundary

`FUN_00718d00` contains no `+0x18e` active-marker filter.

That is intentional. The local query operates on the already constructed
runtime link graph. Link construction in `FUN_00717b90` validates target
activity when it builds `+0x17c/+0x180/+0x184`, while the global
`FUN_007189a0` independently applies the `+0x18e` candidate gate.

The runtime reconstruction therefore does not add an active-marker predicate
that retail code does not execute.

## Runtime implementation

`src/ai/waypoint_local_path_query_runtime.py` exposes:

- exact function and PE block anchors;
- integer Branch-ID selector behavior;
- branch-link anchor redirection;
- source-equivalent Euclidean local metric;
- asymmetric previous/next linked hill-climb;
- exact terminal-chain global-fallback behavior;
- optional final orientation advance;
- bounded fail-closed pointer dereference for offline byte arrays.

The retail function dereferences runtime pointers directly. The offline model
can only dereference pointers inside the supplied contiguous WayPointBase
array; a non-null traversal pointer outside that bounded model is rejected
rather than treated as evidence for arbitrary process memory.
