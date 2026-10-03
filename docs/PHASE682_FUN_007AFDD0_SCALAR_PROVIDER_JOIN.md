# Phase 682 — `FUN_007afdd0` scalar-provider integration join

Phase 681 ports the source-backed arithmetic core of `FUN_007afdd0`, but it
intentionally leaves the retail x87/CRT production of four f32 scalar boundaries
external:

- squared-magnitude value used by the zero test;
- sqrt magnitude;
- sine;
- cosine.

Phase 682 integrates that source core into the proven raw BODY-array path without
inventing those remaining values.

## Proven chain composed here

The native path is now:

```text
0x170 BODY record
  -> Phase 677 decode
  -> FUN_007bab70 pre-basis arithmetic
  -> rotation_increment = cross_vector * dt
  -> mandatory Phase 682 scalar provider
  -> Phase 681 FUN_007afdd0 source core
  -> FUN_007bab70 post-basis arithmetic
  -> Phase 677 writeback
  -> next BODY
```

The provider is invoked once per BODY in the same ascending array order already
proved for `FUN_007b2270`.

## New API

Files:

```text
native_runtime/include/shift_fun_007afdd0_scalar_provider_join.hpp
native_runtime/src/fun_007afdd0_scalar_provider_join.cpp
```

The provider type receives:

```text
body_index
current 9 x f32 basis
3 x f64 rotation_increment
```

and must return `Fun007afdd0ScalarBoundary` from Phase 681.

The composed entry point is:

```text
execute_fun_007b2270_body_buffer_with_fun_007afdd0_source_core_provider(...)
```

Format:

```text
SHIFT.NativeFun007afdd0ScalarProviderJoin/1
```

## Zero path

The recovered source tests the f32 squared-magnitude value before consuming the
sqrt or trigonometric results. Phase 682 preserves that behavior through the
Phase 681 core.

For a provider result with:

```text
squared_magnitude_test == 0.0f
```

`sqrt_magnitude`, `sine`, and `cosine` are not consumed. The deterministic
regression supplies NaN in those unused fields and requires the BODY basis to
remain unchanged.

This is deliberate: fail-closed validation applies only to values actually
consumed by the proven retail branch.

## Non-zero path

When the magnitude test is non-zero, the Phase 681 core requires:

- finite, non-zero f32 sqrt magnitude;
- finite f32 sine;
- finite f32 cosine;
- finite BODY basis and f64 rotation increment.

No host `sqrt`, `sin`, or `cos` is called by this join.

## Raw BODY semantics

The join delegates storage validation and writeback to the already-proven Phase
677 raw adapter. Therefore it preserves:

- exact BODY stride `0x170`;
- ascending source-array order;
- size/count overflow and mismatch rejection;
- non-finite producer-state rejection;
- writes only to the proven `FUN_007bab70` persistent writer lanes;
- byte-for-byte preservation of unrelated BODY storage.

## Reference oracle

Python reference orchestration:

```text
src/physics/fun_007afdd0_scalar_provider_join_runtime.py
```

Regression:

```text
tests/test_fun_007afdd0_scalar_provider_join_runtime.py
```

The oracle verifies provider order, zero-path non-consumption, deterministic
source-core rotation, missing-provider rejection, and non-finite active-scalar
rejection.

## Native regression

`shift_runtime_fun_007afdd0_scalar_provider_join_check` builds two raw BODY
records:

1. BODY 0 has zero rotation increment. The provider returns a zero magnitude
   test and NaN for unused sqrt/sine/cosine values; the basis remains identity.
2. BODY 1 has `rotation_increment=(0,0,2)`. The provider supplies the exact
   deterministic Phase 681 boundary values `4, 2, 1, 0`, producing the proven
   quarter-turn source-core result.

The check also verifies:

- provider order is exactly `[0,1]`;
- provider call count equals BODY count;
- unrelated bytes at `+0x100` survive unchanged;
- missing provider fails closed;
- a non-finite active sine boundary fails closed;
- BODY size/count mismatch fails closed.

## Evidence boundary

Phase 682 does **not** make the four scalar values production-ready. In
particular it does not claim:

- exact `__CIsqrt` machine behavior;
- exact argument/result precision of `FUN_00900c40` or `FUN_00900b10`;
- x87 excess-precision lifetime inside the recovered expressions;
- ambient x87 control-word or MXCSR state;
- complete machine parity for `FUN_007afdd0`;
- permission to replace the production Phase 679 external basis boundary with
  an internally synthesized host-math implementation.

Accordingly the Phase 682 report remains explicit:

```text
machine_scalar_production_ready = false
production_basis_callback_replacement_ready = false
```

## Next gate

The remaining direct blocker is still the Phase 680 machine precision surface.
Once a real targeted `FUN_007afdd0` instruction/p-code slice proves the scalar
production and excess-precision boundaries, the provider can be replaced by an
exact native implementation without changing the surrounding BODY-array
integration architecture established by Phases 676-682.
