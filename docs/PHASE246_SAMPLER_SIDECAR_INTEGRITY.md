# Phase 246 — sampler sidecar integrity gate

Phase 246 adds a pre-native integrity check for the lossless sampler sidecar introduced in Phase 245.

When `sampler_contracts.meta.json` is present, `vulkan_bundle_run.py` now verifies:
- the metadata format;
- the exact `textures.svtp` path and SHA-256 recorded in the sidecar;
- the nested `SHIFT.VulkanSamplerContract/1` format and readiness.

A mismatch or blocked sampler contract stops the runner before descriptor validation/native Vulkan. Bundles without the sidecar remain accepted for backward compatibility.

This is an integrity gate, not a claim that the native executor already consumes the complete D3D9 sampler contract.
