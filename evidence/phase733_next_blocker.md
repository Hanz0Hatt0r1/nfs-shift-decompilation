# Phase 733 next blocker

Phase 733 proves the PC retail cache owner and refresh policy for the node pointer consumed by `FUN_007675f0 -> FUN_00759210`: `HDVehicle+0x120`, initialized null and refreshed through `FUN_00717cd0` when null or after strict squared 3D displacement `> 0.01`, with exact BODY0 f64 origin cached at `+0x128/+0x130/+0x138`.

The next precise Process 2 blocker is runtime wiring of that cache policy into the selected native session without losing the surrounding `FUN_00769ef0` active-path behavior.

Next work should:

1. type the `FUN_00717cd0` lookup as the earlier external boundary rather than accepting a direct per-pass node pointer;
2. preserve the previous-node argument and f32-narrowed current BODY0 query position exactly;
3. preserve the source null-node / parent / child gates that decide whether `FUN_007675f0` executes after lookup;
4. make `HDVehicle+0x120/+0x128/+0x130/+0x138` persistent and transactional in `NativeVehicleProviderSession` only after those gates are source-backed in the composed chain.

If that join becomes disproportionately broad, use the alternate bounded target: recover the exact source provenance of `base_scalar`, `projected_scalar`, `alignment_scalar`, or `param_3` in `FUN_007675f0`, without assigning undocumented physical semantics.
