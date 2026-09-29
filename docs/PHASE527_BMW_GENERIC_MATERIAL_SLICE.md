# Phase 527 — generic BMW body material slices

Phase 527 removes the paint-only restriction from the retail BMW M3 body
material pipeline without weakening the existing paint proof.

## Canonical primitive material selection

`build_real_bmw_material_slice()` now derives the BMT from the selected MEB
primitive:

```text
primitive.material (.mtx) -> exact sibling .bmt
```

The exact MEB resource identity, primitive index, `first_index`,
`index_count`, material reference and mesh counts are still checked against
the BMW golden manifest.

The known body LODA evidence contains six primitives and five material
references, so BADGING, PAINT, GENERIC_WINDOWS, GENERIC_GLOSS_BLACK and
LIGHTSGLASS can now enter the same retail linker path.

## Generic shader/permutation gate

`SHIFT.BMWGenericMaterialBindingGate/1` fails closed unless the selected
material has all of the following:

- unique material-linker shader selection;
- an exact FXO candidate;
- a unique vertex/pixel shader pair;
- a translated `SHIFT.LinkedShaderPair/1`;
- a 64-character `SHIFT.ShaderPermutationIdentity/1` identity;
- no linker translation error;
- no unresolved material textures.

This gate is material-agnostic and is required by every BMW material slice.

## Paint remains stricter

For `BMW_M3_E36_PAINT.mtx`, the existing BMW paint material contract and
paint shader gate remain additional mandatory checks. Non-paint primitives do
not run or inherit those paint-specific assertions.

## Evidence boundary

Phase 527 does **not** claim that every non-paint material has a unique retail
shader permutation. It makes those materials observable through the same
fail-closed BMT -> FX -> FXO -> RenderCommand pipeline.

A material whose retail archives resolve to an ambiguous shader, missing
texture, unsupported translation, or incomplete provenance remains blocked.

The next step is to run the canonical non-paint primitives against the retail
BMW/RENDER corpus and feed the first distinct fully-ready material
permutations into the Phase 524-526 native multi-draw path.
