# SHIFT Texture / Render-State status

## TextureResource/1

Carries source DDS identity, dimensions, mip count, compression family, upload strategy, sampler state and color-space state.

Known DXT1/DXT3/DXT5/ATI1/ATI2 families remain explicit compressed formats. Optional target extensions are requirements, not assumptions.

## Reference sampler

The software reference path supports the project's current DXT/uncompressed decode paths, explicit address/filter behavior, multiple sampler2D registers, and samplerCube via six-face resources or complete DDS cubemaps.

## State rules

Unsupported mappings such as BORDER remain blockers. sRGB/linear state is explicit. Conflicting source flags are hard errors. Duplicate non-external sampler registers are rejected.

## BMW

Paint uses s1 diffuse, s2 specular and s4 scratch-control. Environment s3 and shadow s0 remain external renderer resources.

Runtime capture also records texture lifecycle and optional mip/cube payload evidence.

## Remaining work

Close exact sampler/material semantics and correlate more runtime resource instances with the static material plan.
