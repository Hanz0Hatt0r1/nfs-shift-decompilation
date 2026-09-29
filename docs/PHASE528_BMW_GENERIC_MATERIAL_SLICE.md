# Phase 528 — generic BMW body material slices

Phase 528 removes the paint-only restriction from the retail BMW M3 body
material pipeline while preserving the stricter paint proof introduced earlier.

## Primitive-selected material

`build_real_bmw_material_slice()` now derives the material BMT from the exact
selected MEB primitive:

```text
primitive.material (.mtx) -> exact sibling .bmt
```

The BMW golden gate still verifies the exact MEB identity, primitive index,
`first_index`, `index_count`, material reference and mesh counts.

The canonical body LODA contains six primitives using five material references:
BADGING, PAINT, GENERIC_WINDOWS, GENERIC_GLOSS_BLACK and LIGHTSGLASS. All five
can now enter the same retail linker path.

## Generic binding gate

Every material must pass `SHIFT.BMWGenericMaterialBindingGate/1`. It fails
closed unless the linker provides:

- a unique material shader selection;
- an exact FXO candidate;
- a unique vertex/pixel shader pair;
- a translated `SHIFT.LinkedShaderPair/1`;
- a 64-character `SHIFT.ShaderPermutationIdentity/1` identity;
- no linked-shader translation error;
- no unresolved material textures.

## Paint remains stricter

For `BMW_M3_E36_PAINT.mtx`, the existing BMW paint material contract and paint
shader gate remain additional mandatory checks. Non-paint primitives do not
inherit paint-specific assertions.

## Native path

Phase 527 already adapts complete material slices into per-submesh Vulkan child
bundles. Phase 528 supplies that adapter with canonical non-paint slices when
their retail shader/resource evidence resolves uniquely.

This phase does not claim that all non-paint permutations are already resolved.
Ambiguous FXO selection, missing DDS resources, unsupported shader translation
or incomplete provenance remains an explicit blocker.
