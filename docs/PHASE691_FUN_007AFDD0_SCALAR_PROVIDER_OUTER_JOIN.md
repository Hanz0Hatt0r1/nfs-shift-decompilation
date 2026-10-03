# Phase 691 — typed `FUN_007afdd0` scalar-provider outer join

Phase 690 gives `NativeRuntimeState` an explicit persistent outer-update state,
but the Phase 689 half-step input still exposes an arbitrary
`BodyBasisRotationCallback`. That callback is broader than the evidence requires:
Phase 681 already recovered the source-shaped `FUN_007afdd0` basis update and
Phase 682 already defined the four unresolved scalar boundaries needed to run it.

Phase 691 replaces the arbitrary basis callback at the composed outer-update
boundary with that typed scalar provider.

## New outer-chain boundary

The native contract is:

```text
SHIFT.NativeFun00770e80ScalarProviderAnchorChain/1
```

implemented by:

```text
native_runtime/include/shift_fun_00770e80_scalar_provider_anchor_chain.hpp
native_runtime/src/fun_00770e80_scalar_provider_anchor_chain.cpp
```

The half-step provider now supplies the previously proven Phase 688/689 inputs
plus:

```text
Fun007afdd0ScalarProvider
```

For each BODY basis update the provider returns exactly:

```text
squared_magnitude_test : f32
sqrt_magnitude         : f32
sine                   : f32
cosine                 : f32
```

The native adapter then executes `execute_fun_007afdd0_source_core()` itself and
returns the resulting basis to the already-proven BODY writer path.

## What moved inside the native chain

Before this phase:

```text
persistent BODY writer
  -> arbitrary external basis callback
  -> updated basis
```

After this phase:

```text
persistent BODY writer
  -> typed four-f32 scalar provider
  -> native FUN_007afdd0 source core
  -> updated basis
```

Thus external code can no longer replace the recovered basis arithmetic with an
arbitrary transform when using the Phase 691 API.

The source core preserves the recovered zero test, f64-to-f32 normalization
boundary, coefficient graph and in-place stripe write order from Phase 681.

## Runtime-state integration

`ExplicitOuterUpdateRuntimeState` adds a typed execution method and tracks:

- scalar-provider call count;
- applied rotation count;
- zero/no-op count.

`NativeRuntimeState` exposes:

```text
execute_explicit_outer_update_with_fun_007afdd0_scalar_provider(...)
```

The Phase 690 admission gates remain unchanged:

- ready physics workspace;
- ready participant instance;
- proven participant identity join;
- exact persistent BODY byte cardinality.

The call remains explicit. `NativeRuntimeState::fixed_step()` still does not
schedule the Phase 689/691 outer-update chain automatically.

## Machine boundary deliberately left open

Phase 691 does **not** produce the four scalar values with host mathematics.
In particular, it does not substitute host `sqrt`, `sin` or `cos` for the retail
x87/CRT paths.

The unresolved retail boundary still includes:

- the exact extended-precision squared-magnitude value and f32 store/test;
- `__CIsqrt`/sqrt result production;
- `FUN_00900c40` sine dispatcher behavior;
- `FUN_00900b10` cosine dispatcher behavior;
- ambient x87 control word and MXCSR at the callsite;
- any excess-precision boundaries not proven by the recovered C source alone.

A targeted machine/p-code export for `FUN_007afdd0` remains the correct route to
close those values. Drive indexing currently exposes the Ghidra project but did
not surface a ready `fun_007afdd0_basis_rotation_static.json` artifact, so this
phase does not infer the missing machine semantics.

## Regression

The deterministic native regression uses the valid source-core zero/no-op path:

```text
squared_magnitude_test = 0
sqrt_magnitude = 0
sine = 0
cosine = 1
```

The zero test returns before the other scalar values participate in arithmetic,
matching the recovered source contract.

For the two-BODY fixture it requires:

- two scalar-provider calls per half-step/pass;
- four calls per explicit outer update;
- four zero/no-op source-core results;
- no externally supplied arbitrary basis callback;
- the Phase 689 frozen first-outer BODY-0 origin
  `(3.125, 4.65625, 6.1875)`;
- exact persistent BODY carry into a second explicit outer update;
- missing scalar provider rejection;
- participant admission rejection before any outer providers execute.

The Python scheduling oracle separately freezes provider cardinality and the
remaining evidence boundary without reproducing the native basis arithmetic.

## Remaining frontier

Phase 691 narrows the persistent-motion path to typed machine scalar production.
It still does not prove:

- exact retail x87/CRT scalar generation for `FUN_007afdd0`;
- native fixed-step cadence equals retail `FUN_00770e80` cadence;
- automatic per-pass solver/contact producer refresh;
- retail control-input ownership or drivetrain propagation;
- complete `FUN_007afdd0`, `FUN_00765470`, `FUN_0076d100` or `FUN_00770e80`
  semantics.

No original game execution or new runtime capture is required by this phase.
