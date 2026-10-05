# Phase 593 — exact external samplerCube s3 snapshots

Phase 589–591 close scene-bound external `sampler2D` snapshots and repeated
scene-instance disambiguation.

The D3D9 producer already captures `CreateCubeTexture` lifecycle identity and,
for a captured bound cube, emits six PPM face paths. The native Vulkan path
already consumes `SHIFT.ReferenceCubeTexture/1` through
`SHIFT.VulkanCubeTexturePacket/1`.

Phase 593 joins those existing contracts for the one cube register that is
already source/runtime-proven: D3D9 sampler **s3**.

## Contract

New module:

`src/scene/native_scene_external_sampler_cube_snapshots.py`

emits:

`SHIFT.NativeSceneExternalSamplerCubeSnapshots/1`.

A snapshot row is admissible only for one exact:

- NativeSceneBundle draw identity SHA-256;
- IMB archive/path/SHA-256 identity;
- primitive index;
- D3D9 register s3;
- `samplerCube` type;
- canonical `SHIFT.ReferenceCubeTexture/1` object;
- canonical cube JSON SHA-256;
- provenance-bearing six-face D3D9 capture.

No arbitrary cube register is introduced.

## Capture join

`SHIFT.NativeSceneExternalSamplerCaptureAdapter/1` now recognizes an external
`samplerCube` declaration only when it is at s3.

The selected strong-attributed runtime draw must contain:

- observed `CreateCubeTexture` lifecycle identity;
- `snapshot_status = captured`;
- exactly six snapshot paths;
- exactly one path for each face suffix:
  `px`, `nx`, `py`, `ny`, `pz`, `nz`.

Each face path is resolved with the same explicit capture-root policy already
used for sampler2D snapshots. Missing, duplicate or ambiguous faces remain
blocked.

The six PPM files are converted with the existing
`ppms_to_reference_cube()` helper. Filesystem-only `source_path` fields are
removed before canonical scene identity is computed.

## Provenance

The cube snapshot provenance uses:

`SHIFT.ExternalSamplerSnapshotProvenance/1`

with:

- `source_kind = D3D9_CAPTURE_PPM_CUBE`;
- capture frame/draw;
- D3D9 texture pointer;
- observed CreateCubeTexture descriptor;
- one source SHA-256 and resolved/raw path per face;
- a deterministic aggregate source SHA-256 over the six face source hashes;
- optional Phase 591 repeated-instance proof.

The contract validator recomputes the aggregate hash from the six face hashes.

## Vulkan admission

`SHIFT.NativeSceneVulkanSet/1` accepts an optional
`SHIFT.NativeSceneExternalSamplerCubeSnapshots/1`.

For a matching scene draw it revalidates:

- draw identity;
- IMB resource identity;
- primitive index;
- s3/samplerCube identity.

Only then is the captured `ReferenceCubeTexture/1` passed to the existing
neutral Vulkan child builder and serialized as:

`environment_cube.svcp`.

The existing native cube descriptor ABI is unchanged.

## Global DDS compatibility

Phase 593 originally retained the historical explicit
`--environment-cube-dds` scene-builder path and rejected only the case where it
was supplied together with a scene-bound cube snapshot.

**Phase 659 supersedes that compatibility rule.** A manually selected global DDS
is no longer runtime authority for `SHIFT.NativeSceneVulkanSet/1`, even when no
Phase 593 snapshot is present. The CLI argument remains accepted only so older
invocations fail with an explicit provenance diagnostic:

`environment-cube:global-dds-not-runtime-proven-for-scene`.

Supplying both a global DDS and an exact scene snapshot still fails closed with:

`environment-cube:global-dds-conflicts-with-scene-snapshots`.

BMW material/environment DDS support remains separate in the BMW DDS bridge and
is not removed by Phase 659.

## CLI

Capture both external 2D and cube resources:

```bash
python shift_importer.py native-scene-external-capture \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/silverstone-runtime-attribution.json \
  out/scene-external-capture.json \
  --capture-root out/capture \
  --instance-transform-match out/scene-instance-transform-match.json \
  --snapshot-output out/scene-external-snapshots.json \
  --cube-snapshot-output out/scene-external-cube-snapshots.json
```

Feed the exact cube contract into the scene set:

```bash
python shift_importer.py native-scene-vulkan-set \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan \
  --external-sampler-snapshots out/scene-external-snapshots.json \
  --external-sampler-cube-snapshots out/scene-external-cube-snapshots.json
```

## Boundary

Phase 593 closes capture-to-native transport for renderer-owned external
`samplerCube` only at the already-proven s3 boundary.

It does not:

- assign semantics to other cube registers;
- synthesize missing cube faces;
- treat a material DDS as runtime scene evidence;
- generate authentic Silverstone capture data.

The remaining external evidence gate is still an authentic Silverstone capture
containing the required shader/resource observations. Other renderer-owned
resource types, scene streaming/LOD, unresolved MatrixNumber history and IMX
XML adaptation remain separate workstreams.
