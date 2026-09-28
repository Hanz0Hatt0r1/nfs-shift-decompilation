# SHIFT DrawPacket / StaticDraw status

## Current boundary

`VHF/CAR → MEB → BMT → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

## DrawPacket

A canonical packet preserves scene/node identity, world transform, MEB primitive range, material identity, shader-selection metadata, linked VS/PS information, vertex ABI evidence, textures and material constants.

Selection is evidence-driven. Filesystem/archive order is never a hidden semantic tie-breaker.

## StaticDraw readiness

A draw is ready only when the selected path has:

- valid VertexLayout/1;
- unique compatible VS/PS selection;
- valid shader translation;
- resolved required material textures;
- valid sampler/uniform/constant contracts;
- valid submesh index range;
- all required external resources represented explicitly.

## Vertex ABI

The current BMW static mapping is:

`460 → [4,6,0]`, `461 → [4,6,1]`, Type 4 = D3DCOLOR, Usage 6 = D3D9 COLOR.

Runtime same-instance declaration/buffer proof remains a separate gate.

## Reference and native handoff

The desktop oracle consumes RenderCommand/1 directly. Vulkan is required to consume the same contract rather than reinterpreting MEB/BMT/FXO independently.

## Remaining render work

- broaden exact BMW shader/material coverage;
- close more runtime draw/resource same-instance proofs;
- complete Vulkan RenderCommand submission;
- keep unsupported and ambiguous states fail-closed.
