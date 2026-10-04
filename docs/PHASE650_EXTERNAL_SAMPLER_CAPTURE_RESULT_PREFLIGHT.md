# Phase 650 — exact external-sampler capture-result preflight

## Playable-slice blocker reduced

The supplied historical D3D9 capture is sufficient for shader/draw-state
analysis but contains no captured external-sampler snapshot paths. Phase 641
therefore emits an exact `runtime_evidence_required[]` frontier when a proven
Silverstone draw still needs renderer-owned `sampler2D` or `samplerCube`
content. Phase 642 converts that frontier into an exact stage-selective Wine
capture and Phase 643 materializes the plan from the unified bootstrap.

Before Phase 650, the selective capture launcher terminated as soon as the game
process returned. A failed D3D9 readback, wrong snapshot directory, incomplete
cube capture, or missing PPM was discovered only after rerunning the expensive
renderer attribution/admission chain.

Phase 650 adds a narrow fail-closed post-capture preflight:

```text
SHIFT.RendererNativeSceneHandoff/1
  -> SHIFT.Phase641ExternalSamplerCapturePlan/1
  -> selective Wine D3D9 capture
  -> shift_d3d9_capture.jsonl + textures/*.ppm
  -> SHIFT.Phase642ExternalSamplerCaptureResult/1
```

The new result proves only that the new capture contains the input class that
the exact Phase 641 frontier requested. It is not renderer admission.

## Tool

```text
tools/phase642_external_sampler_capture_result.py
```

The tool rebuilds the authoritative Phase 641 plan from the handoff and streams
the resulting raw JSONL. For every distinct requested sampler input class it
requires at least one `set_texture` event with:

- the exact requested D3D9 stage `s0..s15`;
- the exact expected D3D9 resource type (`texture2d` or `cube_texture`);
- `snapshot_status == "captured"`;
- exactly one snapshot path for `sampler2D`;
- exactly six snapshot paths for `samplerCube`;
- every referenced PPM resolving to a real file.

Cube captures additionally require the complete canonical face set:

```text
px nx py ny pz nz
```

A malformed JSON line also blocks the preflight rather than being silently
ignored.

## Snapshot path policy

The preflight preserves the existing Phase 590 portable capture-layout rule.
It never recursively searches by basename.

Accepted forms are:

1. an already-existing absolute path;
2. an exact relative path below the explicitly supplied capture root;
3. relocation of a Windows/POSIX absolute path only when its immediate source
   parent is exactly `textures`, producing:

```text
<capture-root>/textures/<exact filename>
```

Traversal outside the capture root is rejected.

## Wine wrapper integration

`tools/run_phase641_snapshot_capture_wine.sh` now keeps ownership after the game
process exits. On successful capture it automatically runs the preflight over:

```text
<OutputDir>/shift_d3d9_capture.jsonl
<OutputDir>/textures/
```

and writes:

```text
<OutputDir>/external_sampler_capture_result.json
```

If the normal launcher fails, its exit status is preserved. If it succeeds but
the capture JSONL is missing or the requested snapshot input classes are not
usable, the Phase 641 wrapper exits non-zero immediately.

## Proof boundary

`SHIFT.Phase642ExternalSamplerCaptureResult/1` explicitly does **not** claim:

- Phase 641 binding identity was revalidated;
- draw identity was revalidated;
- a texture pointer identifies a retail resource;
- a stage-level snapshot identifies a scene instance;
- `scene_set_ready` is true;
- the renderer admission chain may be skipped.

Two Phase 641 requirements may share one stage/resource class. A single valid
snapshot event can therefore make that **capture input class** ready, but it
cannot satisfy either binding semantically. Full Phase 569/572/574/590/592 and
Phase 580/585 re-attribution remains mandatory.

## Regression coverage

`tests/test_phase642_external_sampler_capture_result.py` freezes:

- successful exact `sampler2D` and six-face `samplerCube` input preflight;
- deterministic Windows launcher-path relocation;
- incomplete cube rejection;
- wrong resource-type rejection;
- missing PPM rejection;
- malformed JSON rejection;
- deduplicated stage-class readiness without binding-identity promotion.

`tests/test_phase642_wine_external_sampler_snapshot_capture.py` additionally
requires the Wine wrapper to execute this preflight after the normal capture
launcher rather than `exec`-replacing itself.

## Result

The remaining renderer evidence blocker still requires a new exact selective
capture; Phase 650 does not invent the missing pixels. It shortens that blocker
edge by making one capture attempt self-validating before the expensive
renderer feedback chain is rerun.
