# Phase 370 — collision query contract

Phase 370 freezes the caller-visible boundary between the wheel runtime and
FUN_007b0710.

## Query record

FUN_00765c40 prepares a seven-double query record before the call:

- position (x, y + 0.15, z);
- +0x18 = 200.35;
- +0x20 = 9.999999933815813e36;
- +0x28 receives the returned contact height;
- +0x30 carries the previous query/cache handle;
- param_3 = 1 enables the cache-aware path.

The transform producing (x, y, z) remains an external boundary; no world/local
coordinate convention is added here.

## Returned cache record

FUN_007b0710 returns a pointer into a 0x58-byte record pool. The source
observes:

| Offset | Observed use |
|---:|---|
| +0x04 | cached query point X |
| +0x08 | cached query point Y |
| +0x0C | cached query point Z |
| +0x10 | returned normal X |
| +0x14 | returned normal Y |
| +0x18 | returned normal Z |
| +0x1C | cached/computed contact height |
| +0x20..0x28 | triangle vertex A |
| +0x2C..0x34 | triangle vertex B |
| +0x38..0x40 | triangle vertex C |
| +0x44 | record-valid flag |
| +0x50 | query-hit counter |

+0x00, +0x48 and the remaining tail are kept opaque. The allocation stride is
source-backed, but no PhysX type name is assigned.

## Observable miss/hit behavior

On a cache/fallback miss, FUN_007b0710 writes (0, 1, 0) to the output normal
vector and returns null. On a hit it writes the record normal, updates the
query record's +0x28 contact-height slot, attaches the cache pointer at +0x30,
and returns the record pointer.

FUN_00765c40 then stores the returned pointer at runtime +0x38dc. Its next
scalar is +0x38e0 = original_world_y - contact_height on hit, or the existing
+0x38e8 fallback on miss.

The derived scalar is intentionally not named as suspension travel, penetration,
height, or force because the recovered source does not prove the physical unit.

## Next boundary

The next bounded target is the query-result consumer that turns the returned
surface record into wheel/contact response. PhysX cache internals, object types,
and physical units remain separate evidence targets.
