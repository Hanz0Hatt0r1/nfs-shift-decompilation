# Phase 696 — typed `FUN_007682c0` motion-read effect provider join

## Playable-slice blocker reduced

After Phase 695 the deepest persistent outer-update path already exposes typed
persistent BODY origin/basis snapshots, but several `FUN_0076d100` pass anchors
still remain broad external callbacks.

Phase 693/694 already internalized the proven `FUN_007675f0` arithmetic. The next
anchor in the statically proven tail order is `FUN_007682c0`:

```text
FUN_00769ef0
  -> FUN_007675f0
  -> FUN_007682c0
```

Phase 380 proves a narrower source/machine-visible effect for `FUN_007682c0`:

- it has an initial speed gate;
- when the gate is closed it performs no accumulator application;
- the visible write target is BODY accumulator `+0x50`;
- the applied value is a scalar delta produced by still-incomplete response and
  machine-scalar paths.

The exact sqrt/x87 production and BODY ownership needed to produce/apply that
value are not yet safe to internalize. Phase 696 therefore performs the first
provider transition only:

```text
arbitrary void() FUN_007682c0 callback
  -> typed source-visible effect provider
       gate_open
       accumulator_y_delta
  -> typed accumulator-delta consumer
```

The external boundary can no longer replace the whole anchor with arbitrary
logic while claiming to use the Phase 696 API.

## Native contract

New format:

```text
SHIFT.NativeFun00770e80MotionReadEffectProviderChain/1
```

Files:

```text
native_runtime/include/shift_fun_00770e80_motion_read_effect_provider_chain.hpp
native_runtime/src/fun_00770e80_motion_read_effect_provider_chain.cpp
```

The public pass bundle is:

```text
Fun0076d100MotionReadEffectProviderCallbacks
```

It preserves the already-typed Phase 693 `FUN_007675f0` input provider and
replaces only the previous generic `motion_read_gate` callback with:

```text
Fun007682c0EffectProvider
  -> Fun007682c0AccumulatorEffect {
       gate_open
       accumulator_y_delta
     }

Fun007682c0AccumulatorDeltaConsumer
  <- accumulator_y_delta
```

At the exact Phase 684 tail anchor position the adapter:

1. invokes the typed effect provider exactly once;
2. validates the effect;
3. invokes the typed delta consumer only when `gate_open == true`;
4. only then allows the following half-step provider to execute.

The adapter reuses the complete Phase 693 chain, so native `FUN_007675f0`
execution still precedes this boundary.

## Effect validation

The typed effect fails closed when:

- `accumulator_y_delta` is NaN or Inf;
- `gate_open == false` while the delta is non-zero;
- the effect provider is missing;
- the delta consumer is missing;
- a per-pass provider is repeated;
- any Phase 693/691/689 boundary rejects its input.

A closed gate is represented as:

```text
gate_open = false
accumulator_y_delta = 0.0
```

and the delta consumer is not invoked.

## Why the delta consumer remains external

Phase 380 proves the observable BODY `+0x50` accumulator lane, but the deepest
Phase 695 runtime still does not prove which concrete retail vehicle object owns
the BODY instance at this `FUN_007682c0` call.

The consumer is therefore intentionally typed but external. It represents the
remaining identity/application join rather than pretending that Process 2 can
select a BODY index from current evidence.

This boundary is narrower than `void()` because external code receives only the
source-visible scalar delta at the application point; it cannot replace the
entire contact-tail anchor when using this API.

## Machine scalar boundary remains external

Phase 696 does **not** port the Phase 380 Python `sqrt` calls into C++.

The unresolved retail path still includes at least:

- the initial 3D magnitude over BODY `+0x78/+0x80/+0x88`;
- the planar magnitude used by `FUN_0075ada0`;
- exact x87 precision/store-reload boundaries around those intermediates;
- the complete producer inputs feeding `FUN_007595d0`;
- exact ownership of the caller-side state fields consumed by that response.

Therefore:

```text
fun_007682c0_effect_production_external = true
fun_007682c0_machine_scalar_production_external = true
host_sqrt_substitution_allowed = false
host_trig_substitution_allowed = false
complete_fun_007682c0_semantics = false
```

A future Process 1 proof may replace the typed effect provider with a recovered
native producer while keeping this Phase 696 consumer/application boundary.

## Preserved ordering and scheduling

Phase 696 reuses Phase 693, Phase 691 and the existing composed outer update.
It therefore preserves:

- two `FUN_0076d100` passes;
- source-backed Phase 684 anchor order;
- native Phase 662 `FUN_007675f0` execution before `FUN_007682c0`;
- `0.5 * outer_dt` half-step boundaries;
- solver/contact BODY integration;
- raw persistent BODY carry between half-steps;
- the Phase 691 four-f32 `FUN_007afdd0` scalar-provider boundary.

It does **not** attach the outer update to `NativeRuntimeState::fixed_step()`.

The latest Process 1 merge at the start of this phase is PR #1174,
`SHIFT.OuterUpdateMachineGate/1`. PR #1174 adds the fail-closed machine analyzer
that can map the unique source-side `FUN_00713050 -> FUN_00794a30` gate to one
exact CALL site once the targeted retail instruction export is supplied. It does
not contain a committed retail instruction result and therefore does not itself
prove one mapped machine callsite or close machine-callsite cardinality. Dynamic
execution multiplicity and the runtime cadence owner also remain unproven. The
contract therefore still reports fixed-step and render-cadence auto-scheduling
as disallowed. Process 2 must keep outer execution explicit.

## Process 3 boundary

The latest relevant Process 3 merge remains PR #1171, which unifies the offline
resource and renderer vertical-slice bootstrap. It does not prove a physics
BODY-to-scene identity. Phase 696 therefore does not route the new accumulator
effect or Phase 695 BODY pose into renderer state.

## Reference oracle

Scheduling oracle:

```text
src/physics/fun_00770e80_motion_read_effect_provider_chain_runtime.py
```

Regression:

```text
tests/test_fun_00770e80_motion_read_effect_provider_chain_runtime.py
```

The oracle verifies:

- exact two-pass provider cardinality;
- open-gate provider -> consumer ordering;
- closed gate skips the consumer;
- non-finite and closed/non-zero effects fail closed;
- missing typed boundaries are rejected before pass callback side effects;
- no host machine-scalar arithmetic is introduced.

## Native regression

```text
shift_runtime_fun_00770e80_motion_read_effect_provider_chain_check
```

The native check enters the real Phase 693 chain and stops at the half-step
provider after validating the newly introduced anchor adapter. It verifies:

- `FUN_00765c40 -> FUN_00758b50 -> FUN_00766510` still precede the tail;
- native `FUN_007675f0` still executes before the typed `FUN_007682c0` effect;
- an open effect reaches exactly one typed delta consumer before the half-step;
- a closed effect reaches no delta consumer;
- invalid effects stop the chain before the half-step;
- missing typed effect/consumer boundaries fail before pass side effects.

The Phase 691/694/695 regressions remain responsible for the full persistent
multi-update BODY path; Phase 696 isolates only the newly narrowed anchor.

## Provider inventory after Phase 696

| Deep-chain boundary | Status | Next action |
| --- | --- | --- |
| `FUN_007675f0` arithmetic | native inside persistent chain | closed |
| `FUN_007675f0` caller inputs | typed external provider | Process 1 producer mapping |
| `FUN_007682c0` whole arbitrary callback | removed from Phase 696 path | closed as broad boundary |
| `FUN_007682c0` source-visible effect production | typed external provider | Process 1 exact machine/input producer proof |
| `FUN_007682c0` BODY `+0x50` ownership/application | typed external consumer | Process 1 concrete BODY identity proof |
| `FUN_007afdd0` four f32 scalars | typed external provider | Process 1 machine-scalar proof |
| `FUN_00765c40` | partial native subchain; world/collision producer unresolved | remain external |
| `FUN_00758b50` | complete producer ownership not proven | remain external |
| `FUN_00766510` | primary response-application transform incomplete | remain external |
| `FUN_007b8810` | refresh producer unresolved | remain external |
| half-step solver/constraint refresh | typed external producer bundle | prove retail refresh ownership |
| BODY origin/basis decode | typed persistent snapshots since Phase 695 | closed |
| BODY -> concrete vehicle identity | unproven | Process 1 |
| BODY pose -> renderer scene identity | unproven | Process 1 + Process 3 join |
| outer-update machine callsite | source gate narrowed; exact retail machine mapping remains evidence-gated by PR #1174 | targeted retail instruction export / Process 1 |
| outer-update dynamic multiplicity / cadence owner | unproven after PR #1174 | keep explicit |

## Next blocker

The nearest useful follow-up is whichever proof arrives first:

1. Process 1 proves enough of the `FUN_007682c0` machine/input path to replace
   `Fun007682c0EffectProvider` with a recovered producer; or
2. Process 1 proves concrete vehicle/BODY identity, allowing the typed delta
   consumer and Phase 695 pose snapshot to bind to a real vehicle BODY; or
3. Process 1 proves dynamic execution multiplicity and the runtime cadence owner,
   allowing the existing explicit outer update to move onto that proven boundary.

No original game execution or new runtime capture is used or required.
