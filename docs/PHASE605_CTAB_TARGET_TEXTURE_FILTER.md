# Phase 605 — CTAB-aware target texture filtering

## Motivation

D3D9 texture bindings persist across draws. A sampler stage that remains bound
does not prove that the currently active pixel shader reads it.

The production Phase 603 catalogue therefore can include stale texture stages
inside descriptor-only resource-shape signatures even when shader/draw state is
otherwise correct.

## Change

On `CreatePixelShader`, the target draw catalogue now parses the captured SM3
bytecode with the existing `shader_ir.parse_shader_blobs` CTAB parser.

For reflected target draws:

- CTAB sampler registers are recovered from the pixel shader;
- only bound texture stages whose numeric stage is one of those registers enter
  `texture_stages` in the stable resource-shape signature.

If reflection is unavailable or malformed, the catalogue deliberately falls
back to all currently bound stages. No texture evidence is silently discarded
when sampler metadata is missing.

The report also counts:

- `reflected_target_draw_count`;
- `fallback_texture_state_draw_count`.

## Boundary

CTAB filtering proves only that one sampler register exists in the captured
pixel shader. It does not prove the semantic role, source DDS identity, IMB
primitive identity or scene-instance identity of the bound texture.

Existing resource path/SHA, payload and same-instance gates remain unchanged.
