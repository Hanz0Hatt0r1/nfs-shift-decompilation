# Phase 588 — explicit external sampler2D snapshots

Phase 587 proves that prepared neutral scene transforms are actually executed by
`native_runtime`. The next renderer boundary is external resources: material
textures already travel through `SHIFT.VulkanTexturePacket/1`, while
renderer-owned samplers remain explicit `external_samplers`.

Phase 588 closes the **transport ABI** for externally supplied 2D texture
snapshots without inventing their contents or silently relabeling them as
material textures.

## SVTP external 2D channel

`build_vulkan_texture_packet()` now accepts an optional
`external_textures` map in addition to the existing material texture map.

An external image is serialized only when all of these are true:

- the RenderCommand declares the same register in `external_samplers`;
- the declared type is exactly `sampler2D`;
- the register is in the native packet range s0..s15;
- the register does not collide with a material texture;
- the external sampler has explicit `sampler_state`;
- the supplied resource is a valid `SHIFT.ReferenceTexture/1` RGBA8 image.

Unprovided external samplers are not converted into blockers at this atomic
packet layer; they remain runtime-resource requirements exactly as before.

The binary SVTP header/record ABI is unchanged. Metadata now records whether
each record came from a `material` or `external` source.

## Neutral draw bundle

`SHIFT.VulkanDrawBundle/1` gains an optional `external_textures` input.

For each external sampler the manifest reports one of:

- `provided-to-vulkan-texture-packet`;
- `provided-to-vulkan-cube-packet`;
- `requires-runtime-resource`.

The boundary also records the exact external 2D registers actually transported.
A supplied snapshot does not change `RuntimeProvenDraw` or shader provenance.

## DDS bridge

The DDS resource bridge now distinguishes:

- material 2D registers;
- external 2D registers;
- external cube registers.

External 2D DDS input is decoded into the same native SVTP binary packet but is
recorded in provenance as `external-2d`. Material and external registers are
kept disjoint.

This corrects a prior inconsistency where the bridge recognized external
sampler2D registers as 2D requirements but the texture packet builder ignored
them.

## CLI

The neutral draw-bundle command exposes:

```bash
python shift_importer.py vulkan-draw-bundle \
  render-command.json \
  neutral-mesh.json \
  out/vulkan-draw \
  --external-textures external-textures.json
```

The JSON object maps D3D9 sampler registers to explicit
`SHIFT.ReferenceTexture/1` snapshots.

## Fail-closed boundary

Phase 588 does **not**:

- infer an external texture from a sampler name;
- map a shadow/environment sampler to a retail DDS automatically;
- invent missing sampler state;
- resolve scene-level external-resource blockers merely because the transport
  ABI exists;
- broaden the cube path beyond its separately proven contract.

The next scene integration step can resolve a
`external-sampler:runtime-resource-unresolved` blocker only when an explicit,
provenance-bearing snapshot is supplied for that exact draw/register/type.

## Tests

Regression coverage now verifies:

- material + external sampler2D records in one SVTP packet;
- unchanged behavior when the external resource is not supplied;
- undeclared external-register rejection;
- explicit sampler-state requirement;
- neutral draw-bundle manifest status/provenance;
- DDS material/external register separation and source kinds;
- root importer CLI exposure.
