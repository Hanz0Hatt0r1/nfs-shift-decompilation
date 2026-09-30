# Phase 597 — apply owner-scoped runtime roots to SGB handoffs

Phase 596 proves a current MultiMatrix root only when independent runtime
resources and distinct static local chains converge to one exact float32 root
without assigning a retail world-register semantic.

Phase 597 feeds only those ready roots back into the existing SGB OBJECT
handoff/evaluation path before scene admission.

## Scope correction

The Phase 596 consensus key is refined from wrapper-only to:

`wrapper chunk + wrapper source record index + recursive owner_path`.

This matters because one SUMM/NODE wrapper may contain nested LOD/HIERARCHY
objects, each owning an independent MultiMatrix table.

Two nested owners may never support each other merely because they are stored
under the same wrapper.

A ready consensus row therefore authorizes:

`authorizes_current_multimatrix_owner_root = true`.

The older wrapper-root flag is true only when `owner_path == []`.

## Handoff application

`build_sgb_object_render_handoff_set()` now accepts an optional
`SHIFT.SGBMultiMatrixRootConsensus/1`.

For every recursive OBJECT row it derives the immediate owner key:

```text
(wrapper chunk, wrapper source record index, object_path[:-1])
```

If one ready Phase 596 consensus exists for that exact owner, its current root
is passed into the already-existing `build_object_render_handoff()` path.

The ordinary source-backed MultiMatrix evaluator then computes the selected
MatrixNumber world matrix.

No separate transform implementation is introduced.

## Provenance

Consensus-driven root state is preserved in the ordinary
`root_transform_state` summary as:

`current_root_source = "phase596-runtime-root-consensus"`.

The handoff also retains compact consensus provenance:

- wrapper identity;
- owner path;
- exact float32 root identity;
- independent runtime resource count;
- distinct cumulative-local count;
- witness count.

This lets later scene admission distinguish runtime-consensus current state from
an explicitly supplied root or a recovered SceneGraph update history.

## Fail-closed rules

When a root-consensus file is explicitly supplied:

- its format must be `SHIFT.SGBMultiMatrixRootConsensus/1`;
- the top-level report must be ready;
- only ready rows with
  `authorizes_current_multimatrix_owner_root = true` are indexed;
- owner paths and matrices must be structurally valid;
- duplicate ready roots for the same owner are rejected.

Ambiguous/non-ready owner rows are never applied.

OBJECTs under owners without one ready consensus keep the old unresolved
numeric-world state.

## No scope leakage

A root for:

```text
SUMM 7 / owner_path [0]
```

does not apply to:

```text
SUMM 7 / owner_path []
SUMM 7 / owner_path [1]
```

Regression coverage freezes this behavior.

## CLI

The existing command gains one optional argument:

```bash
python shift_importer.py sgb-object-render-handoff \
  out/sgb-runtime.json \
  out/object-handoffs.json \
  --root-consensus out/multimatrix-root-consensus.json
```

The resulting `SHIFT.SGBObjectRenderHandoffSet/1` reports:

- `runtime_root_consensus_available_count`;
- `runtime_root_consensus_applied_object_count`;
- the resulting `numeric_world_matrix_ready_count`.

It can then flow unchanged into
`SHIFT.SGBRenderBindingAdmission/1`.

## Boundary

Phase 597 proves current MatrixNumber world matrices only for owners with a
ready Phase 596 consensus.

It does not recover:

- the historical SceneGraph update sequence;
- OBJECT↔runtime draw attribution;
- streaming/LOD decisions;
- a retail world-matrix constant register.

The next production step is to run Phases 595–597 on authentic Silverstone
capture content and measure which previously blocked MatrixNumber rows become
numerically ready. Any unresolved owners stay fail-closed.
