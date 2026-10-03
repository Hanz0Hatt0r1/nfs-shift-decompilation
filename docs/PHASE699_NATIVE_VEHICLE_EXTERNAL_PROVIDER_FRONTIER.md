# Phase 699 — deepest native vehicle external-provider frontier

## Playable-slice blocker reduced

Phase 697 carries the strongest current two-half-step physics path persistently
through `NativeRuntimeState`. Phase 698 adds fail-closed infrastructure for a
future proven concrete BODY index to select one persistent BODY pose. Process 1
PR #1183 further narrows the BMW chassis identity frontier by proving nine named
BODY field roles and the exact retail SDF cardinality, but it still reports:

```text
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
```

The remaining execution-depth problem is therefore the set of injected producers
inside the Phase 697 path. Phase 699 freezes that set as a machine-readable
handoff rather than replacing an unresolved producer with guessed behavior.

No original `SHIFT.exe` execution or new runtime capture is used.

## Contract

```text
SHIFT.NativeVehicleExternalProviderFrontier/1
```

Source and report builder:

```text
src/physics/native_vehicle_external_provider_frontier.py
tools/build_native_vehicle_external_provider_frontier.py
```

Classification policy:

```text
already proven producer     -> implement_now
static frontier available   -> request_process1_static_proof
runtime-only evidence       -> remain_blocked_runtime_only
```

Current result:

```text
external providers = 9
implement_now = 0
Process 1 handoffs = 9
runtime-only blocked = 0
```

`implement_now = 0` is intentional: every producer currently strong enough for
safe native substitution is already integrated.

## Remaining provider inventory

| Boundary | Current API | Missing proof |
| --- | --- | --- |
| complete `FUN_00765c40` | generic `contact_factor` callback | complete/separable local work, query world-position producer, collision-provider ownership |
| `FUN_00758b50` | generic `wheel_update` callback | complete inputs/writes/nested work and wheel/control ownership |
| `FUN_00766510` | generic `contact_response` callback | primary response application into `FUN_007baa70` and caller-state producers |
| `FUN_007675f0` caller inputs | `Fun007675f0ContactOuterInputProvider` | producers/refresh timing for all ten typed inputs |
| `FUN_007682c0` effect production | `Fun007682c0EffectProvider` | exact magnitude/x87 path and complete response inputs |
| `FUN_007682c0` BODY `+0x50` application | `Fun007682c0AccumulatorDeltaConsumer` | exact main/chassis BODY index plus update-child -> solver-base continuity |
| `FUN_007afdd0` f32 scalars | `Fun007afdd0ScalarProvider` | exact stores/returns, sqrt/trig provenance, floating-control state |
| `FUN_007b8810` | `Fun007b8810PostHalfStepCallback` | complete refresh producer semantics |
| `FUN_00765470` refresh | `Fun00765470MachineScalarHalfStepProvider` | producer ownership and exact refresh timing across both half-steps |

The JSON contract contains the exact proof requests for every row.

## Process 1 sync

PR #1183 (`SHIFT.VehicleNamedBodyTopologyFrontier/1`) is the latest identity
narrowing used here. It proves the BMW named BODY field topology and establishes
that the retail suspension SDF contains 11 BODY records. With an exact hash-
matched SDF it can recover BODY name order and finite residual rows, but it does
not declare any plausible residual name to be the chassis.

Two identity joins remain:

1. main/chassis BODY semantic selection;
2. update-child -> vehicle solver-base continuity through `FUN_007615c0`.

Phase 698 is ready to consume an exact selected index once those proofs become
positive.

The scheduling boundary remains separate. Current committed evidence narrows the
source gate and finite machine candidates, but does not provide the complete
retail proof needed for automatic scheduling: exact selected machine callsite,
dynamic statement multiplicity and runtime cadence ownership all remain gated.

Policy:

```text
explicit outer update only
fixed_step auto-schedule forbidden
```

## Process 3 sync

Phase 641 advances the resource/renderer side by exhausting existing capture
sampler evidence before recapture. It still does not establish physics
BODY/vehicle -> exact renderer scene-object identity.

## Fail-closed guards

Phase 699 preserves:

- exactly two half-steps;
- persistent BODY state;
- participant admission;
- missing-provider rejection;
- no host `sqrt`, `sin` or `cos` substitution at unresolved machine boundaries;
- no BODY-pose -> vehicle-transform promotion;
- no fixed-step auto scheduling;
- no original-game execution;
- no new runtime capture requirement.

## Regression / CI

```text
tests/test_native_vehicle_external_provider_frontier.py
.github/workflows/native-physics-phase699.yml
```

The regression verifies exactly nine external providers, an empty
`implement_now` set, the actual Phase 697 C++ provider API symbols, Phase 698
fail-closed selection infrastructure, the PR #1183 chassis-selection state, and
the negative scheduling/math/transform guards.

## Next Process 2 action

Regenerate the report before each provider-replacement stage and implement only a
row whose upstream proof has moved to an implementable state. Highest-value
frontiers are currently:

1. exact main/chassis BODY selection and update-child -> solver-base continuity;
2. exact `FUN_007682c0` machine/effect production;
3. exact outer-update callsite + dynamic multiplicity/cadence ownership;
4. complete/separable `FUN_00765c40` production;
5. retail resource -> concrete initial BODY construction.
