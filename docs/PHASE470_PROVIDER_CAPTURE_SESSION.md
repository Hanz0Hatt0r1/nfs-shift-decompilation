# Phase 470 — specialized-provider capture session

## Goal

Phase 470 combines the provider capture primitives into one normalized session contract.

The session accepts a `provider_pre_<id>_<hit>.json` snapshot and optionally a matching `provider_post_<id>_<hit>.json` snapshot from Phase 463.

## Integrated checks

The session validates provider/scalar/workspace shape and frame pairing, then exposes:

- provider geometry validation against the recovered static layout;
- reset-state delta from Phase 469;
- raw pre/post mutation diff from Phase 464.

All three are returned separately so a failure in one layer cannot be mistaken for a failure in another.

## Session boundary

A session with only a pre-solve snapshot is valid and can still measure reset delta. A post-solve snapshot is optional and adds mutation analysis.

The session remains storage-level. It does not convert provider workspace into the builtin logical matrix schema and does not claim provider numerical parity.

## Next use

The resulting contract is the stable input for a provider-capture CLI and, later, for correlating source-derived factor writes with real runtime mutations.
