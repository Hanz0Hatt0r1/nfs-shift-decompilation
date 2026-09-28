# Desktop reference renderer

The desktop software renderer is the deterministic behavioral oracle for the neutral render contracts.

## Current execution surface

Supports:

- indexed static and skinned geometry;
- RenderCommand/1 validation and execution;
- DDS DXT1/DXT3/DXT5 and common 32-bit reference decode;
- explicit sampler address/filter state where defined;
- multiple sampler2D resources;
- samplerCube using explicit six-face resources and complete DDS cubemaps;
- bounded ShaderProgram/1 vertex and pixel execution;
- VS→PS semantic linkage by (usage,index);
- explicit extended semantics such as TEXCOORD5;
- explicit SkinPose deformation before shader/raster execution.

The renderer is not a complete D3D9/HLSL interpreter.

## Skinning

`SkinnedDraw/1 + SkinPose/1 → SkinnedMeshReference/1 → reference VS/PS → raster`

Bind-local BAB/BAS matrices are not silently substituted for a runtime skin pose.

## External resources

BMW renderer-global resources remain explicit, notably environment s3 and shadow s0.

## Determinism

Reference output can be hashed with SHA-256 and compared as a regression artifact. Geometry ranges, resource identity and shader/reference payloads are validated before execution.

## Recent progress

The deterministic shader oracle now executes structured D3D9 conditionals and matrix/sign operations, allowing more vertex/pixel programs to reach reference execution before native parity work.

## Remaining work

Broaden D3D9 instruction/control-flow coverage, close exact BMW lighting/blending semantics, prove more runtime resources and use the oracle as the native Vulkan parity target.
