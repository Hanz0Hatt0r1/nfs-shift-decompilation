# Phase 699 — deepest native vehicle external-provider frontier

## Role

`SHIFT.NativeVehicleExternalProviderFrontier/1` is the machine-readable
coordination graph for the deepest persistent native vehicle chain. It is not a
physics implementation and never promotes a provider merely because a nearby
identity or renderer boundary became ready.

Source and builder:

```text
src/physics/native_vehicle_external_provider_frontier.py
tools/build_native_vehicle_external_provider_frontier.py
```

Classification remains:

```text
already proven producer     -> implement_now
static frontier available   -> request_process1_static_proof
runtime-only evidence       -> remain_blocked_runtime_only
```

## Phase 708 refresh status

This document now reflects:

- Process 1 #1208 — positive retail `SHIFT.GlobalVehicleBodyOwnerIdentity/1`;
- Process 1 #1210 — physical `SHIFT.BMWBody0BindPoseWriterABI/1`;
- Process 2 Phase 707 — native retail BODY-owner identity producer;
- Process 3 Phases 647-649 — live Vulkan upload and freshness-gated Phase706
  renderer sink.

Current provider inventory is still:

```text
external providers = 9
implement_now = 0
Process 1 handoffs = 9
runtime-only blocked = 0
```

The count remains nine because #1208 closes a cross-chain identity join, not the
producer semantics of any of the nine Phase 697/701 injected boundaries.

## Remaining provider inventory

| Boundary | Current API | Remaining proof |
| --- | --- | --- |
| complete `FUN_00765c40` | generic `contact_factor` callback | complete/separable local work, query world-position producer, collision-provider ownership |
| `FUN_00758b50` | generic `wheel_update` callback | complete inputs/writes/nested work and wheel/control ownership |
| `FUN_00766510` | generic `contact_response` callback | primary response application into `FUN_007baa70` and caller-state producers |
| `FUN_007675f0` caller inputs | `Fun007675f0ContactOuterInputProvider` | producers/refresh timing for all ten typed inputs |
| `FUN_007682c0` effect production | `Fun007682c0EffectProvider` | exact magnitude/x87 path and complete response inputs |
| `FUN_007682c0` BODY `+0x50` application | `Fun007682c0AccumulatorDeltaConsumer` | exact destination BODY pointer/record provenance at the application site, joined to proven retail BODY 0 |
| `FUN_007afdd0` f32 scalars | `Fun007afdd0ScalarProvider` | exact stores/returns, sqrt/trig provenance, floating-control state |
| `FUN_007b8810` | `Fun007b8810PostHalfStepCallback` | complete refresh producer semantics |
| `FUN_00765470` refresh | `Fun00765470MachineScalarHalfStepProvider` | producer ownership plus exact per-half-step refresh/reuse schedule |

## Identity join is closed

Process 1 #1208 commits:

```text
global vehicle base 0x00c13700
  -> pointer field +0x339c
  -> BODY-array owner
  -> retail BMW chassis BODY 0
```

The BODY-array owner pointer is not asserted equal to the global vehicle base.
Phase 707 consumes the contract through the existing Phase 703/698/700 path and
provides retail Phase 705/706 wrappers without caller-injected identity.

Therefore `body_to_vehicle_identity` is now a closed cross-chain join. The
historical targeted `FUN_00765470` receiver proof must not be requested again.

This does **not** by itself close `FUN_007682c0` delta application. That row still
needs proof that the exact destination record at the application site is the
proven chassis BODY 0 record.

## BODY0 bind frontier after Process 1 #1210

#1210 proves the physical pose-writer ABI for `FUN_007b7840`, but explicitly does
not prove semantic roles:

```text
BODY0_pointer_proven = false
BODY0_bind_origin_proven = false
BODY0_bind_basis_proven = false
BODY0_bind_frame_proof_ready = false
```

Consequently Phase 704/705/706 stay fail-closed on
`SHIFT.BMWBody0BindFrameProof/1`. Physical register/stack placement is not a
license to infer BODY0 pointer, origin, or basis meaning.

The next static bind work is now narrowly:

1. stack argument value provenance at the proven pose-writer callsites;
2. parameter semantic roles;
3. target pointer -> retail chassis BODY 0 join;
4. source-backed bind origin/basis semantics.

## Renderer transport is no longer the blocker

Process 3 now provides:

```text
Phase 646  dynamic vehicle transform core
Phase 647  SHIFT.LiveVehicleVertexBufferUpload/1
Phase 648  shift_runtime explicit regression wiring
Phase 649  SHIFT.PersistentVehicleVulkanUpload/1
```

Phase 649 reads the current Phase 706 state before GPU access, waits the supplied
frame fences, then reuses Phase 647. Stale transform state is rejected before
vertex memory mutation.

Thus the BODY-pose -> renderer join is blocked on the semantic BODY0 bind witness
(and later a proven production commit schedule), not on another renderer
transport layer.

## Scheduling and machine-scalar guards

Nothing in #1208, #1210, Phase 707, or Phases 647-649 proves the retail outer
cadence. The deep update remains explicit:

```text
fixed_step auto-schedule forbidden
```

Likewise unresolved machine boundaries still forbid replacing retail paths with
host `sqrt`, `sin`, or `cos`.

## Regression / CI

```text
tests/test_native_vehicle_external_provider_frontier.py
.github/workflows/native-physics-phase699.yml
```

The Phase 708 refresh regression verifies:

- exactly nine external provider rows and `implement_now = []`;
- positive #1208/Phase707 retail identity;
- no reintroduction of update-child pointer equality;
- no stale request for the closed `FUN_00765470` receiver proof;
- #1210 physical ABI without semantic bind promotion;
- Process 3 Phases 647-649 as closed renderer transport;
- all scheduling and host-math guards remain fail-closed.

No original game execution or new runtime capture is used or required.
