# Phase 125 — BMW runtime shader join

`SHIFT.BMWRuntimeShaderJoin/1` correlates one exact `SHIFT.BMWMaterialSlice/1` with
a captured `SHIFT.D3D9RuntimeBindingEvidence/1` frame.

Acceptance requires both identities:

- exact shader permutation identity (`SHIFT.ShaderPermutationIdentity/1`);
- exact BMW MEB resource SHA-256, or normalized resource path when SHA is unavailable in the capture.

The join then validates the material sampler contract against the runtime pixel-shader
reflection: every expected material/external sampler register must exist with the same
sampler type, and unexpected runtime samplers are blockers.

## CLI

```bash
python shift_importer.py bmw-runtime-shader-join bmw-paint-slice.json runtime-evidence.json bmw-runtime-join.json
```

## Boundary

This contract does not infer a missing Usage ordinal mapping and does not authenticate
an external capture. It establishes a reproducible correlation only when the supplied
identity fields agree.

## Next

Use the resulting joined frame to validate constants and VS input semantics against
`MaterialConstantPayload/1`, `VertexLayout/1` and the captured D3D9 declaration, then
feed the exact command to the desktop shader-reference renderer.