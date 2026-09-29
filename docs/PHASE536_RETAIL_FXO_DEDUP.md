# Phase 536 — retail FXO corpus deduplication and family scoping

Phase 536 fixes two issues exposed by running Phase 533 against the real
BMW_M3_E36, BMW_M3_E36_Cockpit and RENDER archives.

## Duplicate retail resources

The vehicle and cockpit archives intentionally repeat many shader-cache
resources. The previous BMW retail linker named FXO candidates as
`archive::resource-path`, so two byte-identical copies of the same logical
resource could become two different ranked candidates and incorrectly make an
otherwise unique selection ambiguous.

Phase 536 treats byte-identical duplicate resource paths as one logical retail
resource. Archive order remains deterministic and the primary archive copy is
retained for provenance.

If the same normalized resource path occurs with different payload bytes across
archives, the linker fails closed with a conflicting-duplicate error.

The same duplicate-resource rule is also used for BMT, MEB and FX source
lookups.

## Shader-family candidate scope

FXO enumeration is now restricted to the family referenced by the selected
BMT shader, using the same cache-name normalization already used by the general
render pipeline:

```text
render/shaders/bodywork.fx
  -> bodywork
render/shaders/cache/render_shaders_bodywork_<hash>.fxo
  -> bodywork
```

This avoids reflecting unrelated shader families and makes real retail
admission practical without changing the ranking criteria inside
`material_linker.link_material()`.

## Provenance

The retail material-binding report now records:

- `fxo_shader_family`;
- unique `fxo_candidate_count`;
- `fxo_duplicate_copy_count`.

The raw BFFs remain external evidence and are not committed.

## Evidence boundary

Family scoping and duplicate collapse do not select a shader permutation.
Every remaining candidate still passes through the existing sampler, uniform,
specialization, vertex-pair, translation and permutation-identity gates.

Phase 536 therefore removes archive-layout ambiguity only. True shader-pair
ambiguity remains a blocker.
