# Phase 735 next blocker

Phase 735 makes the two BODY-derived `FUN_007675f0` scalar intermediates native. Production `ContactOuterSessionInput` is therefore narrowed to the earlier `surface_probe_node` boundary plus one remaining direct scalar, `projected_scalar`.

The next narrow source-backed target is the exact `FUN_00759c90` caller join that produces `projected_scalar`. Phase 660 already provides the native three-record aggregate arithmetic, but Phase 735 deliberately does not assume which aggregate field/intermediate is consumed until the PC `FUN_007675f0` callsite and record ownership are joined exactly.

For that next slice:

1. use PC retail `0x0076779f..0x007677df` and the `FUN_00759c90` implementation/call signature as authority;
2. use Xbox recomp `sub_825939F0` and its call to `sub_825899C0` only to accelerate cross-platform mapping;
3. identify the exact native Phase 660 output/intermediate corresponding to the directional projection stored before the strict outer gate;
4. preserve all f32 narrowing/order visible at the caller;
5. remove `projected_scalar` from production `ContactOuterSessionInput` only after that join is proved.

The active top-level provider count remains seven until a whole provider boundary, rather than only fields inside it, can be removed.
