# Phase 221 — end-to-end native Vulkan bundle execution

Phase 221 completes the current prepared-bundle path.

The Python runner:
1. compiles bundle shader sources to SPIR-V;
2. writes a deterministic SPIR-V report;
3. validates SPIR-V descriptors against actual bundle resource packets;
4. writes the interface report;
5. launches the native Vulkan bundle executor only when both gates are ready;
6. records the final PPM SHA-256.

The native executable consumes only binary bundle artifacts and does not parse BFF,
MEB, BMT or RenderCommand JSON.

The native renderer uses neutral raster state. Retail blend/raster state, shader
semantic completeness and runtime-derived resource contents remain separate evidence
and parity work.
