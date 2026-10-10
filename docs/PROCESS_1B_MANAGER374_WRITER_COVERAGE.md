# Process 1B — manager+0x374 bounded writer coverage

This composition joins the three already-closed bounded writer classes for the Participants Manager `+0x374` field:

- exact-root direct-callee writes;
- computed `+0x374` runtime paths;
- literal/direct `FUN_00481e20` bulk-copy writes.

## Result

The exact-root direct surface contains 9 callees and exactly one nonzero `manager+0x374` writer, `FUN_00d60660`. Its value domain is the allocator-owned selected `manager+0x2a0` entry, already proven distinct from fixed `HDVehicle+0x4330`.

The computed-runtime partition is complete: 18 original paths, 0 remaining. The direct write-through candidate is rejected, the returned-pointer path is read-only, 11 forwarding paths are source-only, and all 6 receiver/destination paths are closed-negative by exact receiver provenance.

The residual literal/direct bulk-copy writer surface is also complete. `FUN_00481e20` has no remaining direct embedded-subobject destinations after the stack-local, SMS participant render-snapshot, and CCameraView state destinations were rejected.

Therefore the currently bounded direct/computed/literal writer classes do not place fixed `HDVehicle+0x4330` into `manager+0x374`.

## Remaining boundary

This does **not** close:

- escaped storage of the exact manager root;
- stack-argument aliases of the exact manager root;
- helper-mediated writes;
- non-vtable indirect setter entry;
- unrelated reconstructed manager-root aliases.

Those surfaces must be closed before the global `manager+0x374 -> HDVehicle+0x4330` identity join or final `0x004b86cf` adjudication can be promoted.

Provider count remains **7**.
