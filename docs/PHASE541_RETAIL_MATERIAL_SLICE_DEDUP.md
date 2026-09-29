# Phase 541 — retail BMW material-slice duplicate closure

Phase 541 applies the established retail content-deduplication rule to
`bmw_real_material_slice.py`, downstream of the Phase 536 material-binding
dedup and the Phase 538–540 runtime shader attribution pipeline.

For BMT/MEB, FX source and material DDS lookup across
`BMW_M3_E36.bff`, `BMW_M3_E36_Cockpit.bff` and
`Pakfiles/Dir/RENDER.bff`:

- zero copies remain missing evidence;
- one copy is accepted;
- multiple copies with identical payload SHA-256 are one logical resource and
  retain deterministic first-archive provenance;
- multiple copies with different payload bytes fail closed.

DDS byte conflicts are surfaced as `material-slice:dds-conflict:<path>`.

This changes only archive resource identity handling. It does not select a
shader permutation or weaken the same-instance D3D9 attribution gate.
