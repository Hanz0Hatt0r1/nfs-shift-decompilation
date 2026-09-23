# SHIFT Texture / Render-State status

`SHIFT.TextureResource/1` now describes the source DDS format, dimensions, mip count, compression block geometry, upload strategy, sampler state and color-space state.

Known DXT1/DXT3/DXT5/ATI1/ATI2 families retain their BCn identity and explicit runtime extension requirement. The contract does not silently assume that optional compressed-texture extensions exist on the target Android device.

D3D9 filter/address modes are translated to GLES-equivalent sampler state names where the mapping is unambiguous. Unsupported modes such as BORDER are blocking conditions.

sRGB/linear are treated as renderer state. Conflicting source flags are a hard error rather than an implicit preference.

## Phase 40: software DDS reference sampler

`texture_reference.py` now decodes the DDS base level for DXT1/DXT3/DXT5 and common 32-bit masked RGBA resources into RGBA8, then applies explicit repeat/clamp/mirror addressing and nearest/linear sampling. `reference_renderer.py` can consume this image through a UV0-aware textured reference path without invoking BFF/LZX or the HLSL shader runtime.

The path is intentionally a texture/material oracle only: full BMT/HLSL lighting and multi-texture shader execution remain separate work.
