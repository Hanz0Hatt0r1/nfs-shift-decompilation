# Process 1B — HDVehicle+0x4330 bounded indirect-entry coverage v3

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/3` supersedes `/2` and incorporates the new constant-only encoded-carrier synthesis closure.

The aggregate now contains five bounded classes:

1. static/source-visible exact carrier materialization — 4 subclasses, 0 exact-carrier hits;
2. canonical computed/loader entry publication — 3 subclasses, 0 hits;
3. bounded runtime callback registration — 8 surfaces, 51 physical callsites, 36 possible entrypoints, 0 hits;
4. exact preferred-imagebase + exact carrier-RVA immediate synthesis — 2,847,850 decoded instructions over the P1A 16-carrier superset, 0 exact carrier-RVA scalar uses/candidates;
5. constant-only straight-line encoded synthesis — 2,847,850 instructions, 67,970 constant seeds, 2,168 recognized transitions, 0 exact P1B carrier values.

The composed bounded exact-carrier hit count remains **0**.

This version does not promote any global indirect-entry gate. Memory/table-derived pointer values, split or cross-block arithmetic, delayed module-base consumers, runtime copied pointers, runtime patching, remaining callback families and opaque indirect dispatch remain open.

Provider count remains 7. `manager+0x374 -> HDVehicle+0x4330`, final `0x004b86cf` rejection and aggregate P1.3 remain fail-closed.
