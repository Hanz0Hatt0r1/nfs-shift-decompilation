# Phase 732 next blocker

Phase 732 internalizes the two `FUN_00759210`-derived production values previously supplied to `FUN_007675f0`: `planar_delta` and `surface_scalar`. The native pass now derives current BODY0 query position, executes the already-native surface probe, and reproduces the source float32 returned-point subtraction.

The next precise Process 2 blocker is the source owner/producer of the node pointer supplied to `FUN_007675f0` and forwarded to `FUN_00759210`.

PC retail proves the immediate handoff at `0x0076760c` (`mov edx,[ebx+0x8]`) but Phase 732 does not yet prove what object owns that `+0x8` slot, when the pointer is refreshed, or whether the selected native session can derive it from existing state. Xbox 360 independently preserves the same node argument into probe counterpart `0x8258ffb8`, but Xbox-only naming or ownership must not be imported into the PC contract.

Next work should:

1. identify the exact PC caller(s) of `FUN_007675f0` and the object passed as its node-bearing argument;
2. trace the `+0x8` node-pointer producer and refresh boundary;
3. connect an already-native owner only if the selected-session identity/freshness is source-backed;
4. otherwise type the earlier node-provider boundary without guessing physical semantics.

If node ownership remains blocked, the alternate bounded targets are `base_scalar`, `projected_scalar`, `alignment_scalar`, and `param_3`, again without semantic-name promotion.
