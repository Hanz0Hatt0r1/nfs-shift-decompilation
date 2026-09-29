# Phase 539 — retail material-slice duplicate closure

Phase 536 made the BMW material-binding linker archive-layout-safe, Phase 537
collapsed byte-identical top-ranked shader identities, and Phase 538 converted
the remaining ties into a runtime shader target set.

Phase 539 applies the same content-aware duplicate rule to the downstream
`bmw_real_material_slice.py` resource resolver.

The documented retail corpus combines `BMW_M3_E36.bff`,
`BMW_M3_E36_Cockpit.bff`, and `Pakfiles/Dir/RENDER.bff`. Some logical BMT,
FX, and DDS resources are intentionally copied between those archives. The
slice layer previously rejected any logical path that appeared more than once,
even when the payload bytes were identical.

The new fail-closed rule is:

1. zero copies: missing resource;
2. one copy: use it;
3. multiple copies with one payload SHA-256: one logical resource, retain the
   first archive in deterministic corpus order for provenance;
4. multiple copies with different payload SHA-256 values: hard conflict.

DDS conflicts are surfaced as `material-slice:dds-conflict:<path>`.

This change does not select a shader permutation and does not weaken the
Phase 537/538 ambiguity boundary. It only ensures that the six-primitive body
orchestrator reaches the genuine shader-attribution gate instead of failing on
archive duplication.
