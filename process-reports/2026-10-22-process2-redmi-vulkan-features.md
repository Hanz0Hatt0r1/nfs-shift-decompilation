# Redmi Note 8 Pro Vulkan device profile

**Date:** 2026-10-22
**Scope:** read-only Android and Vulkan capability query for the locally connected Redmi Note 8 Pro (`begonia`). No app was installed or launched, no setting was changed, and no game/runtime was started. No XEX, game data, raw `vkjson` dump, device UUID, ADB serial, or network address was retained in this report.

## Result

Android's existing `cmd gpu vkjson` command returned Vulkan instance and physical-device JSON. Its `properties.apiVersion` field reports **Vulkan 1.1.131** for the Mali-G76 MC4 physical device. This is the device property, distinct from the JSON's top-level instance `apiVersion` of 1.3.0 and from Android build/API properties.

The feature profile **fails ReXGlue SDK v0.10.0's Xenos GPU-emulation device gate**: `vertexPipelineStoresAndAtomics` is false. The other two unconditional Xenos requirements, `independentBlend` and `fragmentStoresAndAtomics`, are true. Disabling the Android-default `fillModeNonSolid` requirement could bypass that separate optional-feature gate, but cannot bypass the missing vertex-pipeline stores/atomics requirement. This profile therefore rules out this phone's current Vulkan driver as an Xenos GPU-emulation device for the audited SDK version. It does not say whether NFS SHIFT's retail XEX can run on another device or backend.

## Android build identity

Read-only `getprop` results:

| Property | Value |
| --- | --- |
| Product model / device | Redmi Note 8 Pro / `begonia` |
| Framework `ro.build.version.release` / SDK | `13` / `33` |
| Vendor `ro.vendor.build.version.release` / SDK | `11` / `30` |
| Product first API level | `28` |
| Build fingerprint | `Redmi/begonia/begonia:11/RP1A.200720.011/V12.5.8.0.RGGMIXM:user/release-keys` |
| Security patch | `2023-05-05` |

The framework release/SDK properties and vendor release/fingerprint disagree (13/API 33 versus 11/API 30). The report preserves that discrepancy instead of inferring a single Android base version. It does not change the physical Vulkan property reported below.

## Physical device properties and required features

The queried `VkPhysicalDeviceProperties` profile is:

| Field | Value |
| --- | --- |
| `deviceName` | `Mali-G76 MC4` |
| `apiVersion` | `1.1.131` (raw Vulkan version value `4198531`) |
| Driver name | `Mali-G76 MC4` |
| Driver info | `v1.r26p0-01eac0.66a08f2668d757b36371f0062427ea04` |
| `VK_KHR_driver_properties` conformance version | `1.2.0.2` |

Feature values came from the JSON's physical-device `features` object; `1` means reported supported and `0` unsupported.

| Feature | Reported | ReXGlue Xenos v0.10.0 consequence |
| --- | --- | --- |
| `independentBlend` | `true` | Passes unconditional Xenos device gate. |
| `fragmentStoresAndAtomics` | `true` | Passes unconditional Xenos device gate. |
| `vertexPipelineStoresAndAtomics` | **`false`** | **Fails unconditional Xenos device gate; device creation is rejected for GPU emulation.** |
| `geometryShader` | `true` | Passes the Android default requirement. |
| `fillModeNonSolid` | **`false`** | Fails the Android default requirement unless `vulkan_require_fill_mode_non_solid=false`; source fallback changes line/point polygon modes to solid fill. |

The exact feature gate is in [`vulkan_device.cpp` at the v0.10.0 tag](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/ui/vulkan/vulkan_device.cpp#L95-L140). The earlier [X6 source audit](2026-10-22-process2-xenos-vulkan11-audit.md) describes the backend-side requirements and limits.

## Extensions and queue family

The physical-device query returned 57 device extensions. Relevant entries include `VK_KHR_spirv_1_4`, `VK_KHR_swapchain`, `VK_KHR_sampler_mirror_clamp_to_edge`, and `VK_KHR_driver_properties`. `VK_KHR_dynamic_rendering` is not in the returned list, consistent with using ReXGlue's conventional render-pass path on a Vulkan 1.1 device.

Full device-extension names returned by the query:

```text
VK_KHR_incremental_present
VK_KHR_shared_presentable_image
VK_GOOGLE_display_timing
VK_KHR_16bit_storage
VK_KHR_8bit_storage
VK_KHR_bind_memory2
VK_KHR_buffer_device_address
VK_KHR_create_renderpass2
VK_KHR_dedicated_allocation
VK_KHR_depth_stencil_resolve
VK_KHR_descriptor_update_template
VK_KHR_device_group
VK_KHR_driver_properties
VK_KHR_external_fence
VK_KHR_external_fence_fd
VK_KHR_external_memory
VK_KHR_external_memory_fd
VK_KHR_external_semaphore
VK_KHR_external_semaphore_fd
VK_KHR_get_memory_requirements2
VK_KHR_image_format_list
VK_KHR_imageless_framebuffer
VK_KHR_maintenance1
VK_KHR_maintenance2
VK_KHR_maintenance3
VK_KHR_multiview
VK_KHR_relaxed_block_layout
VK_KHR_sampler_mirror_clamp_to_edge
VK_KHR_sampler_ycbcr_conversion
VK_KHR_separate_depth_stencil_layouts
VK_KHR_shader_draw_parameters
VK_KHR_shader_float16_int8
VK_KHR_shader_float_controls
VK_KHR_shader_subgroup_extended_types
VK_KHR_spirv_1_4
VK_KHR_storage_buffer_storage_class
VK_KHR_timeline_semaphore
VK_KHR_uniform_buffer_standard_layout
VK_KHR_variable_pointers
VK_KHR_vulkan_memory_model
VK_EXT_astc_decode_mode
VK_EXT_global_priority
VK_EXT_host_query_reset
VK_EXT_index_type_uint8
VK_EXT_inline_uniform_block
VK_EXT_line_rasterization
VK_EXT_queue_family_foreign
VK_EXT_scalar_block_layout
VK_EXT_separate_stencil_usage
VK_EXT_texture_compression_astc_hdr
VK_EXT_shader_subgroup_ballot
VK_EXT_shader_subgroup_vote
VK_EXT_transform_feedback
VK_EXT_external_memory_dma_buf
VK_EXT_image_drm_format_modifier
VK_ANDROID_external_memory_android_hardware_buffer
VK_KHR_swapchain
```

One queue family was reported with `queueCount=2` and `queueFlags=7` (graphics, compute, and transfer bits). The instance extensions include `VK_KHR_surface` and `VK_KHR_android_surface`; the device extensions include `VK_KHR_swapchain`. `vkjson` did **not** report a surface-specific `vkGetPhysicalDeviceSurfaceSupportKHR` result. No Android `VkSurfaceKHR` was created, so actual surface/present-queue support remains unverified.

## Probe method and evidence boundary

Commands used were read-only `adb shell getprop`, `adb shell dumpsys gpu`, `adb shell dumpsys SurfaceFlinger`, and `adb shell cmd gpu vkjson`. The returned JSON marks `vkjson` deprecated. Android's [GpuService source](https://android.googlesource.com/platform/frameworks/native/+/171cac1b603e4bb83412eb596d05a500af5d7a76/services/gpuservice/GpuService.cpp) documents it as dumping Vulkan properties as JSON. The raw JSON was not saved because it includes device and driver UUID fields; only the non-unique build/profile values above were recorded.

This confirms the connected phone's reported physical-device API version and feature bits. It does not exercise ReXGlue on Android, verify surface presentation, run Vulkan validation, or show an NFS SHIFT retail draw/frame. The coordination X6 ledger/status and all renderer/runtime source remain unchanged.
