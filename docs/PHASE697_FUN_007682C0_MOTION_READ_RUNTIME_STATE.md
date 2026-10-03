# Phase 697 — persistent `FUN_007682c0` motion-read runtime-state join

## Playable-slice blocker reduced

Phase 696 removes the broad arbitrary `FUN_007682c0` callback from the deepest
composed outer-update path and replaces it with a typed source-visible effect
provider plus a typed accumulator-delta consumer.

That stronger path still existed only as a standalone explicit executor. Phase
697 carries it through `NativeRuntimeState` so repeated explicit vehicle updates
reuse the same persistent BODY state and refresh the Phase 695 BODY pose snapshot
transport after every successful update:

```text
NativeRuntimeState
  -> participant/workspace admission
  -> persistent BODY bytes N
  -> Phase 696 typed FUN_007682c0 effect chain
     -> Phase 693 native FUN_007675f0 arithmetic
     -> Phase 691 FUN_007afdd0 scalar-provider boundary
     -> two source-ordered half-steps
     -> solver/contact BODY integration
  -> validate returned BODY cardinality
  -> decode persistent BODY origin/basis snapshots
  -> commit BODY bytes N+1 + telemetry + pose generation
  -> next explicit update
```

This removes a runtime integration gap without claiming a retail cadence owner,
BODY-to-vehicle identity, or exact FUN_007682c0 machine scalar production.

## Native runtime entrypoint

`NativeRuntimeState` now exposes:

```text
execute_explicit_outer_update_with_fun_007682c0_motion_read_effect_provider(...)
```

`ExplicitOuterUpdateRuntimeState` adds the corresponding lower entrypoint and
reuses the existing Phase 690 admission boundary before any pass provider is
invoked:

- BODY state initialized;
- physics workspace ready;
- participant instance ready;
- participant identity join proven;
- exact runtime BODY cardinality;
- exact persistent BODY pose-snapshot cardinality.

Only after the complete Phase 696 executor returns successfully does Phase 697
validate the returned BODY byte count, decode the next pose snapshots and commit
runtime-owned state.

## Persistent telemetry

Phase 697 adds persistent counters for the latest successful update:

```text
last_motion_read_effect_provider_call_count
last_motion_read_delta_consumer_call_count
last_motion_read_gate_open_count
```

It also carries forward the nested Phase 693/691/689 telemetry:

```text
last_contact_outer_input_provider_call_count
last_contact_outer_native_call_count
last_contact_outer_gate_open_count
last_scalar_provider_call_count
last_applied_rotation_count
last_zero_noop_count
last_half_step_provider_call_count
last_physics_pass_provider_call_count
```

On successful commit:

```text
explicit_update_count += 1
body_pose_snapshot_generation = explicit_update_count
```

Legacy explicit entrypoints reset the Phase 697-only motion-read counters to
zero so telemetry cannot incorrectly attribute typed FUN_007682c0 execution to a
weaker path.

## Transaction boundary

Phase 697 is transactional for **runtime-owned persistent state**:

1. validate runtime admission;
2. execute the complete Phase 696 chain against the current persistent BODY
   bytes;
3. validate returned BODY cardinality;
4. decode the complete next BODY pose snapshot set;
5. commit BODY bytes, snapshots and telemetry together.

A participant/workspace failure occurs before any Phase 697 pass provider side
effect. A failure inside Phase 696 or malformed returned BODY buffer prevents the
runtime-owned BODY bytes, snapshots, counters and generation from committing.

This does **not** claim rollback of external side effects that already occurred
inside an injected provider or consumer before a later failure. In particular,
`Fun007682c0AccumulatorDeltaConsumer` remains an external evidence boundary; its
own external side effects are outside the runtime-owned transaction.

## BODY identity remains unresolved

Phase 380 proves the source-visible accumulator lane `BODY +0x50`, and Phase 696
narrows the application boundary to one typed scalar delta. Current evidence
still does not prove which concrete retail vehicle/BODY instance that consumer
must mutate at the Phase 684 tail callsite.

Therefore Phase 697 persists the stronger **execution chain**, not a guessed
BODY application mapping:

```text
motion_read_body_identity_application_external = true
```

The typed consumer remains mandatory and fail-closed until Process 1 proves the
concrete BODY identity/ownership relation.

## Machine scalar boundary remains unresolved

Phase 697 does not replace the Phase 696 typed effect provider with host math.
The unresolved FUN_007682c0 producer path still includes the machine magnitude
and response intermediates described in Phase 380, including exact x87/store
boundaries and caller-side inputs.

Thus:

```text
motion_read_machine_scalar_production_external = true
host_sqrt_substitution_allowed = false
```

No `std::sqrt`, `std::sin` or `std::cos` substitution is introduced by this
phase.

## Persistent BODY pose transport

Phase 695 already decodes every committed `0x170` BODY record into typed:

```text
origin : 3 x f64
basis  : 9 x f32
```

Phase 697 refreshes those snapshots from the Phase 696 final BODY bytes after
each successful explicit update. The regression proves two consecutive updates:

```text
initial BODY bytes
  -> explicit update 1
  -> BODY bytes 1 + pose generation 1
  -> explicit update 2 input
  -> BODY bytes 2 + pose generation 2
```

This still does not assign one snapshot to a concrete vehicle scene object.
BODY-to-vehicle and BODY-to-render-object identity remain separate evidence
gates.

## Scheduling remains explicit

The latest Process 1 scheduling result remains PR #1174,
`SHIFT.OuterUpdateMachineGate/1`. It proves the unique mapped machine callsite at
`0x007130f1`, but dynamic execution multiplicity and the runtime cadence owner
remain unproven.

Phase 697 therefore does not call its new entrypoint from
`NativeRuntimeState::fixed_step()` and the native regression requires:

```text
physics.fixed_step == 0
```

after two successful explicit outer updates.

## Process 3 boundary

The latest Process 3 merge is PR #1177, Phase 640
`SHIFT.RendererNativeSceneHandoff/1`. It closes the renderer-side transport from
regenerated runtime-proven draw evidence and the static scene into a prepared
native Vulkan scene set, and can satisfy the vertical-slice `scene_set` runtime
requirement without a manual handoff.

That result is deliberately renderer/resource scoped. It does not prove which
persistent physics BODY or Phase 695/697 pose snapshot corresponds to a concrete
vehicle scene object, so Phase 697 still must not write BODY pose into the native
scene or camera. The remaining join is now narrower:

```text
persistent BODY pose snapshot
+ concrete vehicle/BODY identity
+ prepared native renderer scene object identity
-> vehicle world-transform transport
```

The prepared native scene side is available; the cross-domain identity is not.

## Python oracle

Reference state machine:

```text
src/physics/fun_00770e80_motion_read_runtime_state.py
```

Regression:

```text
tests/test_fun_00770e80_motion_read_runtime_state.py
```

It treats Phase 696 as an injected proven executor and verifies only the Phase
697 boundary:

- admission before executor invocation;
- BODY bytes N become input bytes N+1;
- telemetry and pose generation commit after success;
- executor failure preserves runtime-owned state;
- malformed returned BODY cardinality preserves runtime-owned state;
- machine production, BODY application identity and cadence remain external.

The oracle does not reproduce recovered floating-point physics arithmetic.

## Native regression

```text
shift_runtime_fun_00770e80_motion_read_runtime_state_check
```

Using the shared Phase 691/694/695 two-BODY fixture, it verifies:

- two typed FUN_007682c0 effect-provider calls per outer update;
- two typed delta-consumer calls per outer update for the open-gate fixture;
- two native FUN_007675f0 executions per update;
- four Phase 691 scalar-provider calls per update;
- update 0 starts from initialized BODY bytes;
- update 1 starts byte-for-byte from update 0 committed BODY bytes;
- persistent BODY bytes continue changing across update 2;
- pose snapshots remain cardinality-aligned and generation reaches 2;
- participant admission failure invokes no provider and commits no runtime state;
- a missing typed FUN_007682c0 effect provider reaches no half-step and commits
  no runtime state;
- `physics.fixed_step` remains zero.

## CI

`native-physics-phase697` runs:

- Phase 694/696/697 Python state/orchestration regressions;
- CMake configure;
- Phase 695 pose, Phase 696 effect-chain and Phase 697 runtime-state native
  builds;
- focused CTest regressions;
- JSON evidence assertions for persistence, explicit scheduling and unresolved
  machine/identity boundaries.

## Provider inventory after Phase 697

| Deep-chain boundary | Status | Next action |
| --- | --- | --- |
| `FUN_007675f0` arithmetic | native inside persistent Phase 697 chain | closed |
| `FUN_007675f0` caller inputs | typed external provider | Process 1 producer mapping |
| `FUN_007682c0` arbitrary callback | removed from Phase 697 path | closed as broad boundary |
| `FUN_007682c0` typed effect production | external typed provider, persistent path integrated | Process 1 machine/input producer proof |
| `FUN_007682c0` BODY `+0x50` application | external typed consumer | Process 1 concrete BODY identity proof |
| `FUN_007afdd0` four f32 scalars | external typed provider | Process 1 exact machine-scalar proof |
| `FUN_00765c40` | partial native subchain; world/collision producer unresolved | remain external |
| `FUN_00758b50` | complete producer ownership unproven | remain external |
| `FUN_00766510` | primary response-application transform incomplete | remain external |
| `FUN_007b8810` | refresh producer unresolved | remain external |
| solver/constraint refresh | typed external half-step bundle | prove retail refresh ownership |
| persistent BODY origin/basis transport | runtime-owned and refreshed each successful update | closed |
| prepared renderer native scene set | materialized by Process 3 Phase 640 | closed on renderer side |
| BODY -> concrete vehicle identity | unproven | Process 1 |
| BODY pose -> prepared renderer vehicle object | cross-domain identity unproven | Process 1 + Process 3 join |
| outer-update machine callsite | unique mapped callsite proven | closed |
| outer-update dynamic multiplicity/cadence owner | unproven | keep explicit |

## Next blocker

After Phase 697, further native integration should follow whichever upstream
proof first becomes available:

1. exact FUN_007682c0 machine/input production, replacing the typed effect
   provider;
2. concrete BODY/vehicle identity, replacing the typed delta consumer and
   joining Phase 695/697 pose snapshots to the now-prepared renderer scene;
3. exact outer-update dynamic multiplicity/cadence ownership, allowing explicit
   execution to move to the proven scheduler boundary;
4. a proven remaining `FUN_0076d100` producer mapping allowing another generic
   callback to become a source-backed native producer.

No original game execution or new runtime capture is used or required.
