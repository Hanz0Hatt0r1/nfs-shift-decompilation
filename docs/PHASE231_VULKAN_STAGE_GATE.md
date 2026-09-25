# Phase 231 — Vulkan descriptor stage gate

Phase 231 makes the reflected shader stage part of the native Vulkan interface contract.

Set 0 remains fixed:
- binding 14 is vertex c-register storage;
- binding 15 is fragment/pixel c-register storage.

Set 1 sampled textures are currently native-bound only for the fragment stage. A
sampler2D/samplerCube reflected from a vertex shader is therefore rejected before
native execution rather than silently binding an incompatible stage mask.

This gate is deliberately conservative. It validates the current native executor's
descriptor layout; it does not claim that the game never uses vertex-stage samplers.
