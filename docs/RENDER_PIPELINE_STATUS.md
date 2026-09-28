# Render pipeline status

## Canonical path

`VHF/CAR → MEB → BMT/MTX → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

## Implemented

### Resource/material linking

- VHF references resolve to MEB;
- MEB primitive material references resolve through BMT/MTX;
- BMT connects to FX sources and FXO permutations;
- CTAB reflection supplies sampler registers and material constants;
- renderer-global samplers remain explicit external resources.

### Vertex ABI

VertexLayout/1 carries target interleaving/repack information with ABI confidence.

Known BMW attributes include POSITION0, NORMAL0, TANGENT0, BINORMAL0, TEXCOORD0..4, BLENDWEIGHT0, BLENDINDICES0 and static Type-4 COLOR declarations.

### RenderCommand

RenderCommand/1 is the common submission source for the desktop reference renderer and future GLES/Vulkan backends. It preserves geometry ranges, attributes, linked shader stages, constants, samplers and external resources.

## BMW runtime gate

Real captured draws additionally require exact MEB identity, draw-local snapshot alignment and declaration/VB/IB/shader/resource correlation.

## Current native direction

Vulkan has bootstrap, headless checks, geometry/constant/texture/cubemap packets, SPIR-V interface validation and the BMW material→DDS adapter.

## Remaining work

Broaden exact BMW shader/material execution, close more runtime same-instance evidence, and complete full RenderCommand submission on Vulkan.
