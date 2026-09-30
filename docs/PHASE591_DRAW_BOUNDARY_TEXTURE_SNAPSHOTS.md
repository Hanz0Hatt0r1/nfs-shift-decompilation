# Phase 591 — draw-boundary D3D9 texture snapshots

Phase 590 makes the renderer-owned `sampler2D` evidence path executable from
an attributed native D3D9 capture, but its PPM source is historically captured
at `SetTexture` time.

That is sufficient to prove the texture object bound into the later draw-local
state, but it does not prove that the captured pixels are the object's contents
at the indexed draw boundary.

Phase 591 adds a stronger, opt-in capture path.

## Producer mode

The native D3D9 proxy adds:

`SHIFT_D3D9_CAPTURE_DRAW_TEXTURE_SNAPSHOT=1`.

It shares the existing:

- `SHIFT_D3D9_CAPTURE_TEXTURE_STAGES`;
- `SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR`.

The historical SetTexture snapshot mode remains independently available as:

`SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT=1`.

The PowerShell runner exposes the new mode with:

`-CaptureDrawTextureSnapshots`.

## Draw index

The producer now emits a frame-local `draw_index` on every successful
`DrawIndexedPrimitive`.

The counter follows the same global frame convention already used by the
capture writer and resets after a successful `Present`.

The runtime parser independently computes draw order and rejects a producer
ordinal mismatch.

## Snapshot event

Immediately after a successful `DrawIndexedPrimitive`, while the same D3D9
bindings remain active, the opt-in producer calls `GetTexture` for every
configured stage and emits:

`draw_texture_snapshot`.

Each event records:

- capture frame through the normal writer envelope;
- exact frame-local draw index;
- D3D9 device;
- sampler stage;
- texture object pointer;
- resource descriptor;
- PPM capture status/path.

PPM filenames include frame + draw index so repeated use of the same texture
object cannot overwrite the evidence for another draw.

The existing image capture code and supported D3D9 formats are reused.

## Parser join

`SHIFT.D3D9RuntimeBindingEvidence/1` accepts
`draw_texture_snapshot` events and attaches them to the exact
`SHIFT.D3D9DrawStateSnapshot/1` using the explicit frame-local draw index.

For every attached snapshot, the parser rechecks:

`captured texture pointer == active SetTexture pointer at the same stage`.

A mismatch is a capture blocker:

`draw-texture-snapshot:active-binding-mismatch:sN`.

An event referring to a nonexistent draw index is also blocked.

The draw snapshot now carries a separate:

`draw_texture_snapshots[]`

list. Historical `active_texture_bindings[].snapshot_paths` remain unchanged.

## Phase 573 compact evidence v2

Phase 573 still discards full runtime frames from its compact output.

The strong-attributed texture slice is upgraded to:

`selected-strong-variant-draw-textures-v2`.

Each selected runtime draw preserves both:

- legacy SetTexture-time snapshot metadata in
  `active_texture_bindings`;
- exact Phase 591 draw-boundary snapshot metadata in
  `draw_texture_snapshots`.

Only runtime draws supporting the selected strong Phase 572 shader variant are
retained.

## Phase 590 preference policy

The capture→scene adapter accepts both v1 and v2 compact evidence.

For a required external register:

1. if any Phase 591 draw snapshot event exists for that stage, only valid
   draw-boundary evidence may satisfy the snapshot;
2. if the draw-boundary event exists but capture failed, the texture pointer
   mismatches, resource creation is not proven or the path is invalid, Phase
   590 remains blocked;
3. only when no draw-boundary event exists for the register may a legacy
   SetTexture-time PPM be used as fallback.

This prevents a failed stronger measurement from being silently replaced by an
older weaker image.

A successful Phase 591 conversion records:

- provenance source kind `D3D9_DRAW_CAPTURE_PPM`;
- snapshot time `draw-boundary-post-draw`;
- exact draw-snapshot event index.

Legacy fallback remains labeled `D3D9_CAPTURE_PPM` / `set-texture`.

## Temporal claim

The Phase 591 PPM is captured **immediately after a successful
DrawIndexedPrimitive**, not before it.

The claim is therefore:

- same capture frame;
- exact draw ordinal;
- same active sampler binding;
- same texture object pointer;
- image read immediately after the draw call returned.

No stronger claim about undocumented D3D9 driver/GPU synchronization or
earlier/later application-side texture mutation is invented.

## Runner example

```powershell
.\tools\run_shift_capture.ps1 `
  -GameExe "C:\Games\SHIFT\shift.exe" `
  -ProxyDll ".\build\native_capture\d3d9.dll" `
  -OutputDir ".\shift-capture" `
  -CaptureDrawTextureSnapshots `
  -TextureStages "0,3,4,7"
```

SetTexture-time snapshots can still be enabled independently when comparative
evidence is useful.

## Tests

Phase 591 covers:

- capture schema acceptance/rejection for the new event;
- producer draw-index schema;
- exact draw-snapshot attachment;
- active texture pointer equality;
- producer/parser draw-index mismatch;
- Phase 573 transport of draw-boundary evidence;
- Phase 590 preference for draw-boundary PPM;
- no fallback when the stronger draw capture failed;
- no fallback on draw-boundary pointer mismatch;
- runner switch/environment exposure.

The Windows capture-producer CI also recompiles the modified D3D9 proxy.

## Boundary after Phase 591

For an unambiguous strongly attributed scene draw, the software path can now
prefer a PPM captured at the exact indexed draw boundary before generating the
Phase 589 external sampler snapshot contract.

Still open:

- authentic Silverstone capture content;
- repeated scene-instance disambiguation;
- external cube/other renderer-owned resource types;
- any deeper synchronization/mutation proof required by a specific retail
  resource;
- scene streaming/LOD, remaining MatrixNumber history and IMX XML adaptation.
