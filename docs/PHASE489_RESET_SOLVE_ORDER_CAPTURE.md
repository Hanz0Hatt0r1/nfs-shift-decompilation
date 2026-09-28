# Phase 489 — reset → provider-solve ordering capture

## Goal

Phase 489 adds a monotonic runtime counter for `FUN_007b2210` reset dispatches and stores that counter in provider pre/post solver snapshots.

Provider snapshots now carry:

- `scalar_reset_event_count` — total observed reset events since probe start;
- `scalar_reset_events_since_frame_entry` — reset events observed since the latest frame-entry breakpoint.

## Ordering proof

Given a complete `scalar_reset_events.jsonl` log, the counter can be checked against the maximum reset `call_index` observed through the provider solve frame.

The frame-local counter is checked against the number of reset events tagged with the same `frame_index`.

Pre/post provider snapshots from the same frame must preserve the same reset counter. A changed counter would indicate that additional reset events occurred after the provider solve snapshot, contradicting the source execution order.

## Why this matters

Phase 488 verifies the topology of the reset event stream. Phase 489 adds a temporal boundary tying that stream directly to the provider `+0x18` solve snapshot.

Together they establish a capture-side sequence:

`frame entry → FUN_007b2210 reset events → provider +0x18 pre-solve snapshot → provider solve return`

The logic is evidence-only: it does not infer solver coefficients or matrix semantics.

## Scope boundary

The counter starts when the GDB probe process installs the frame-entry observation and is intentionally probe-local. It is not a game frame counter and is not persisted across probe restarts.

A complete event log is required for strict counter reconciliation; partial logs remain useful for raw event inspection but cannot prove completeness.