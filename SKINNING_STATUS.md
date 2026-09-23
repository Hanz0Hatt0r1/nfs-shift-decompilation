# SHIFT Skinning / Animation status

`SHIFT.Skinning/1` формализует MEB skinning inputs: property 310 = FLOAT4 weights и property 580 = UINT8x4 bone indices.

`skinning.py` теперь содержит:
- проверку парности weights/indices и диапазона bone indices;
- deterministic CPU reference skinning для positions;
- rotation-only reference transform для normals/tangents;
- optional source-weight normalization для случаев, когда исходный набор весов требует нормализации при runtime upload.

`SHIFT.SkinnedDraw/1` допускает draw only when mesh is skinned, a resolved pose has the expected bone count, each bone has a valid 3x4/4x4 matrix, and provided influence arrays are valid.

`resource_formats.analyze_decoded_resource()` now recognizes binary `.bab` resources and routes them through the verified BAB parser, preserving the opaque animation tail with offset/size/SHA-256 instead of classifying it as unknown binary data.

BAB bone records и BAS hierarchy уже парсятся существующими parsers. BAB animation tail пока хранится как opaque payload с offset/size/SHA-256; keyframe grammar не угадывается.
