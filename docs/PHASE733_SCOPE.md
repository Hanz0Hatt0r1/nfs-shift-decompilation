# Phase 733 scope

Phase 733 is limited to the PC retail cache ownership and refresh policy for the surface-probe node consumed by `FUN_007675f0 -> FUN_00759210`.

In scope:

- prove `FUN_00769ef0` is the only direct caller of `FUN_007675f0`;
- prove the node comes from `HDVehicle+0x120`;
- prove setup initializes `+0x120` to null;
- prove exact last-position storage at `+0x128/+0x130/+0x138`;
- reproduce the strict `cached_node == null || squared_displacement > 0.01` refresh policy;
- type the exact external `FUN_00717cd0` lookup boundary as current f32 query position plus previous node pointer;
- preserve seven top-level external provider boundaries.

Out of scope:

- assigning physical semantics to `FUN_00717cd0` or the node graph;
- internalizing the world/node lookup implementation;
- wiring the cache helper into `NativeVehicleProviderSession` before the surrounding `FUN_00769ef0` active-path/null-node gate is modeled;
- reducing the provider count;
- changing the already-native `FUN_00759210` arithmetic;
- guessing semantics for `base_scalar`, `projected_scalar`, `alignment_scalar`, or `param_3`.
