# Phase 694 — persistent `FUN_007675f0` contact-outer runtime-state join

## Playable-slice blocker removed

Phase 693 internalized the already-native `FUN_007675f0` arithmetic inside the
deepest two-half-step outer chain, but that stronger chain still existed only as
an explicit standalone executor. The persistent `NativeRuntimeState` entrypoint
stopped at Phase 691 and therefore could not expose or retain the new typed
contact-outer execution telemetry.

Phase 694 carries the Phase 693 chain across the existing persistent runtime
boundary:

```text
NativeRuntimeState
  -> participant/workspace admission
  -> persistent BODY bytes
  -> Phase 693 typed FUN_007675f0 provider chain
     -> Phase 691 four-f32 scalar-provider chain
     -> two source-ordered half-steps
     -> solver/contact BODY update
  -> commit resulting BODY bytes
  -> explicit execution telemetry
```

This removes a runtime integration gap without claiming a retail cadence owner.

## Native entrypoint

`NativeRuntimeState` now exposes:

```text
execute_explicit_outer_update_with_fun_007675f0_contact_outer_provider(...)
```

The method delegates to `ExplicitOuterUpdateRuntimeState`, which validates the
same Phase 690 runtime boundary before any physics provider is invoked:

- BODY state initialized;
- physics workspace ready;
- participant ready;
- participant identity join proven;
- runtime BODY cardinality exactly matches the persistent byte buffer.

Only after successful completion of the full Phase 693 executor are the returned
BODY bytes committed to the persistent runtime state.

## Telemetry

The persistent outer-update state now records the most recent successful update:

```text
last_contact_outer_input_provider_call_count
last_contact_outer_native_call_count
last_contact_outer_gate_open_count
```

The existing fields remain populated from the nested Phase 691/689 result:

```text
last_physics_pass_provider_call_count
last_half_step_provider_call_count
last_scalar_provider_call_count
last_applied_rotation_count
last_zero_noop_count
explicit_update_count
last_outer_timestep
```

Older explicit entrypoints reset the new contact-outer counters to zero, so the
telemetry never incorrectly attributes Phase 693 execution to a legacy path.

## Persistence and failure semantics

The Phase 694 state transition is transactional at the outer boundary:

1. validate runtime admission;
2. execute the complete Phase 693 chain using the current persistent BODY bytes;
3. validate returned BODY byte cardinality;
4. commit BODY bytes and telemetry;
5. increment `explicit_update_count`.

A participant/workspace failure occurs before provider side effects. A provider,
solver, machine-scalar, contact-kernel or returned-cardinality failure occurs
before persistent BODY/telemetry commit.

The next explicit call therefore sees exactly the previous successful call's
BODY bytes, not a partially completed update.

## Scheduling remains explicit

Phase 694 intentionally does not call the new entrypoint from
`NativeRuntimeState::fixed_step()`.

The regression verifies that two successful explicit Phase 694 updates leave:

```text
physics.fixed_step == 0
```

This is required until Process 1 proves the retail cadence owner for the
`FUN_00770e80` outer update.

## Reusable regression fixture

The existing Phase 691 two-half-step solver/BODY fixture is moved into:

```text
native_runtime/tests/fun_00770e80_outer_update_fixture.hpp
```

Both the Phase 691 regression and the new Phase 694 regression consume this
fixture. This avoids maintaining two divergent synthetic solver topologies while
allowing deeper composed paths to verify the same persistent BODY invariants.

## Reference oracle

Reference state machine:

```text
src/physics/fun_00770e80_contact_outer_runtime_state.py
```

Regression:

```text
tests/test_fun_00770e80_contact_outer_runtime_state.py
```

The oracle treats Phase 693 as an injected proven executor. It checks only the
new boundary owned by Phase 694:

- admission before executor invocation;
- BODY bytes from update N are input to update N+1;
- telemetry is committed only after success;
- failed/malformed execution preserves prior state;
- fixed-step scheduling and unresolved producers remain outside the contract.

It does not duplicate any recovered floating-point physics arithmetic.

## Native regression

```text
shift_runtime_fun_00770e80_contact_outer_runtime_state_check
```

Using the same full solver/BODY fixture as Phase 691, it verifies:

- exactly two typed `FUN_007675f0` input-provider calls per outer update;
- exactly two native Phase 662 `FUN_007675f0` executions per outer update;
- four Phase 691 machine-scalar provider calls per outer update for two BODYs;
- first half-step of update 0 receives the initialized BODY bytes;
- first half-step of update 1 receives update 0's committed final BODY bytes;
- final BODY bytes continue changing across the second explicit update;
- participant failure invokes no provider and commits no state;
- a missing typed contact-outer provider reaches no half-step and commits no
  state;
- explicit outer execution does not increment `physics.fixed_step`.

## Remaining provider inventory

| Deep-chain boundary | Status after Phase 694 | Next owner/action |
| --- | --- | --- |
| `FUN_007675f0` arithmetic | native inside persistent runtime chain | closed |
| `FUN_007675f0` caller inputs | typed external provider; producer mapping incomplete | Process 1 static producer proof |
| `FUN_007afdd0` four f32 machine scalars | typed external provider; Phase 692 machine path incomplete | Process 1 machine-boundary proof |
| `FUN_00765c40` | partial native query chain; world/collision source unresolved | keep external until producer join |
| `FUN_00758b50` | full outer producer ownership not proven | keep external |
| `FUN_00766510` | multiple native subpaths exist; primary response-application transform not frozen | keep whole callback external |
| `FUN_007682c0` | arithmetic evidence exists; producer/machine boundaries incomplete | Process 1 handoff before replacement |
| `FUN_007b8810` | required anchor/order proven; refresh producer unresolved | keep external |
| solver/constraint half-step refresh | native consumers exist; retail refresh production still external | keep typed provider |
| outer-update cadence owner | not proven | explicit only; do not attach to `fixed_step()` |

## Process 3 interaction

The latest Process 3 merge, PR #1168, threads offline bootstrap into renderer
OBJECT candidate regeneration. Phase 694 does not invent a physics participant or
BODY mapping from that artifact. The new runtime entrypoint is ready to consume a
future proven resource/participant transport without weakening admission.

## Scope guard

Phase 694 does not:

- run or depend on `SHIFT.exe`;
- request a new runtime capture;
- synthesize contact inputs;
- use `std::sqrt`, `std::sin`, or `std::cos` for unresolved retail machine
  intermediates;
- infer gameplay names for opaque control/contact channels;
- schedule the explicit outer update from the native fixed-step loop;
- claim a BODY-to-world vehicle transform mapping.
