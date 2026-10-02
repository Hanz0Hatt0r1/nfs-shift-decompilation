# Phase 607 — layout-aware runtime pipeline candidate join

## Production observation

The first Phase 606 Silverstone join contains 10 runtime pipeline signatures and
1,581 target draws.

Only two runtime signatures have an exact static VS+PS candidate pair. Those
two signatures cover 136 draws. The other eight signatures still overlap the
static target set by exact pixel-shader byte hash, but their observed VS hashes
are not present in the corresponding static pair targets.

The Phase 606 output is also unnecessarily large because each static binding is
repeated once per matching FXO offset.

## Source-backed layout fallback

Phase 607 adds a weaker candidate path for static targets whose own strength is
already `prefilter-only`.

A runtime pipeline may enter this fallback only when all of the following hold:

- exact pixel-shader byte SHA-256 matches;
- the static target is `prefilter-only`;
- the static IMB vertex properties are all mapped by the proven neutral IMB
  ABI;
- the byte stride derived from those source properties equals observed D3D9
  stream 0 stride.

The production Silverstone layouts derive naturally to the observed runtime
classes:

- `200,460,220,130` -> 36 bytes;
- `200,460,220,240,250,130` -> 60 bytes;
- `200,460,220,240,250,130,231` -> 72 bytes;
- `200,460,220,240,250,130,580,310` -> 80 bytes.

Unknown/deferred IMB properties return no derived stride and therefore cannot
pass the fallback.

## Fail-closed strength handling

An `exact-pair` static target never degrades to the PS+stride fallback merely
because the runtime VS differs. Such a mismatch remains below candidate
admission for that target.

## Compact candidate rows

Candidate output is now grouped by static primitive binding rather than
duplicating the same binding payload for every FXO program/vertex offset.

Each compact candidate records:

- binding/resource/material identity;
- source vertex properties and derived static stride;
- evidence kind;
- matched target identity;
- number of concrete matching variants.

The full Phase 568 target-set input remains the authoritative location for all
individual FXO offsets.

## Boundary

`pixel + static vertex stride` is a narrowing observation only.

It does not prove:

- runtime VS identity;
- runtime IMB resource identity;
- primitive identity;
- same-instance identity;
- shader or render admission.

Promotion still requires exact runtime resource identity, exact primitive draw
range and the existing strong Phase 572 gates.
