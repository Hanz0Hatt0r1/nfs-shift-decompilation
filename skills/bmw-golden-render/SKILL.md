---
name: bmw-golden-render
description: >-
  Build deterministic golden-asset evidence for the BMW M3 E36 render slice in
  Need for Speed: SHIFT.
---
# BMW M3 golden render workflow

## Objective

Produce a deterministic BMW M3 render slice from neutral IR and prove native parity against the desktop reference.

Renderer execution must not parse the original BFF at runtime.

## Selection

Prefer resources with:

- stable resource SHA-256 and root-relative path;
- POSITION0 and required material streams;
- real primitive/index ranges;
- BMT→FX→FXO resolution;
- unique shader/interface evidence.

Keep damage and LOD variants separate.

## Oracle chain

`BFF → MEB/VHF/BMT/FX/FXO/DDS → DrawBinding → RenderCommand → desktop reference → Vulkan`

## ABI note

BMW COLOR0/1 static declaration evidence is resolved to D3D9 Type 4 / Usage COLOR. Runtime same-instance declaration/buffer proof is still required for a concrete draw.

## External resources

Environment/shadow samplers remain explicit renderer-global resources.

## Golden artifacts

Record resource identities, shader pair hashes, permutation identity, material constants, texture identities, readiness blockers and final image SHA-256.

Do not commit original game archives.
