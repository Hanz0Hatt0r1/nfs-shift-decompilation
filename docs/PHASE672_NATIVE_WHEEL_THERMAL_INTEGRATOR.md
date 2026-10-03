# Phase 672 — native `FUN_00755a60` wheel thermal integrator

Phase 672 ports the source/disassembly-backed three-node thermal arithmetic from `src/physics/wheel_thermal_integrator_runtime.py` into `shift_runtime_physics`.

The native function is `FUN_00755a60`, called from `FUN_00770e80` once per recovered wheel slot. `FUN_00760b50` is a separate post-pass function and is not conflated with this phase.

## Wheel topology and state offsets

Retail walks four wheel objects beginning at vehicle `+0x400`. The recovered pointer loop advances by `0x150` doubles, which is exactly `0xA80` bytes per wheel.

The contract freezes these wheel-relative state offsets:

- temperature node 0: `+0x7B0`;
- temperature node 1: `+0x7B8`;
- temperature node 2: `+0x7C0`;
- reservoir: `+0x7C8`;
- derived reservoir: `+0x7D8`;
- wear state: `+0x7F8`;
- output: `+0x800`;
- accumulator: `+0x850`.

No physical units or semantic tyre-layer names are assigned beyond the source-backed thermal role.

## Recovered arithmetic

The native implementation preserves the established reference-oracle order:

1. add `273.16` to both ambient inputs;
2. compute source heat as `abs(spin_measure) * spin_activity_scale * activity` only for positive activity;
3. execute the `factor_control` square-root branch and the `< 0.5` quarter adjustment;
4. form the secondary source and clamp the two steering intermediates to `[-1, 1]`;
5. derive the three temperature fractions;
6. compute ambient/reservoir exchange coefficients;
7. update the three temperature nodes in order, mutating the shared reservoir after each node;
8. clamp the reservoir to `[273.16, 546.32]`;
9. compute average and derived reservoir fields;
10. accumulate the abrasion term and apply the `0.6875` wear floor when enabled;
11. compute the signed temperature slope branch, bounded factor and final output;
12. compute the derived auxiliary field and over-temperature condition.

The sequential reservoir mutation is significant: node 1 consumes the reservoir left by node 0, and node 2 consumes the reservoir left by node 1.

## Native safety boundary

The native path rejects non-finite inputs/results, negative square-root arguments and a zero normalization reference. These are fail-closed runtime guards; they are not claimed as retail exception behavior.

## Regression

`shift_runtime_wheel_thermal_integrator_check` ports the established Python fixtures for:

- source-heat zero/active branches;
- shape-factor branches;
- temperature fractions;
- sequential reservoir exchange (`301.0`, `300.9`, `300.81`, reservoir `307.29`);
- positive activity (`source_heat=20`, `secondary_source=3`, nodes `301.15`);
- reservoir high clamp and derived fields;
- wear-floor crossing;
- final factor/output (`limited=1`, output `0.5`);
- non-finite, invalid sqrt and zero-normalization rejection.

`native-physics-recent` is extended through Phase 672.

## Remaining boundary

Phase 672 does not reconstruct the unresolved event side effects attributed to `FUN_0070e2c0`, does not assign physical units to coefficients, does not port the separate `FUN_00760b50` post-pass, and does not schedule thermal updates in `NativeRuntimeState`.

The outer `FUN_00770e80` two-pass ordering remains source-backed but only partially executable natively; it should be joined after the relevant `FUN_0076d100` and post-pass boundaries are closed without inventing missing callees.
