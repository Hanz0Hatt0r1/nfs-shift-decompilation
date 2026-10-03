# Phase 693 — typed `FUN_007675f0` contact-outer provider join

## Playable-slice blocker removed

The deepest persistent native vehicle chain in Phase 691 still represents every
`FUN_0076d100` physics-pass anchor as an arbitrary `void()` callback. That is too
broad for `FUN_007675f0`: Phase 662 already ports its source-backed outer
arithmetic into native C++.

Phase 693 removes that arbitrary callback from the composed outer-update path:

```text
Phase 691 persistent two-half-step outer chain
  -> FUN_0076d100 required anchor sequence
     -> FUN_00765c40 callback                 external
     -> FUN_00758b50 callback                 external
     -> FUN_00766510 callback                 external
     -> typed FUN_007675f0 input provider     external
        -> native Phase 662 FUN_007675f0      internal
     -> FUN_007682c0 callback                 external
  -> Phase 691 half-step / solver / BODY path
```

This increases integration depth without manufacturing the still-unproven
caller-side values consumed by `FUN_007675f0`.

## Native contract

New contract:

```text
SHIFT.NativeFun00770e80ContactOuterProviderChain/1
```

Implementation:

```text
native_runtime/include/shift_fun_00770e80_contact_outer_provider_chain.hpp
native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp
```

The public physics-pass bundle replaces only the generic contact-outer callback
with:

```text
Fun007675f0ContactOuterInputProvider
    -> ContactOuterKernelInput
```

At the exact Phase 684 contact-outer anchor position the adapter:

1. calls the typed input provider once;
2. executes `execute_fun_007675f0_outer_arithmetic()`;
3. records the native result for the pass;
4. only then permits the proven `FUN_007682c0` tail anchor to run.

The other Phase 684 callbacks remain unchanged. The Phase 691 four-f32
`FUN_007afdd0` scalar provider also remains unchanged.

## Preserved boundaries

Phase 693 does not rename or infer physical semantics for the Phase 662 input
fields. It transports the exact existing typed contract:

```text
planar_delta
previous_distance_state
distance_filter_cap
speed_x
speed_z
surface_scalar
base_scalar
projected_scalar
alignment_scalar
param_3
```

Their production remains external. In particular this phase does not infer the
world-point mapping, surface ownership, force-vector ownership, vehicle control
ownership, or cadence of the contact stage.

The existing Phase 662 arithmetic remains the sole native implementation used by
this join. Phase 693 does not duplicate the kernel with new host arithmetic.

## Fail-closed behavior

The join rejects:

- a missing physics-pass provider;
- any missing remaining Phase 684 callback;
- a missing typed `FUN_007675f0` input provider;
- a repeated provider invocation for one of the two proven passes;
- invalid/non-finite Phase 662 input through the existing native kernel;
- any failure already enforced by the Phase 691 scalar-provider outer chain.

The typed pass bundle is validated before any pass callback is executed. If the
native `FUN_007675f0` kernel rejects its input, `FUN_007682c0` and the following
half-step are not executed.

## Scheduling and persistence

The join reuses Phase 691, therefore it preserves:

- exactly two outer passes;
- the existing `0.5 * outer_dt` half-step boundary;
- the Phase 684 required anchor order;
- persistent raw BODY bytes between half-steps;
- the Phase 691 typed `FUN_007afdd0` scalar-provider boundary;
- explicit outer-update execution only.

It does **not** attach the outer update to `NativeRuntimeState::fixed_step()`.
Retail cadence remains evidence-gated.

## Provider inventory after Phase 693

| Deep-chain boundary | Current classification | Process 2 action |
| --- | --- | --- |
| `FUN_007675f0` arithmetic body | already proven producer/kernel | implemented now inside outer chain |
| `FUN_007675f0` caller inputs | static/source frontier exists but producer mapping incomplete | keep typed provider; Process 1 handoff for exact producer mapping |
| `FUN_007afdd0` four f32 machine scalars | Phase 692 static frontier available; machine production not ready | remain fail-closed; Process 1 handoff |
| `FUN_00765c40` | partial native factor/query/response subchain exists; collision/world-position provider unresolved | do not replace whole callback yet |
| `FUN_00758b50` | complete producer ownership not proven at this boundary | remain external |
| `FUN_00766510` | native response arithmetic exists, upstream query/state production still external | keep callback until producer join is proven |
| `FUN_007682c0` | source/machine arithmetic evidence exists, but producer inputs and machine scalar boundaries are not yet safe for an outer-chain substitution | remain external; next Process 1/2 frontier |
| `FUN_007b8810` | required scheduling anchor proven; complete native refresh producer unresolved | remain external |
| Phase 688 solver/constraint refresh bundle | native consumers exist; per-half-step retail refresh producer not proven | remain typed external provider |
| outer-update cadence | caller frontier exists; fixed-step ownership not proven | explicit execution only |

This inventory is intentionally about the deepest composed vehicle chain rather
than counting isolated kernels.

## Reference oracle

Scheduling oracle:

```text
src/physics/fun_00770e80_contact_outer_provider_chain_runtime.py
```

Regression:

```text
tests/test_fun_00770e80_contact_outer_provider_chain_runtime.py
```

It verifies exactly one typed contact-outer input provider and one native
contact-outer execution per pass, exact two-pass cardinality, duplicate-pass
rejection, and admission failure before callback side effects. It does not
reimplement Phase 662 arithmetic.

## Native regression

```text
shift_runtime_fun_00770e80_contact_outer_provider_chain_check
```

The native check enters the actual Phase 691 composition. It verifies that:

- pass-0 order reaches the typed `FUN_007675f0` provider between
  `FUN_00766510` and `FUN_007682c0`;
- a valid Phase 662 input executes successfully before the half-step provider;
- a zero X/Z delta is rejected by the native Phase 662 kernel before
  `FUN_007682c0` or the half-step can run;
- a missing typed provider is rejected before any pass callback side effect;
- a missing physics-pass provider fails closed.

The regression deliberately stops after the first pass with a sentinel
half-step-provider exception. The already-green Phase 691 regression remains the
full persistent two-update BODY execution test; Phase 693 isolates the newly
introduced adapter without cloning its large solver fixture.

## Remaining blocker graph

Phase 693 reduces:

```text
arbitrary physics-pass callback set
  -> four generic callbacks + one typed source-backed input provider
```

The next useful Process 2 step should not add another isolated kernel. It should
either:

1. consume a Process 1 proof that closes one of the remaining producer mappings
   above and replace that provider in this composed path; or
2. expose this stronger Phase 693 chain through persistent `NativeRuntimeState`
   telemetry while preserving explicit scheduling and participant admission.

No `SHIFT.exe` execution or new runtime capture is used or required.
