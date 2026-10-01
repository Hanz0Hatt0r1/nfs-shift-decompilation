# Phase 644 — capture-session timeline correlation

Phase 643 gives every new retail SDF probe run an explicit
`capture_session_id` and stamps that identity onto GDB evidence. Phase 644
moves the session boundary into the Phase 637 mutation timeline gate.

## Session-aware mode

The correlator remains backward-compatible with historical pre-Phase-643
fixtures. If no mutation or timeline anchor contains `capture_session_id`, the
legacy report shape and readiness behavior are unchanged.

If any timeline-contributing record contains a session id, session-aware mode
activates and fails closed unless:

- every relation-state mutation has a valid 32-hex session id;
- every frame-entry, builtin/provider-solve, scalar-reset and post-solve anchor
  has a valid 32-hex session id;
- all valid session ids are identical.

The resulting timeline records the normalized top-level
`capture_session_id`. Correlated mutation events and visible neighboring
anchors retain the same identity.

## Fail-closed cases

Session-aware correlation rejects:

- a missing mutation session id;
- an invalid mutation session id;
- a mutation session mismatch;
- a missing anchor session id;
- an invalid anchor session id;
- an anchor session mismatch.

These checks run in addition to the existing event-sequence, frame-entry,
callsite and slot validation.

## Replay compatibility

The Phase 641 evidence-bundle replay path reuses the same Phase 637 correlator.
A Phase 643+ bundle therefore recomputes the same session-aware timeline after
extraction. Historical unstamped bundles remain replayable through the legacy
path.

## Evidence boundary

Session consistency proves that the correlated records belong to one declared
probe capture session. It is not an external authenticity signature and does
not establish gameplay meaning, scheduler timing or native mutation admission.

Authentic retail runtime evidence remains required before relation-state
mutation can be scheduled in the native runtime.
