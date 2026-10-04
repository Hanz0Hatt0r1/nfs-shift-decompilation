# Phase 536 — retail FXO corpus deduplication and family scoping

> **Playable-resource supersession (Phase 654).** The duplicate-collapse rules
> below describe the historical Phase 536 linker and remain useful for FXO
> **program-byte equivalence**. They are no longer semantic resource-identity
> authority for the playable BMW path. Phase 654 requires exactly one admitted
> MEB/BMT/FX/DDS occurrence even when duplicate payload bytes are identical, and
> never promotes an FXO byte-equivalence class to one semantic source resource.

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

The same historical duplicate-resource rule is also used for BMT, MEB and FX
source lookups inside the Phase 533 helpers. Phase 654 explicitly revalidates
those selected resources before playable admission and rejects 2+ occurrences
regardless of byte equality.

## Shader-family candidate scope

FXO enumeration is restricted to the family referenced by the selected BMT
shader, using the same cache-name normalization already used by the general
render pipeline:

```text
render/shaders/bodywork.fx
  -> bodywork
render/shaders/cache/render_shaders_bodywork_<hash>.fxo
  -> bodywork
```

This avoids reflecting unrelated shader families and makes real retail admission
practical without changing the ranking criteria inside
`material_linker.link_material()`.

## Provenance

The retail material-binding report records:

- `fxo_shader_family`;
- unique `fxo_candidate_count`;
- `fxo_duplicate_copy_count`.

The raw BFFs remain external evidence and are not committed.

For Phase 536 those counters establish byte-equivalent cache-copy handling. They
do not, after Phase 654, prove one semantic archive occurrence for the playable
resource graph.

## Evidence boundary

Family scoping and duplicate collapse do not select a shader permutation. Every
remaining candidate still passes through the existing sampler, uniform,
specialization, vertex-pair, translation and permutation-identity gates.

For shader execution, byte-identical FXO copies may remain a program-byte
equivalence class. For playable MEB/BMT/FX/DDS resource identity, Phase 654 is
the authoritative stricter boundary: archive order, first duplicate and byte
identity cannot select a semantic resource occurrence.
