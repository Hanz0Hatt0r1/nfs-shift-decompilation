# Phase 488 — scalar reset event sequence validation

## Goal

Phase 488 validates the runtime `FUN_007b2210` event stream against the exact callsite topology recovered in Phase 486.

## Per-frame rules

Within one frame the source groups must occur in this order:

`JOINT/HINGE → SECONDARY → BAR`

Each active JOINT/HINGE record emits exactly three calls with ordinals `0,1,2`.

Each active SECONDARY record emits exactly two calls with ordinals `0,1`.

Each active BAR record emits exactly one call with ordinal `0`.

If a breakpoint is missed inside a group, the ordinal sequence becomes invalid and the frame is reported as not ready.

## Why this is useful

Phase 485 captures every scalar reset as an individual event. Phase 488 now determines whether the observed event stream is structurally consistent with the retail call topology.

This is particularly useful for diagnosing instrumentation problems: a provider may be correct while the capture itself is incomplete. The sequence validator detects that distinction without examining solver coefficients.

## Inline attribution

Phase 487 already stores the Phase 486 callsite attribution inside each JSONL event. Phase 488 accepts that embedded attribution or independently resolves the caller return address when the field is absent.

## Scope boundary

This phase validates call ordering and group cardinality only. It does not infer which constraint object produced a selector, does not assign matrix meaning to the selector, and does not claim numerical solver parity.