# Phase 670 — native `FUN_007555b0` spring-gap state writes

Phase 670 ports the source- and instruction-backed state-transition part of `FUN_007555b0` into `shift_runtime_physics`.

The scope is intentionally narrower than a complete spring response. Retail `FUN_00755950` consumes a live x87 value after calling `FUN_007555b0` and stores it at runtime `+0x548`, but the recovered C prototype and current instruction evidence do not establish stable semantics for that value. The native implementation therefore ports only the independently proven gap/history writes and leaves the caller x87 return unresolved.

## Proven storage

The retail instruction stream freezes these helper-relative offsets:

- lower boundary: `+0x238`;
- upper boundary: `+0x240`;
- current gap: `+0x248`;
- previous gap: `+0x250`;
- transition trigger value: `+0x258`;
- crossing flag: `+0x260`.

The caller embeds this helper at runtime `+0x80`, so Phase 364's corresponding runtime-visible history fields remain consistent with this contract.

## Exact write order

The machine code proves that retail first copies current gap `+0x248` into previous gap `+0x250`, then recalculates current gap.

The recovered two-sided expression is:

```text
if displacement <= upper_boundary:
    current_gap = upper_boundary - displacement
else:
    current_gap = displacement - lower_boundary
```

The crossing condition is exact:

```text
current_gap > 0 && previous_gap < 0
```

When that condition is true, the instruction stream proves a write to `+0x260` and a write of the passed trigger value to `+0x258`.

The available evidence does **not** prove that either field is cleared on the non-transition path. `SpringGapStateResult` therefore reports only whether those writes occur; it does not synthesize zero/clear writes.

## Native API

`shift_spring_gap_state.hpp` exposes:

- `compute_fun_007555b0_gap()` for the exact two-sided gap expression;
- `execute_fun_007555b0_gap_state()` for the proven `+0x248 -> +0x250`, `+0x248` recalculation, and conditional `+0x260/+0x258` write boundary.

`spring_type` is retained because it belongs to the recovered helper call boundary, but Phase 670 does not invent additional type-dependent response semantics.

## Regression

`shift_runtime_spring_gap_state_check` covers:

- exact helper offsets;
- equality at the upper-bound branch;
- both sides of the two-sided gap expression;
- copy of old current gap into previous gap;
- positive-over-negative crossing with trigger write;
- a non-crossing path with no invented clearing writes;
- invalid spring type, non-finite input, and overflow rejection.

`native-physics-recent` is extended through Phase 670.

## Remaining boundary

Phase 670 does not assign physical units, does not reconstruct the caller-consumed x87 value written at runtime `+0x548`, and does not schedule the helper in `NativeRuntimeState`.

The next safe join is to compose this state helper with the Phase 669 `FUN_00758b50` pre-helper handoff while keeping the x87 output as an explicit external value, or to continue static work on the exact final per-wheel `FUN_007baa70/FUN_007baaf0` vectors and the `FUN_0076d100/FUN_00770e80` ordering frontier.
