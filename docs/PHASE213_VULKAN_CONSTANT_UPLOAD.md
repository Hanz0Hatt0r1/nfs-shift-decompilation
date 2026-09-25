# Phase 213 — Vulkan D3D9 constant upload

Phase 213 connects RenderCommand constant payloads to real Vulkan descriptor-backed
uniform buffers.

The Python boundary is SHIFT.VulkanConstantPacket/1:
- two fixed 256-register float banks;
- 16 bytes per D3D9 c-register;
- vertex bank -> set 0/binding 14;
- pixel bank -> set 0/binding 15.

Because MaterialConstantPayload/1 does not store shader stage inside each register row,
the packet builder cross-checks RenderCommand constant_commands. A register mapped to
both VS and PS is rejected rather than duplicated or guessed.

The native Vulkan checkpoint creates two uniform buffers, a descriptor-set layout,
descriptor pool/set and writes both buffers before drawing an offscreen triangle whose
position offset and fragment color come from c0.

This is the first actual GPU-side material-constant upload. It is still a synthetic
triangle checkpoint, not the real BMW material permutation.
