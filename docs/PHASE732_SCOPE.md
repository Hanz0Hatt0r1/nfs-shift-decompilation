# Phase 732 scope

In scope:

- preserve the direct PC retail `FUN_007675f0 -> FUN_00759210` caller ABI;
- derive the query point from current chassis BODY0 position with the source float32 spill;
- reuse the already-native `FUN_00759210` implementation;
- derive `planar_delta` as returned point minus BODY query point through the source float32 lane behavior;
- derive `surface_scalar` from the same probe call;
- replace the two derived production fields with the earlier `surface_probe_node` boundary;
- preserve compatibility-only derived values for historical lower-chain fixtures;
- keep the active top-level external-provider count at seven;
- use Xbox 360 instructions only as independent corroboration.

Out of scope:

- the producer/owner/freshness of the node pointer;
- a physical name for the node or probe outputs;
- changes to Phase 661 recursive-probe arithmetic;
- ownership of `base_scalar`, `projected_scalar`, `alignment_scalar`, or `param_3`;
- reducing the top-level provider count without a separate source-backed closure.
