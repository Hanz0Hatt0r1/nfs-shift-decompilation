# Render pipeline status

## Canonical path

`VHF/CAR → MEB → BMT/MTX → FX/FXO → RenderBinding/1 → DrawPacket/1 → StaticDraw/1 → RenderCommand/1`

## Implemented

### Resource/material linking

- VHF references resolve to MEB;
- scene-admitted SGB MEB instances can enter the same resource path with their source-backed world matrices;
- the retail SGB OBJECT factory is classified separately as MeshType/type 0 or MeshInst/type 7 (`.imb/.imx`); `.imb` decodes through `SHIFT.IMBNeutralGeometry/1`, while Phase 592 reconstructs the source-backed `.imx` XML grammar into `SHIFT.IMXNeutralGeometry/1`; both feed the neutral renderer without asserting serialized-container equivalence, and the existing MEB path remains separate;
- MEB primitive material references resolve through BMT/MTX;
- BMT connects to FX sources and FXO permutations;
- CTAB reflection supplies sampler registers and material constants;
- renderer-global samplers remain explicit external resources; Phase 588 transports an explicitly supplied external `sampler2D` snapshot through SVTP without reclassifying it as a material texture; Phase 589 admits that snapshot at scene level only after exact draw/resource/primitive/register/type/hash/provenance matching; Phase 590 converts strong-attributed draw-local native D3D9 PPM evidence into that exact scene contract only when scene-instance and texture observations are unambiguous.

### Vertex ABI

VertexLayout/1 carries target interleaving/repack information with ABI confidence.

Known BMW attributes include POSITION0, NORMAL0, TANGENT0, BINORMAL0, TEXCOORD0..4, BLENDWEIGHT0, BLENDINDICES0 and static Type-4 COLOR declarations.

### RenderCommand

RenderCommand/1 is the common submission source for the desktop reference renderer and future GLES/Vulkan backends. It preserves geometry ranges, attributes, linked shader stages, constants, samplers and external resources.

## BMW runtime gate

Real captured draws additionally require exact MEB identity, draw-local snapshot alignment and declaration/VB/IB/shader/resource correlation.

## Current native direction

Vulkan has bootstrap, headless checks, geometry/constant/texture/cubemap packets, SPIR-V interface validation, the BMW material→DDS adapter, neutral scene-set execution, an explicit external-`sampler2D` snapshot channel in the existing SVTP binary ABI, exact scene-level admission for provenance-bearing sampler2D snapshots, and an automatic strong-attributed D3D9 PPM→scene snapshot adapter.

## Remaining work

Broaden exact BMW shader/material execution, close more runtime same-instance evidence, obtain authentic Silverstone capture content, disambiguate repeated scene instances where required, and cover remaining renderer-owned resource types, establish IMX runtime same-instance evidence when available, carry scene visibility/streaming semantics beyond the SGB resource bridge, and close remaining alpha-test/bias/stencil Vulkan state. Missing renderer-owned resources remain fail-closed.
