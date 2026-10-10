# Process 1A / P1.3A — direct/static `FUN_0067b660` slot-4 composition

## Scope

The bounded slot-4 ABI frontier isolated two one-argument, caller-cleaned candidates: `0x006022ee` and `0x006145c4`. Subsequent contracts independently classified their static/direct producer surfaces. This contract composes those results and adds one whole-image check for the exact `creg` command scalar.

## Candidate `0x006022ee`

The direct/static provenance contract resolves its table pointer to the network/CommUDP family. On that bounded surface the exact slot-4 target is `FUN_00600f60`, not animation slot `0x00af7544+0x4 -> FUN_0067b660`.

## Candidate `0x006145c4`

The registry has two statically supplied initializer result types. Their successful object vptrs are `0x00ae7d84` and `0x00ae7d6c`; neither is animation vptr `0x00af7544`.

A third registration can be forwarded through the `creg` branch at `0x005ffc7a`. The merged direct-entry closure proves 13 direct calls to `FUN_005ffc50`, zero with command `creg`, plus zero exact raw absolute-VA/RVA pointers to the dispatcher.

This pass adds a whole-image scalar check: little-endian `0x63726567` occurs exactly once, as the immediate operand of `0x005ffc69 cmp eax,0x63726567`. There is no second exact-immediate `creg` seed elsewhere in the image.

That does **not** prove the branch unreachable: the command or dispatcher pointer may still be reconstructed, encoded, supplied at runtime, or reached through unresolved indirect entry.

## Gate effect

Promoted only `p13a_fun0067b660_direct_static_immediate_slot4_surface_complete=true`. Within this bounded direct/static class no candidate is proven to target `FUN_0067b660`.

Still fail-closed: dynamic-registry reconstructed/indirect registration, callback argument provenance, global callbacks/incoming indirect, encoded/reconstructed callback entry, runtime-generated selected-wheel pointer-store negative, stored aliases, slot0, slot1, and aggregate P1.3. Provider count remains 7.

## Next step

Stop re-scanning direct/static immediate slot-4 candidates. Continue specifically with reconstructed/indirect entry to `FUN_005ffc50` and the type of any runtime registration reaching `0x006145c4`.
