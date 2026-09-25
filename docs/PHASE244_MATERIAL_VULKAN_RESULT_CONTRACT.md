# Phase 244 — material Vulkan result contract

The `SHIFT.BMWMaterialSliceVulkan/1` adapter now exposes its DDS bridge report at the top level as `dds_bridge`, in addition to the nested bundle manifest copy.

This makes exact DDS source extraction/verification status directly consumable by callers without requiring them to unpack the lower-level `BMWVulkanBundle/1` result. The value is the same object written into the bundle's `dds_bridge` field.
