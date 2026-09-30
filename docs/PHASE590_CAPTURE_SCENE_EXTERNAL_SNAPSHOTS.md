# Phase 590 — attributed D3D9 capture → exact scene external snapshots

Phase 589 defines the exact scene-level admission contract for a renderer-owned
external `sampler2D`, but the snapshot JSON still has to be constructed from
capture evidence.

Phase 590 connects the existing native D3D9 texture-snapshot producer to that
contract without weakening any of the shader/resource/scene proof gates.

## Existing evidence reused

No new D3D9 capture mechanism is introduced.

The existing capture stack already provides:

- `CreateTexture` / `SetTexture` object lifecycle evidence;
- draw-local `SHIFT.D3D9DrawStateSnapshot/1`;
- active texture bindings at the exact indexed draw boundary;
- `snapshot_status` and `snapshot_paths`;
- captured 2D PPM files;
- Phase 572 unique strong shader attribution.

`src/runtime/runtime_texture_reference.py` already converts a captured PPM to
`SHIFT.ReferenceTexture/1`.

Phase 590 only joins these existing contracts.

## Phase 573 compact evidence extension

`SHIFT.IMBRuntimeCapturePipeline/1` still does **not** retain full runtime
frames.

For every binding that Phase 572 uniquely attributes, it now preserves a small
`attributed_texture_observations` list containing only runtime draws that
support the selected strong shader variant.

Each observation contains:

- binding index;
- capture frame and draw index;
- active texture register;
- D3D9 texture pointer;
- observed `CreateTexture` identity;
- capture status;
- snapshot paths.

Pixel-only/prefilter-only shader observations are not retained here.

The PPM itself is captured by the native producer at the active `SetTexture`
boundary and then carried into the exact draw-local state snapshot. Phase 590
does not claim that no texture mutation occurred after that binding event; that
is a separate evidence gate.

If multiple runtime draws support the same selected strong variant, all are
preserved. Phase 573 does not choose one.

## Capture adapter

New module:

`src/scene/native_scene_external_sampler_capture.py`

emits:

`SHIFT.NativeSceneExternalSamplerCaptureAdapter/1`.

Inputs:

- ready `SHIFT.NativeSceneBundle/1`;
- ready `SHIFT.SGBRenderBindingBridge/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`;
- an explicit capture root containing the PPM files.

The bridge is required so Phase 590 can distinguish RenderCommand
`external_samplers` from ordinary material textures.

## Exact automatic join

For each external `sampler2D` declaration, automatic conversion is allowed
only when:

1. the Phase 574/577 binding index maps to exactly one NativeSceneBundle draw;
2. that exact command/submesh declares the register as an external
   `sampler2D`;
3. Phase 572 produced a unique strong shader attribution;
4. exactly one supporting runtime draw observation remains;
5. the active register has observed `CreateTexture` lifecycle identity;
6. the created object is exactly `texture2d`;
7. snapshot status is `captured`;
8. exactly one PPM snapshot path is present;
9. the PPM resolves unambiguously under the explicit capture root;
10. the generated snapshot passes the complete Phase 589 validator.

Repeated scene instances sharing one resource-level binding remain blocked by
Phase 590 alone. Phase 591 may supply an exact transform-match contract; without
that proof the adapter still does not choose a world-space instance arbitrarily.

## Captured PPM conversion

A successful PPM is converted to `SHIFT.ReferenceTexture/1` RGBA8 with the
existing runtime texture converter.

The local `source_path` field is removed before the Phase 589 canonical
texture-object hash is computed, so scene admission identity does not depend on
the workstation filesystem path.

The Phase 589 provenance row records:

- source kind `D3D9_CAPTURE_PPM`;
- SHA-256 of the actual PPM bytes;
- capture frame;
- capture draw index;
- texture pointer;
- raw snapshot path;
- resolved local path;
- path-resolution mode;
- observed `CreateTexture` descriptor.

## Cross-platform capture paths

Native capture commonly emits Windows-absolute paths.

The adapter first accepts an existing absolute path or an exact path relative
to the explicit capture root.

For a copied Windows capture processed on another OS, it may remap by basename
only when exactly one file with that basename exists recursively below the
explicit capture root.

Zero or multiple basename matches remain fail-closed.

## Output

The adapter report contains a `snapshot_contract` only when the complete join
is ready.

For external sampler2D the contract remains exactly:\n\n`SHIFT.NativeSceneExternalSamplerSnapshots/1`\n\nand is revalidated through the Phase 589 validator before being exposed. Phase 592 additionally emits a separate `SHIFT.NativeSceneExternalSamplerCubeSnapshots/1` for the proven samplerCube s3 boundary.

A blocked adapter cannot accidentally masquerade as a valid Phase 589
snapshot manifest.

## CLI

After running the Phase 573 attribution pipeline:

```bash
python shift_importer.py native-scene-external-capture \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/silverstone-runtime-attribution.json \
  out/scene-external-capture.json \
  --capture-root out/capture \
  --instance-transform-match out/scene-instance-transform-match.json \\
  --snapshot-output out/scene-external-snapshots.json \\
  --cube-snapshot-output out/scene-external-cube-snapshots.json
```

The resulting snapshot manifest can be passed directly to Phase 589:

```bash
python shift_importer.py native-scene-vulkan-set \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan \
  --external-sampler-snapshots out/scene-external-snapshots.json \\
  --external-sampler-cube-snapshots out/scene-external-cube-snapshots.json
```

## Fail-closed cases

The adapter blocks rather than guessing when:

- one binding appears in multiple NativeSceneBundle instances without a ready Phase 591 exact transform match;
- more than one attributed runtime draw can supply the register;
- texture creation is not observed;
- the runtime object type does not match the declared sampler type;
- no PPM is captured;
- multiple snapshot paths exist;
- capture path resolution is missing or ambiguous;
- the generated Phase 589 contract fails exact identity validation.

Ordinary material textures are never promoted into the external snapshot
contract.

## Boundary after Phase 590

The software path from authentic D3D9 `SetTexture` PPM capture to exact
scene-level external `sampler2D` admission is now executable.

Still external/evidence-gated:

- obtaining a real Silverstone capture containing the required renderer-owned
  sampler snapshots;
- repeated-instance disambiguation is available through Phase 591 when exact
  draw-local VS constant windows uniquely identify one world matrix; otherwise it remains blocked;
- Phase 592 closes external `samplerCube` only at proven s3; other renderer-owned resource types or cube registers remain gated;
- unresolved scene streaming/LOD and MatrixNumber update history;
- IMX XML neutral adaptation.
