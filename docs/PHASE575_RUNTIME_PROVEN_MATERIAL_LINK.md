# Phase 575 — runtime-proven MaterialBinding relink

Phase 574 admits a runtime-proven shader identity but intentionally leaves
`render_admission=false`. Phase 575 consumes that admission inside the existing
material linker and rebuilds the complete material/shader contract from the
proven VS/PS identity.

## Why exact vertex offsets matter

Silverstone static ranking can leave one pixel program paired with several
equally valid vertex programs. A runtime capture can distinguish those variants
by VS byte hash, but rebuilding the material with the old
`pair_selected_pixel()` path would reintroduce the static ambiguity.

The shader-interface layer therefore exposes:

`pair_exact_offsets(data, vertex_offset, pixel_offset, properties=...)`

and the ranking/target/match/admission path preserves the concrete
`vertex_program_offset` for every candidate variant.

The material linker also expands an ambiguous static VS tie into separate
candidate rows before ranking. Each row carries:

- pixel program offset;
- vertex program offset;
- permutation identity SHA-256;
- pair byte SHA-256;
- vertex byte SHA-256;
- pixel byte SHA-256.

## Runtime admission selector

`material_linker.link_material(..., runtime_admission=...)` now accepts one
Phase 574 admitted binding.

The runtime selector requires:

- `shader_selection_admitted=true`;
- selected runtime score >= 80;
- at least one strong identity/hash field;
- all supplied permutation/pair/VS/PS hashes to match the static candidate;
- exactly one static content identity after matching;
- an exact candidate with a concrete vertex program offset.

It does not trust FXO filename or program offset as the primary identity.

## Content-equivalent copies

Multiple FXO locations may contain the same proven shader bytes.

When all matching candidates collapse to one content identity, Phase 575 keeps
all matching locations as provenance and chooses a deterministic representative
for reconstruction. This does not promote filename/order into evidence.

If matching candidates represent more than one static content identity, the
runtime admission remains blocked.

## Rebuilt material state

Once the runtime candidate is accepted, the linker replaces the static
ambiguous `best` candidate and rebuilds all downstream state from its exact
VS/PS offsets:

- D3D9 sampler register assignments;
- exact shader-pair interface;
- exact vertex-format bindings;
- GLSL translation through `translate_pair_blob()`;
- material uniform binding through `link_selected_pair()`;
- `SHIFT.ShaderPermutationIdentity/1`.

The returned `SHIFT.MaterialBinding/1` records:

- `selection_status = "unique"`;
- `selection_source = "runtime-admission"`;
- `runtime_selection.ready = true`;
- the selected full FXO candidate;
- matching static locations and admission provenance.

A supplied but invalid/weak admission forces
`selection_status = "blocked"` and clears the selected FXO instead of falling
back to static ranking.

## Generic render gate

The Phase 575 regression suite proves that a runtime-admitted ambiguous
synthetic material passes the existing generic native material gate:

`validate_generic_material_binding()`.

This means runtime proof can now produce the same complete MaterialBinding ABI
expected by StaticDraw/RenderCommand.

## Boundary

Phase 575 does not yet decide which scene primitive receives which admission.
The material linker receives one already-joined Phase 574 admission.

The next step is a per-binding scene bridge:

`IMB primitive binding + Phase 574 admission → runtime-proven MaterialBinding
→ StaticDraw → RenderCommand`.

That bridge must still verify IMB path/SHA, primitive index and draw range before
injecting the admission into the corresponding scene primitive.
