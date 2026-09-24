---
name: bmw-golden-render
description: >-
  Build deterministic golden-asset evidence for the BMW M3 E36 render slice in
  Need for Speed: SHIFT. Use for selecting real BMW MEB resources, validating
  material/shader permutations, constructing DrawPacket/RenderCommand fixtures,
  and preserving reproducible render evidence.
---
# BMW M3 golden render workflow

The current milestone is a real BMW M3 static render without reading BFF archives
at renderer runtime.

## Selection rules

Prefer a real 1.02 corpus resource with:

- stable resource SHA-256 and root-relative path;
- POSITION0 and required material streams;
- a real primitive/index range;
- a material reference that can be resolved through BMT → FX → FXO;
- shader interface evidence that is unique rather than file-order dependent.

Keep damage/LOD variants separate. Do not silently substitute one mesh for another.

## Oracle chain

`BFF → MEB/VHF/BMT/FX/FXO/DDS → DrawBinding → RenderCommand → desktop reference`

The desktop reference is the golden oracle. GLES is compared against its command and
shader inputs, not used to redefine the data model.

## Golden artifacts

Every new golden fixture should record resource identities, shader pair hashes,
material constant payload hash, texture identities, readiness blockers and final
image SHA-256. Raw copyrighted game archives should not be committed.
