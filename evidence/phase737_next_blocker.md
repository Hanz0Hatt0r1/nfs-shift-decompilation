# Phase 737 next blocker

Phase 737 removes the two wheel-origin vectors from the unresolved `FUN_007618f0` input boundary. Existing source-backed topology now maps `HDVehicle+0x820/+0x12a0` to selected BMW FL/FR wheel BODY indices 3/4, and the native helper reads their current persistent f64 origins directly from the 11-record BODY buffer.

The remaining `FUN_007618f0` ownership blocker is singular: identify the second source argument passed to the producer and prove the owner/refresh timing of its f64 `+0x338` and inline f64 vec3 `+0x918` fields.

Next work should:

1. recover the exact `FUN_007618f0` callsite(s) and second-argument producer;
2. prove the source object's identity/lifetime without assigning semantics from field shape;
3. preserve the exact per-pass timing relative to `FUN_00765c40` and current BODY state;
4. once positive, compose Phase737 -> Phase728 -> Phase727 so `FUN_00765c40` query `world_position` no longer comes from the external pass result;
5. only then reassess whether the complete `fun_00765c40_complete_anchor` provider can be split or removed.

Alternative bounded work remains the Phase733 `FUN_00717cd0` node-cache runtime join, but only after the surrounding `FUN_00769ef0` active/null-node gate is source-backed.
