# Phase 716 — explicit runtime scheduler authority

## BLOCKER

Process 2 P2.D requires the production runtime to distinguish current host-development pacing from any future retail outer-update scheduler/cadence handoff. Host `1/60` must never silently satisfy a retail scheduling gate.

## INPUT

- `native_runtime/src/runtime_loop_policy.hpp` continuous host pacing;
- the canonical fail-closed rule that host `1/60` pacing is not retail outer-update cadence;
- no positive Process 1 retail scheduler/cadence artifact is currently merged.

## OUTPUT

`RuntimeLoopPolicy` now carries an explicit `RuntimeSchedulerAuthority`:

```text
HostDevelopment
RetailEvidence
```

All currently constructed bounded/scripted/continuous policies remain `HostDevelopment`, with `retail_cadence_admitted == false`.

The continuous wall-clock pacer rejects any policy that is switched to `RetailEvidence` while retaining host pacing. Therefore a future positive Process 1 cadence handoff cannot become retail-admissible merely by reusing the existing `1/60` timer.

Machine-readable Process 2 handoff:

```text
SHIFT.Process2RuntimeSchedulerAuthority/1
```

in `evidence/process2_runtime_scheduler_authority.json`.

## CONSUMER

The next positive Process 1 scheduler/cadence artifact can be parsed by a strict Process 2 loader and select `RetailEvidence` explicitly. Its proven scheduling mechanism must then drive admitted outer updates without inheriting `continuous_wall_clock_pacing`.

## GATES_CHANGED

```text
scheduler_authority_explicit = true
host_1_60_is_retail_cadence = false
retail_host_fallback_rejected = true
retail_cadence_admitted = false
```

## LIMITS

This phase does not prove scheduler ownership, update multiplicity, cadence, catch-up/drop behavior, or any Process 1 artifact schema. It does not alter BODY0 bind admission, persistent BODY state, transform freshness, or Vulkan transport.

## TESTS

- `shift_runtime_loop_policy_check` verifies current host-development scheduling and executes the retail-authority/host-pacer rejection path.
- `tests/test_process2_runtime_scheduler_authority.py` locks the source and machine-readable fail-closed contract.

## NEXT_OWNER

Process 1 remains owner of retail scheduler/cadence proof. Process 2 consumes the exact positive handoff when it lands.
