# Phase 491 — scalar-reset evidence CLI

## Goal

Phase 491 adds `tools/verify_specialized_provider_reset_capture.py`, a one-command frontend for the Phase 490 reset-evidence manifest.

## Basic use

    python tools/verify_specialized_provider_reset_capture.py \
      --events scalar_reset_events.jsonl

This validates the complete scalar-reset stream and prints the frame/group/provider summary.

## With provider solve snapshots

    python tools/verify_specialized_provider_reset_capture.py \
      --events scalar_reset_events.jsonl \
      --provider-pre provider_pre_0_000001.json \
      --provider-post provider_post_0_000001.json

Provider pre/post arguments can be repeated in matching order. The CLI rejects unequal list lengths rather than silently pairing the wrong snapshots.

## Exit code

`0` means the requested evidence checks are ready.

`2` means validation is blocked or the event stream is structurally inconsistent.

## Scope boundary

The CLI is an evidence aggregator. It does not infer matrix semantics, physical units, or provider classes, and it does not turn a numerically solved reference into a claim of retail binary equivalence.