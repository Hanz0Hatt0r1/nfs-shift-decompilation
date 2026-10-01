# Phase 645 — portable evidence capture-session identity

Phase 644 makes relation-mutation timeline correlation session-aware. Phase 645
extends the same boundary to the deterministic portable evidence ZIP and its
independent verifier.

## Builder contract

For launcher-produced captures, the builder reads the Phase 643 session id from
the host-local `probe_manifest.json`. The probe manifest itself remains
excluded from the portable archive.

If the launcher declares a session, or if any packaged evidence record already
contains `capture_session_id`, the bundle becomes session-aware. The builder
then requires every packaged JSON/JSONL evidence record to carry the same valid
32-hex id.

A session-aware `evidence_manifest.json` records:

- `capture_session_required = true`;
- `capture_session_id = <normalized 32-hex id>`.

The manifest id is taken from the launcher declaration when available;
otherwise it is inferred from the first valid evidence id. Any missing,
malformed or mismatched record blocks package readiness.

Historical evidence with no session declaration and no session-stamped records
keeps the legacy manifest shape.

## Independent verifier

The Phase 640 verifier does not trust the builder. It independently parses the
portable manifest and every declared evidence payload inside the ZIP.

For a session-aware archive it requires:

- a valid manifest session declaration;
- a valid manifest session id;
- a session id on every JSON object and every non-empty JSONL record;
- exact equality between every record id and the manifest id.

These checks happen after the ordinary ZIP metadata, file list, size and
SHA-256 checks, but do not depend on replay. Rehashing a payload after changing
or deleting its session id therefore does not bypass the session gate.

If raw evidence is session-stamped but the portable manifest drops the session
declaration, verification also fails closed.

## Replay

Phase 641 replay remains unchanged structurally. A valid Phase 645 archive
passes independent session verification first, is materialized, and then
recomputes the Phase 644 session-aware timeline. Exact embedded/recomputed
timeline equality remains mandatory.

## Trust boundary

The session id is capture provenance, not a cryptographic signature. An
attacker capable of rebuilding an entirely new legacy-shaped archive can still
present it as legacy evidence; Phase 645 does not claim external authenticity.

For normal Phase 643+ launcher captures, accidental stale/mixed/partially
stripped evidence is now blocked at launcher, timeline, package, verification
and replay layers. Native relation-state scheduling remains capture-gated.
