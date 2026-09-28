# Phase 501 — scalar-reset event/effect correlation

## Goal

Phase 501 correlates the Phase 485/487 `scalar_reset_events.jsonl` stream with the Phase 494 `provider_reset_effects.jsonl` stream.

The join key is the probe-local monotonic reset counter:

`scalar_reset.call_index == reset_effect.reset_event_count`

## Integrity checks

Each correlation additionally requires:

- matching provider id;
- matching frame index;
- matching selector;
- matching provider vtable when present.

Missing events on either side, duplicate counters, or mismatched metadata block the correlation rather than pairing by list position.

## Why this matters

Phase 485 proves that a reset call occurred and records its selector/callsite. Phase 494 measures the actual post-return effect on the selector's diagonal and output sentinel cells.

Phase 501 now joins those two facts into one evidence record:

`caller call → selector → provider +0x1c → measured 1.0/0.0 effect`

This is the first direct runtime chain from the scalar reset dispatch through the provider virtual call to an observed storage effect.

## Scope boundary

The correlation does not expand the two sentinel cells into the full case footprint, does not infer matrix semantics, and does not claim the provider solver itself is numerically reconstructed.