# Phase 537 — retail BMW permutation identity

Phase 536 made the retail BMW/Cockpit/RENDER corpus archive-layout-safe by
scoping FXO enumeration to the selected shader family and collapsing identical
resource paths.

Phase 537 executes that normalized corpus and tightens the remaining
permutation ambiguity rule.

## Bytecode identity

Two top-ranked candidates are not distinct merely because they come from
different FXO filenames or program offsets. If a candidate has a proven
`SHIFT.ShaderPermutationIdentity/1`, that identity is the primary tie
identity. Otherwise the shader-pair SHA-256 is used. File/program location is
only a fallback when byte hashes are unavailable.

This removes false ambiguity while retaining fail-closed behavior for genuinely
different shader bytecode.

## Retail observation

The real v1.02 corpus used here is identified by SHA-256 in
`evidence/bmw_m3_e36_retail_material_admission_observation.json`.

All five unique BMW body materials resolve BMT, FX and required material
textures. None is admitted yet: after archive dedupe, family scoping and
bytecode-identity collapse, multiple distinct permutations still satisfy the
current static ranking.

The remaining blocker is therefore evidence-bearing, not an archive-layout or
resource-resolution problem.

## Next gate

Attribute one concrete FXO VS/PS pair to each canonical material using either:

- a same-instance runtime draw capture; or
- a stronger source-backed static discriminator that uniquely explains the
  selected retail permutation.

The linker must not choose the first or highest-ranked distinct permutation
without that additional evidence.
