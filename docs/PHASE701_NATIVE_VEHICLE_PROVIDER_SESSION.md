# Phase 701 — persistent deep vehicle provider session

## Playable-slice blocker reduced

Phase 697 already carries the deepest current source-ordered two-half-step path
through `NativeRuntimeState`. Phase 699 proves that exactly nine producer
boundaries in that path remain external and that none is currently safe to
replace with inferred behavior. Phase 700 closes the downstream read-only pose
handoff for a future proven chassis BODY index.

The remaining Process 2 integration problem is that Phase 697 is still normally
invoked from regressions with a fresh collection of unrelated callbacks on every
call. That is a poor production boundary for replacing the nine external rows
one-by-one as Process 1 proves them.

Phase 701 introduces one persistent, fail-closed provider session:

```text
NativeVehicleProviderSession
  -> validate all nine Phase 699 provider boundaries
  -> NativeRuntimeState admission
  -> source-ordered FUN_0076d100 pass callbacks
  -> typed FUN_007675f0 input provider
  -> typed FUN_007682c0 effect + delta consumer
  -> FUN_00765470 refresh provider
  -> separate FUN_007afdd0 scalar-provider factory
  -> FUN_007b8810 post-half-step callback
  -> Phase 697 persistent outer update
  -> commit runtime-owned BODY state + session telemetry
  -> next explicit session step
```

No original `SHIFT.exe` execution and no new runtime capture are used.

## Contract

```text
SHIFT.NativeVehicleProviderSession/1
```

Native files:

```text
native_runtime/include/shift_native_vehicle_provider_session.hpp
native_runtime/src/native_vehicle_provider_session.cpp
```

The session owns a `NativeVehicleExternalProviderBundle` with exactly nine
first-class boundaries matching Phase 699:

1. `FUN_00765c40` / `contact_factor`;
2. `FUN_00758b50` / `wheel_update`;
3. `FUN_00766510` / `contact_response`;
4. `FUN_007675f0` caller-input provider;
5. `FUN_007682c0` effect provider;
6. `FUN_007682c0` BODY `+0x50` delta consumer;
7. `FUN_007afdd0` scalar-provider factory;
8. `FUN_00765470` half-step refresh provider;
9. `FUN_007b8810` post-half-step provider.

The scalar factory and half-step refresh provider are deliberately separate.
Phase 699 tracks them as separate proof obligations, so Phase 701 does not hide
the unresolved machine-scalar path inside a broad half-step callback.

## Admission and ordering

Construction rejects a missing top-level boundary before any provider is
invoked. `execute_explicit_step()` rechecks the bundle and then delegates to the
existing Phase 697 runtime entrypoint. That entrypoint preserves:

- participant identity admission before pass-provider side effects;
- exactly two physics passes;
- exactly two half-steps;
- source anchor ordering inside each pass;
- persistent BODY byte cardinality and commit;
- pose-snapshot regeneration after success.

Phase 701 adapts the persistent bundle to the already-proven typed Phase 697 API;
it does not reorder the retail anchors.

The `FUN_007afdd0` factory is called when the corresponding half-step input is
requested. A factory that returns an empty scalar provider fails closed. The
factory invocation itself is a native adapter operation and is not promoted as a
retail producer-timing claim.

## Transaction boundary

Session telemetry is accumulated locally and committed only after the Phase 697
runtime update succeeds:

```text
session_step_count += 1
last_telemetry = successful-step telemetry
```

A runtime admission failure or a failure inside the deep chain leaves prior
session telemetry and the runtime-owned persistent BODY commit unchanged.

As in Phase 697, external provider side effects cannot be rolled back if a later
provider fails. Phase 701 does not claim transactional semantics for external
systems.

## Persistent telemetry

The session records call counts for all nine top-level boundaries:

```text
contact_factor
wheel_update
contact_response
contact_outer_input
motion_read_effect
motion_read_delta_consumer
scalar_provider_factory
half_step_refresh
post_half_step
```

For the open-gate two-pass regression every row is called twice per explicit
outer update. The nested Phase 697 telemetry independently verifies native
`FUN_007675f0`, `FUN_007afdd0`, half-step and motion-read execution counts.

## Machine scalar policy

Phase 701 does not internalize `FUN_007afdd0` or `FUN_007682c0` machine scalar
production. The scalar provider remains externally produced through the typed
factory, and the motion-read effect remains a typed external provider.

Therefore:

```text
machine_scalar_math_internalized = false
host_sqrt_substitution_allowed = false
host_sin_substitution_allowed = false
host_cos_substitution_allowed = false
```

No `std::sqrt`, `std::sin` or `std::cos` is introduced by this phase.

## Process 1 sync

The latest relevant Process 1 result remains the corrected
`SHIFT.VehicleNamedBodyTopologyFrontier/2` from PR #1184. Exact BMW SDF BODY
order and eight wheel/spindle indices are known, but:

```text
rear_axle_BODY_index_ready = false
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
```

Phase 701 therefore does not bind the `FUN_007682c0` delta consumer to a guessed
chassis BODY and does not promote any persistent pose to a vehicle transform.

## Process 3 sync

Process 3 PR #1186 / native playable scene composition now closes an important
renderer-side blocker:

```text
prepared Silverstone draws
+ canonical BMW vehicle draws
-> one prepared SHIFT.NativeSceneVulkanSet/1
```

It also gives the BMW vehicle draws a durable renderer vehicle-object identity
and preserves their source `RenderCommand.world_matrix` through the existing
`SHIFT.VulkanWorldTransformPacket/1` path.

That is renderer identity, not physics identity. The Process 3 contract still
keeps:

```text
persistent_BODY_pose_consumed = false
phase698_vehicle_BODY_selection_consumed = false
dynamic_vehicle_world_transform_claimed = false
```

Therefore the remaining cross-process transform join is narrower:

```text
Process 1 proven chassis BODY selection
+ Phase 698/700 selected persistent BODY pose
+ Process 3 durable BMW renderer identity
+ proven BODY pose -> RenderCommand/SVWT matrix convention
-> dynamic vehicle world transform
```

Phase 701 itself does not consume renderer state and has no Vulkan or camera side
effect.

## Scheduling remains explicit

`NativeVehicleProviderSession::execute_explicit_step()` is an explicit call. It
is not invoked from `NativeRuntimeState::fixed_step()` or the executable frame
loop.

Current Process 1 evidence still does not prove dynamic outer-update
multiplicity or cadence ownership. Hence:

```text
fixed_step_auto_schedule = false
deep_outer_update_executable_schedule_enabled = false
```

## Reference oracle

```text
src/physics/native_vehicle_provider_session_runtime.py
tests/test_native_vehicle_provider_session_runtime.py
```

The oracle checks only session orchestration:

- all nine boundaries required before executor invocation;
- two-pass adaptation;
- separate refresh/scalar factories;
- session telemetry commit after success;
- failed step preserves session-owned state;
- negative transform/math/scheduling claims remain false.

It does not reproduce physics arithmetic.

## Native regression

```text
shift_runtime_native_vehicle_provider_session_check
```

Using the existing Phase 697 two-BODY fixture, the regression verifies:

- incomplete provider bundle is rejected before side effects;
- one persistent bundle executes two consecutive explicit outer updates;
- all nine top-level boundaries have expected per-step cardinality;
- nested Phase 697 native provider telemetry remains intact;
- BODY bytes persist from step one into step two and continue evolving;
- participant admission failure reaches no provider side effect;
- failed execution does not advance session or runtime-owned update counters;
- `physics.fixed_step` remains zero.

## Blocker graph after Phase 701

```text
Phase 697 deepest explicit path                    closed
Phase 699 exact external-provider inventory        closed
persistent nine-boundary provider session          closed as infrastructure
replace any one provider with proven producer      blocked on Process 1 proof
main/chassis BODY selection                        blocked on Process 1
renderer vehicle-object identity                   closed on Process 3 side
BODY pose -> RenderCommand/SVWT matrix convention  blocked on Process 1 + cross-domain proof
dynamic vehicle world transform                    blocked behind those joins
automatic cadence                                  blocked on Process 1
```

## Next Process 2 action

Regenerate/review the Phase 699 frontier after every new Process 1 merge. The
first row promoted to `implement_now` should replace its corresponding Phase 701
bundle field without changing the session callsite. If chassis identity becomes
positive first, feed the proven selection through Phase 698/700 and join it to
the Process 3 renderer vehicle identity only after the BODY-pose-to-SVWT matrix
convention is proven. Keep physics execution explicit until cadence ownership is
separately proven.
