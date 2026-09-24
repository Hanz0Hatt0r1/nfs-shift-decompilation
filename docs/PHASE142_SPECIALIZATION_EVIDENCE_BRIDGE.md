# Phase 142 — specialization evidence bridge

`material_linker.link_material()` exposes specialization analysis as a structured
`specialization` record with a `requested` flag set. Phase 142 makes the BMW M3 paint
contract consume that field directly when no flat specialization list is present.

This removes a representation bug where a specialization dict would otherwise be
converted into its dictionary keys.

## Evidence flow

`BMT shaderparams -> material_specialisations() -> feature_indicators().requested ->
MaterialBinding/1.specialization -> compile_material() -> M3 paint contract/shader gate`.

No new feature flags are inferred in this phase.

## Boundary

`requested` expresses material-side feature evidence. It does not prove that a specific
FXO permutation was compiled or used at runtime. The shader gate still requires unique
exact FXO selection, VS/PS pairing and a valid permutation identity.