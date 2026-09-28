# Phase 499/500 — provider capture bundle index and CLI

## Goal

Phases 499–500 make the provider runtime capture directory self-describing. The tooling scans `provider_pre_<id>_<hit>.json` and `provider_post_<id>_<hit>.json`, pairs them by provider id and hit, and optionally correlates the pair with `scalar_reset_events.jsonl` by frame index.

## Pairing rules

Each `(provider_id, hit)` key can have at most one pre and one post snapshot.

A provider bundle is structurally ready only when its pre snapshot exists. A post snapshot is optional, allowing pre-only diagnostics.

Unknown filenames are ignored rather than guessed.

## Integrated analysis

For every bundle the analyzer runs the Phase 470 provider session contract. With a post snapshot it also runs pre/post reset→solve counter checks.

When `--reset-events` is supplied, only reset events tagged with the bundle's `frame_index` are associated with that provider solve. This keeps multiple provider frames from contaminating each other.

## CLI

    python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR

With reset events:

    python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR \
      --reset-events CAPTURE_DIR/scalar_reset_events.jsonl \
      -o provider_bundle_manifest.json

## Scope boundary

This layer is a file/provenance orchestrator. It does not infer matrix semantics or numeric provider equivalence. Raw provider workspace interpretation remains in the separate reset/factor/storage analysis layers.