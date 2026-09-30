# Phase 591 — repeated scene-instance transform matching

Phase 590 can convert a strong-attributed D3D9 texture snapshot into an exact
scene external-sampler contract when one runtime binding maps to one
`SHIFT.NativeSceneBundle/1` draw.

The remaining ambiguity appears when the same resource-level binding is reused
by multiple world-space scene instances.

Phase 591 adds a fail-closed runtime transform witness for that case.

## Contract

New module:

`src/scene/native_scene_instance_transform_match.py`

emits:

`SHIFT.NativeSceneInstanceTransformMatch/1`.

Inputs:

- ready `SHIFT.NativeSceneBundle/1`;
- ready `SHIFT.IMBRuntimeCapturePipeline/1`.

The capture pipeline now retains draw-local vertex constant state only for
runtime draws that already support the selected strong Phase 572 shader
variant.

It does not retain unrelated frame state.

## No world-register guess

Phase 591 does **not** assign a retail world-matrix register.

For each strong-attributed runtime draw, it scans every contiguous four-register
window in the captured vertex float constant state.

Each 4×4 window is compared against every candidate SGB world matrix using exact
IEEE-754 float32 bytes.

Two layouts are accepted:

- source row-major order;
- exact transpose.

The accepted register number and layout are recorded only as observational
witnesses. They are not promoted to a retail shader semantic.

## Resolution rule

A repeated binding is resolved only when:

1. the binding appears in more than one NativeSceneBundle draw;
2. at least one strong-attributed runtime draw is available;
3. every retained runtime observation has an exact world-matrix constant
   witness;
4. each observation points to exactly one scene draw;
5. all observations agree on the same scene draw identity.

Multiple matching constant windows for the same scene draw are allowed and are
preserved as witnesses.

The matcher blocks when:

- no four-register constant window matches;
- the same world matrix belongs to multiple scene draws;
- different runtime observations point to different scene draws;
- any retained observation cannot be resolved;
- the Phase 591 compact observation contract is missing.

## Compact capture extension

`SHIFT.IMBRuntimeCapturePipeline/1` keeps the existing Phase 590 texture
observation contract unchanged and additionally declares:

`selected-strong-variant-vertex-constants-v1`.

Each strong-attributed observation now carries compact draw-local
`constant_state.vertex` / `constant_state.pixel` dictionaries.

This is still a selected-draw slice, not a retained full runtime frame.

## Phase 590 integration

`SHIFT.NativeSceneExternalSamplerCaptureAdapter/1` accepts an optional
`SHIFT.NativeSceneInstanceTransformMatch/1`.

When one binding maps to multiple scene draws, the adapter may select one draw
only when the Phase 591 report contains one ready exact selection for that
binding.

The resulting Phase 589 snapshot provenance records the selected draw order and
draw identity from the transform proof.

Without a Phase 591 proof, repeated bindings remain blocked exactly as before.

## CLI

Build the repeated-instance proof:

```bash
python shift_importer.py native-scene-instance-transform-match \
  out/native-scene-bundle.json \
  out/silverstone-runtime-attribution.json \
  out/scene-instance-transform-match.json
```

Then feed it to the existing capture adapter:

```bash
python shift_importer.py native-scene-external-capture \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/silverstone-runtime-attribution.json \
  out/scene-external-capture.json \
  --capture-root out/capture \
  --instance-transform-match out/scene-instance-transform-match.json \
  --snapshot-output out/scene-external-snapshots.json
```

## Boundary

Phase 591 closes repeated-instance disambiguation only when an authentic capture
contains the exact draw-local vertex constant state needed to distinguish the
world-space instances.

It does not synthesize missing captures and does not infer a world-matrix
register from static shader structure.

Remaining independent gates include:

- obtaining authentic Silverstone capture content;
- multiple supporting texture observations for one selected instance when their
  texture content is not uniquely identical;
- external samplerCube and other renderer-owned resource types;
- unresolved per-instance SceneGraph transform-update history;
- scene streaming/LOD;
- IMX XML neutral adaptation.
