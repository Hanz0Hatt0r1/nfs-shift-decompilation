# Render pipeline status

## Canonical path

`VHF/CAR → MEB → BMT/MTX → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

## Implemented

### Resource/material linking

- VHF references resolve to MEB;
- scene-admitted SGB MEB instances can enter the same resource path with their source-backed world matrices;
- the retail SGB OBJECT factory is classified separately as MeshType/type 0 or MeshInst/type 7 (`.imb/.imx`); `.imx` uses the XML mesh loader while `.imb` now auto-decodes its packed version/control/name prefix plus fixed header, bones and Type/Usage/Channel stream table; the existing MEB path remains a separate neutral adapter;
- MEB primitive material references resolve through BMT/MTX;
- BMT connects to FX sources and FXO permutations;
- CTAB reflection supplies sampler registers and material constants;
- renderer-global samplers remain explicit external resources; Phase 588 transports an explicitly supplied external `sampler2D` snapshot through SVTP without reclassifying it as a material texture, and Phase 589 admits such a snapshot into a neutral scene only after exact draw/sampler identity revalidation.

### Vertex ABI

VertexLayout/1 carries target interleaving/repack information with ABI confidence.

Known BMW attributes include POSITION0, NORMAL0, TANGENT0, BINORMAL0, TEXCOORD0..4, BLENDWEIGHT0, BLENDINDICES0 and static Type-4 COLOR declarations.

### RenderCommand

RenderCommand/1 is the common submission source for the desktop reference renderer and future GLES/Vulkan backends. It preserves geometry ranges, attributes, linked shader stages, constants, samplers and external resources.

## BMW runtime gate

Real captured draws additionally require exact MEB identity, draw-local snapshot alignment and declaration/VB/IB/shader/resource correlation.

## Current native direction

Vulkan has bootstrap, headless checks, geometry/constant/texture/cubemap packets, SPIR-V interface validation, the BMW material→DDS adapter, neutral scene-set execution, and an explicit external-`sampler2D` snapshot channel in the existing SVTP binary ABI.

## Remaining work

Broaden exact BMW shader/material execution, close more runtime same-instance evidence, supply authentic provenance-bearing external snapshots for real scene draws, implement the IMX XML neutral adapter, carry scene visibility/streaming semantics beyond the SGB resource bridge, and close remaining alpha-test/bias/stencil Vulkan state. Missing renderer-owned resources remain fail-closed.
