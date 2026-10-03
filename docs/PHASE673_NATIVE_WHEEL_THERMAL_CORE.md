# Phase 673 — native `FUN_00755a60` three-node thermal core

Phase 673 ports only the source-backed arithmetic core of `FUN_00755a60` into `shift_runtime_physics`. The existing Python reference is `src/physics/wheel_thermal_integrator_runtime.py`, backed by `evidence/wheel_thermal_integrator_evidence.json` and Phase 367.

This is deliberately a partial function port. It does not promote the entire wheel thermal integrator while producer identity and tail semantics remain less certain.

## Proven topology

`FUN_00770e80` calls `FUN_00755a60` once for each of four wheel thermal substructures. The recovered caller derives the first substructure at vehicle `this+0x400` and advances by `0x150` bytes.

The core updates the source-backed state lanes at:

- `+0x7B0` — temperature node 0;
- `+0x7B8` — temperature node 1;
- `+0x7C0` — temperature node 2;
- `+0x7C8` — shared reservoir.

No physical units or semantic names beyond those conservative roles are assigned.

## Native primitives

`compute_fun_00755a60_source_heat()` preserves the proven active/inactive branch:

```text
activity <= 0 -> 0
activity > 0  -> abs(spin_measure) * spin_activity_scale * activity
```

`compute_fun_00755a60_shape_factor()` preserves the recovered square-root branch and the `< 0.5` square-plus-quarter adjustment.

`compute_fun_00755a60_temperature_fractions()` preserves the three source expressions:

```text
f0 = ((0.5*b - a + 1.5) / 3) * dt
f1 = ((1.5 - b) / 3) * dt
f2 = ((a + 0.5*b + 1.5) / 3) * dt
```

`execute_fun_00755a60_three_node_core()` accepts already-produced source heat, secondary source, ambient exchange and reservoir exchange. For each node in source order it:

1. adds the node fraction of source heat;
2. adds the node fraction of the secondary source;
3. conditionally applies ambient-A exchange when activity is positive;
4. computes the reservoir transfer from the current reservoir and original node value;
5. applies ambient-B exchange;
6. applies the reservoir transfer to the node;
7. subtracts the same transfer from the reservoir before processing the next node.

After all three nodes, the reservoir is clamped to `[273.16, 546.32]`, matching the Phase 367 `FUN_00753620` boundary.

## Why the producer boundary stays explicit

The older full Python oracle contains a conservative reconstruction of the complete `FUN_00755a60` tail, but the recovered documentation distinguishes the activity lane used by source heat (`+0x740`) from the scalar participating in the secondary-source/steering expressions (`+0x738`). Phase 673 therefore does not collapse those producers into one native field.

Instead, `secondary_source`, `ambient_exchange` and `reservoir_exchange` enter the core as explicit precomputed scalars. This gives deterministic arithmetic parity without inventing a producer or silently choosing between aliased decompiler variables.

The wear/grip tail (`+0x7F8`, `+0x800`, derived `+0x7D8`/auxiliary state and event side effects) also remains outside this phase.

## Fail-closed behavior

The native boundary rejects non-finite inputs and non-finite intermediate arithmetic. A negative value on the selected square-root branch is rejected rather than propagated as NaN. These are native admission rules, not claims about retail exception handling.

## Regression and CI

`shift_runtime_wheel_thermal_core_check` covers:

- source-heat inactive and positive paths;
- all documented shape-factor branches;
- the neutral three-fraction fixture;
- exact sequential reservoir transfer across all three nodes (`301.0`, `300.9`, `300.81`, reservoir `307.29`);
- source + secondary-source contributions (`301.15` per node);
- high/low reservoir clamps;
- the activity gate around ambient-A exchange;
- negative square-root, non-finite state and overflow rejection.

Registration uses `native_runtime/cmake/recent_physics.cmake`, and `native-physics-recent` is extended through Phase 673.

## Remaining boundary

Phase 673 does not schedule `FUN_00755a60` in `NativeRuntimeState`, does not claim the full `FUN_00770e80` two-pass scheduler, and does not port the unresolved wear/grip tail. The safe next step is to resolve the `+0x738/+0x740` producer split and the source-backed `FUN_00752fc0` derived-state helper before assembling the complete native thermal integrator.
