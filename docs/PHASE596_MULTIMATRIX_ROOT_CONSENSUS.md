# Phase 596 — independent MultiMatrix root consensus

Phase 594 can invert one MatrixNumber slot world matrix into a current
MultiMatrix root. Phase 595 can independently narrow exact runtime IMB resources
to pre-admission SGB OBJECT candidates without using a later RenderBinding
binding index.

One runtime observation is still insufficient because no retail world-matrix
register has been assigned. Any contiguous four-register VS constant window
could be tested as a matrix.

Phase 596 adds a stricter cross-resource consensus witness.

## Contract

New contract:

`SHIFT.SGBMultiMatrixRootConsensus/1`

implemented by:

`src/scene/sgb_multimatrix_root_consensus.py`.

Inputs:

- `SHIFT.SGBRuntime/1`;
- `SHIFT.SGBRuntimeObjectCandidateJoin/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`.

## Observation policy

Only draw-local constant state already retained for strong-attributed runtime
draws is examined.

For every eligible MatrixNumber OBJECT candidate, Phase 596 scans every
contiguous four-register vertex-constant window and tests both:

- row-major;
- exact transpose.

The register and layout remain observational. No retail world-register semantic
is assigned.

Each window is passed through the Phase 594 root solve for that candidate's
selected MultiMatrix slot. A hypothesis survives only when Phase 594's existing
round-trip evaluator reproduces the observed slot world matrix.

## Consensus rule

A wrapper root may be promoted only when one exact float32 root value is
independently supported by:

1. at least two distinct exact runtime resource identities
   (`archive + path + SHA-256`); and
2. at least two distinct cumulative local-transform chains.

The second condition is important. It prevents two resources selecting the same
slot/local chain from turning a shared renderer-global matrix constant into a
false root witness.

Root identity is compared as exact IEEE-754 float32 bytes after solving.

## Ambiguity

If the same wrapper has two or more independently supported root values, the
wrapper remains blocked.

The report keeps all candidate root sets and does not rank them.

A single resource never authorizes a root, regardless of how many draws or
constant windows it supplies.

## SGB owner lookup

Phase 596 resolves each Phase 595 candidate back into the original
`SHIFT.SGBRuntime/1` using:

- wrapper chunk (`SUMM` / `NODE`);
- wrapper source record index;
- recursive `object_path`.

The MatrixNumber OBJECT's parent LOD/HIERARCHY report is then used as the
MultiMatrix owner for Phase 594.

This lookup is pre-admission and does not use a RenderBinding binding index.

## Promotion boundary

A unique consensus row sets:

`authorizes_current_wrapper_root = true`.

That authorizes only the **current root matrix for the wrapper**.

It does not by itself authorize:

- OBJECT↔runtime draw attribution;
- a retail world-matrix register;
- SceneGraph update history;
- RenderBinding or draw admission.

Once a wrapper root is proven, however, all source-backed MatrixNumber child
slots under that wrapper can be re-evaluated through the existing MultiMatrix
contract in a later phase.

## CLI

```bash
python shift_importer.py sgb-multimatrix-root-consensus \
  out/sgb-runtime.json \
  out/runtime-object-candidates.json \
  out/silverstone-runtime-attribution.json \
  out/multimatrix-root-consensus.json
```

## Next

The next scene step is to consume ready Phase 596 wrapper roots back into
`SHIFT.SGBObjectRenderHandoffSet/1` and recompute blocked MatrixNumber world
matrices before `SHIFT.SGBRenderBindingAdmission/1`.

That promotion must remain wrapper-scoped and must not claim that the historical
SceneGraph update sequence was recovered.
