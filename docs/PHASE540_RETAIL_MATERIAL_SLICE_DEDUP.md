# Phase 540 — retail BMW material-slice duplicate closure

Phase 536 made the BMW material-binding linker archive-layout-safe, Phase 537
collapsed byte-identical top-ranked shader identities, Phase 538 produced a
capture target set, and Phase 539 matches those targets to same-instance D3D9
draw snapshots.

Phase 540 closes the remaining duplicate-resource assumption in
`bmw_real_material_slice.py`.

The documented retail corpus combines `BMW_M3_E36.bff`,
`BMW_M3_E36_Cockpit.bff`, and `Pakfiles/Dir/RENDER.bff`. Some logical BMT,
FX and DDS resources are intentionally present in more than one archive. The
slice builder previously required every logical path to occur exactly once,
which could stop the six-primitive orchestrator before the Phase 538/539 shader
attribution boundary.

The fail-closed rule is now:

1. zero copies: missing resource;
2. one copy: accept it;
3. multiple copies with identical payload SHA-256: one logical resource,
   retaining deterministic first-archive provenance;
4. multiple copies with different payload bytes: hard conflict.

DDS conflicts are surfaced separately as
`material-slice:dds-conflict:<path>`.

This phase does not choose a shader permutation, change candidate ranking, or
weaken the same-instance attribution requirement.
