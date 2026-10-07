# Phase 731 — FUN_007675f0 outer channel B ownership

Phase 731 removes `distance_filter_cap` from the production per-pass `FUN_007675f0` provider.

Exact PC retail machine code closes the owner chain:

```text
FUN_00770e80 param_2
  -> f64 store HDVehicle+0xa0 at 0x00770ea5
  -> same HDVehicle+0xa0 loaded before both FUN_00765470 half-steps and multiplied by 0.5
  -> FUN_007675f0 loads HDVehicle+0xa0 at 0x007676d8
  -> f64 is stored/reloaded as f32
  -> narrowed value is passed to FUN_00783a30
```

The BODY pointer is a separate `HDVehicle+0x33a0` load. Therefore the old Phase 379 text `body_field+0xa0` was inaccurate; this is an HDVehicle receiver field, not a BODY field.

The native `outer_timestep` already represents this `FUN_00770e80` channel because the existing Phase 683 schedule uses it to produce the same two `0.5 * outer_timestep` half-step calls. Phase 731 reuses that owner instead of adding a new provider or inventing a new timing source.

Production `ContactOuterSessionInput` now retains six normal external fields:

- `planar_delta`;
- `surface_scalar`;
- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`;
- `param_3`.

`previous_distance_state`, `distance_filter_cap`, `speed_x`, and `speed_z` are no longer normal production provider fields. Historical fixture compatibility metadata is not retail evidence.

The exact PC f64-to-f32 store/reload before `FUN_00783a30` is preserved. Top-level external-provider count remains seven.
