# SHIFT Texture / Render-State status

`SHIFT.TextureResource/1` now describes the source DDS format, dimensions, mip count, compression block geometry, upload strategy, sampler state and color-space state.

Known DXT1/DXT3/DXT5/ATI1/ATI2 families retain their BCn identity and explicit runtime extension requirement. The contract does not silently assume that optional compressed-texture extensions exist on the target Android device.

D3D9 filter/address modes are translated to GLES-equivalent sampler state names where the mapping is unambiguous. Unsupported modes such as BORDER are blocking conditions.

sRGB/linear are treated as renderer state. Conflicting source flags are a hard error rather than an implicit preference.
