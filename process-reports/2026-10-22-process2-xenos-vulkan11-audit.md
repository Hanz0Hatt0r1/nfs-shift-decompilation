# X6 audit: ReXGlue Xenos Vulkan 1.1 and Android ARM64

**Date:** 2026-10-22  
**Scope:** source, feature, shader-target, build-target, and package audit for the ReXGlue Xenos Vulkan backend. No renderer/runtime source or game data was changed or added to Git.

## Finding

The audited Xenos backend has a Vulkan 1.1 execution path. Its use of a Vulkan 1.3 application version and 1.4-era SDK headers does **not** by itself make a Vulkan 1.1 physical device unusable: device capabilities and guest SPIR-V are selected from the physical device's reported API version, promoted functions use extensions on older devices, and dynamic rendering has a render-pass fallback.

However, “Vulkan 1.1” is not a sufficient device profile for this backend. With Xenos GPU emulation enabled, `CreateIfSupported` unconditionally rejects devices without `independentBlend`, `fragmentStoresAndAtomics`, or `vertexPipelineStoresAndAtomics`. Vulkan 1.1 does not guarantee those optional feature bits. Linux and Android also default to requiring `geometryShader` and `fillModeNonSolid`; those can be relaxed, but the fallback paths have observable parity limits. Therefore the X6 gate is **not passed** by the source audit. No target Vulkan 1.1 device was run, and no completed NFS SHIFT draw or present on Vulkan 1.1 was demonstrated.

The source audit establishes what this ReXGlue version asks of a device. It does not establish which of the optional paths the retail SHIFT XEX actually exercises. That requires retail draw/resource evidence.

## SDK and upstream revision identity

The local SDK is `/home/pes/opt/rexglue-0.10.0/linux-amd64`. Its generated `include/rex/version.h` identifies version `0.10.0`, channel `release`, platform `linux-amd64`, timestamp `20260821_2217`. The local `lib/librexgpu-xenos.so` has SHA-256 `09745cbdda1b30b91df8c371c8141a57a41be499eab745b12f4a3041561729f7`, ELF Build ID `beebf68a6c59c198f56ecc1829070992934d4ee1`. `nm -D -C` exposes the plugin ABI entrypoints `rex_gpu_abi_version` and `rex_gpu_create`; internal renderer symbols are hidden by the build.

I verified the public GitHub release archive `rexglue-sdk-0.10.0-linux-amd64.zip` against its published asset digest `0388edb3f8fb1444f1b0ad5d440cb02d9690ac20a76b04fd6b7dcc19f59328a6`. The extracted plugin hash equals the local plugin hash above. The extracted `include/rex/version.h` hash also equals the local header hash `653ec46fee7084a85fde4ea95b9464bcefb9e22f994a2b00f764a2735a482550`. This links the installed plugin and version header to the official v0.10.0 Linux AMD64 release asset, rather than only inferring provenance from the directory name.

The official tag `v0.10.0` resolves to source commit `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`, tree `93d1bc10733b23e1c16475eb5c62e3bb2a68daa1`. Upstream `main` at `c94f5ebdcb3c9d1a460ca48e04f9758448f8d518` has the same tree. The latest upstream `development` ref observed on 2026-10-22 was `bd833a2ab69d305f99ddf57418fc38ffec8af93d` (2026-10-02). The Xenos Vulkan, generic Vulkan-device, and Xenos SPIR-V implementation files audited below are unchanged between the release tag and that development ref. Its relevant differences are build metadata/version-resource changes and a MoltenVK pin, not Vulkan device selection or Xenos rendering logic.

The installed package therefore has a source-linked release tag. For clarity, the source findings below use the tag commit; the development ref was checked for drift. The local Linux AMD64 artifact proves nothing about Android execution.

## Vulkan version selection and shader requirements

`include/rex/ui/vulkan/device.h:41-47` defines `kHighestUsedApiMinorVersion` as Vulkan 1.3. `src/ui/vulkan/vulkan_instance.cpp:111-133, 333-346` queries the loader version and advertises 1.3 when the loader reports at least 1.1; it advertises 1.0 only for a 1.0 loader. Khronos specifies that an implementation supporting 1.1 or later must not reject a higher `VkApplicationInfo::apiVersion` with `VK_ERROR_INCOMPATIBLE_DRIVER`, and newer-version functionality still requires the relevant instance/device version or enabled extension. Thus the 1.3 application target is not proof of a 1.3 device requirement.

The effective device API comes from `VkPhysicalDeviceProperties::apiVersion` in `src/ui/vulkan/vulkan_device.cpp:70-90, 519-538`. The backend queries and enables core 1.2/1.3 feature structures only when the physical device reports those versions; below 1.3, it queries the relevant KHR/EXT feature structures when their extensions exist (`vulkan_device.cpp:194-244, 295-380, 648-732`).

For Xenos guest shaders, `SpirvShaderTranslator::Features` selects SPIR-V 1.5 for a 1.2+ device, SPIR-V 1.4 when `VK_KHR_spirv_1_4` is exposed, SPIR-V 1.3 for a 1.1 device otherwise, and SPIR-V 1.0 for a 1.0 device (`src/graphics/pipeline/shader/spirv_translator.cpp:31-72`). The internal GLSL utility-shader compiler targets Vulkan 1.0 / SPIR-V 1.0 (`src/graphics/vulkan/command_processor.cpp:498-510`). For a plain Vulkan 1.1 device without the SPIR-V 1.4 extension, the guest-shader baseline is SPIR-V 1.3, which Vulkan 1.1 supports.

The SDK CMake stack pins Vulkan headers/loader sources at a Vulkan SDK revision `1.4.357.0` (`cmake/rexglue_vulkan_stack.cmake:1-15`). Those are compile-time declarations and tools, not a runtime floor. `REXGLUE_USE_VULKAN` defaults on outside Windows and controls whether Vulkan sources are built into `rexgpu-xenos` (`CMakeLists.txt:34-46`, `src/graphics/CMakeLists.txt:88-100`).

## Device requirements and fallbacks

Vulkan version numbers do not guarantee most feature bits. Khronos describes features as individually queried and enabled capabilities; unsupported bits mean the functionality is unavailable. The following requirements are confirmed in the v0.10.0 source.

| Requirement | Vulkan 1.1 status | ReXGlue Xenos v0.10.0 treatment | Consequence |
| --- | --- | --- | --- |
| `independentBlend` | Vulkan 1.0 feature, not guaranteed by API version | Hard rejection when `with_gpu_emulation` is true (`vulkan_device.cpp:95-110`) | A 1.1 device without it cannot create this Xenos GPU device. There is no implemented setting that relaxes the check. |
| `fragmentStoresAndAtomics` | Vulkan 1.0 feature, not guaranteed by API version | Hard rejection for GPU emulation (`vulkan_device.cpp:112-117`, also checked in `command_processor.cpp:926-930`). The old `vulkan_require_fragment_stores_and_atomics` CVar is explicitly deprecated and ignored. | No Xenos Vulkan GPU emulation on devices lacking it, even if a particular title draw has not yet been observed to use pixel memexport. |
| `vertexPipelineStoresAndAtomics` | Vulkan 1.0 feature, not guaranteed by API version | Hard rejection for GPU emulation (`vulkan_device.cpp:119-125`, `command_processor.cpp:932-936`). Its old require CVar is also deprecated and ignored. | No Xenos Vulkan GPU emulation on devices lacking it, even if a particular title draw has not yet been observed to use vertex memexport. |
| `geometryShader` | Optional Vulkan 1.0 feature | `vulkan_require_geometry_shader` defaults to `!REX_PLATFORM_MAC`, so it is **true on Android and Linux**. Missing support rejects initialization by default. Setting it false allows primitive conversion/expansion fallback paths (`vulkan_device.cpp:35-38`; `command_processor.cpp:938-948`; `primitive_processor.cpp:44-76`). | Relaxing the gate may permit startup, but it is not retail parity evidence. The fallback does not establish coverage of every NFS topology/state. |
| `fillModeNonSolid` | Optional Vulkan 1.0 feature | `vulkan_require_fill_mode_non_solid` also defaults true outside macOS; missing support rejects by default. If set false, non-fill polygon modes fall back to solid fill (`vulkan_device.cpp:39-42`; `command_processor.cpp:950-960`). | Startup can be allowed with a known visual loss for point/wireframe modes; whether SHIFT uses those modes is unproven. |
| `VK_KHR_swapchain` plus platform surface | Device/instance WSI extensions, not Vulkan core | Required when the Xenos system is created with a swapchain; Android surface code is compiled when `VK_USE_PLATFORM_ANDROID_KHR` is enabled (`vulkan_device.cpp:201-204, 285-288`; `vulkan_instance.cpp:140-160, 426-430`). | Required for a visible/presenting Android window, in addition to a graphics+compute queue and an actual present-capable surface/queue. |

Other capabilities are queried and enabled when present, with conditional paths rather than device-selection rejection:

- `tessellationShader`, `sampleRateShading`, `shaderClipDistance`, `shaderCullDistance`, `depthClamp`, `fullDrawIndexUint32`, sampler anisotropy, and sparse features are read from `VkPhysicalDeviceFeatures`. The backend selects stages and shader behavior based on those values. For example, transfer shaders use masked per-sample handling when sample-rate shading is absent (`render_target_cache.cpp:4301-4324`), and clip/cull output generation is conditional (`pipeline_cache.cpp:929-955`). Their absence is a title-state/parity question, not proof that all Xenos draws fail.
- `VK_KHR_dynamic_rendering` / `VkPhysicalDeviceDynamicRenderingFeaturesKHR` is optional on Vulkan 1.1. The `vulkan_dynamic_rendering` CVar defaults true but is additionally gated by `properties().dynamicRendering`; if that is false or the CVar is disabled, the backend uses conventional render passes (`command_processor.cpp:67-70, 3091-3155`). This is a real Vulkan 1.1 fallback.
- `VK_KHR_spirv_1_4` is optional for a 1.1 device; without it the translator selects SPIR-V 1.3. Vulkan 1.2+ uses SPIR-V 1.5. Neither 1.4 nor 1.5 is necessary for the 1.1 path.
- `VK_EXT_fragment_shader_interlock` is an optional alternative render-target path, selected only when configured; the source checks the feature/limits before using it (`render_target_cache.cpp:203-225`; `spirv_translator.cpp:1169-1178`). It is not evidence that NFS requires interlock.
- `VK_EXT_shader_demote_to_helper_invocation`, `VK_EXT_non_seamless_cube_map`, `VK_EXT_shader_stencil_export`, `VK_EXT_custom_border_color`, and `VK_EXT_robustness2` are optional extensions. The implementation feature-tests the relevant paths. Examples: custom border color falls back to transparent black (`texture_cache.cpp:881-925`); true null descriptors fall back to allocated null images (`texture_cache.cpp:658-671, 2958-2984`); mirror-clamp modes degrade to mirrored-repeat behavior if `samplerMirrorClampToEdge` is absent (`texture_cache.cpp:3243-3258`). These can affect visual correctness without preventing basic Vulkan initialization.
- Vulkan 1.1 minimum limits and format support still need to be checked against actual Xenos resources. The backend queries device limits, formats, render-target/sample capabilities, descriptor capacities, queue families, and present support; the API version alone does not establish those values.

The backend-level hard requirements above are mandatory for **this SDK's Xenos GPU emulation initialization**. No available retail NFS SHIFT GPU capture proves whether geometry/tessellation, wireframe/point fill, MSAA, special border colors, non-seamless cubemaps, or interlock are required by the title. Do not label these as title-required until a retail draw/resource trace uses them.

## Linux ARM64 and Android ARM64

The v0.10.0 release publishes a Linux ARM64 SDK asset, and its workflow builds `linux-arm64`. That is Linux ARM64 evidence only. The source has Android platform conditionals: `include/rex/platform.h` detects `__ANDROID__`; `include/rex/ui/vulkan/api.h:29-33` defines `VK_USE_PLATFORM_ANDROID_KHR`; `vulkan_instance.cpp` requests `VK_KHR_android_surface`; and `vulkan_presenter.cpp` has `AndroidNativeWindowSurface` creation code. Those show platform hooks, not a supported Android application build.

The audited release tree has no Android NDK/Gradle build workflow; its platform workflow list names Windows, macOS, Linux AMD64, and Linux ARM64, but not Android. There is no Android SDK package or ReXGlue NFS SHIFT app/activity lifecycle proof in the examined release. Therefore ARM64 compilation, `VK_KHR_android_surface` declarations, or Android API level do not prove an Android executable, WSI lifecycle, input/audio/storage behavior, or retail game execution.

Khronos' Android guide states that 64-bit devices first released with Android API level 29 or later must include a Vulkan 1.1 driver. That still does not imply support for the optional Xenos feature bits listed above. Device API version and each feature bit must be read from that device's Vulkan driver.

## Blockers and minimum next test

1. **Feature-profile blocker:** before Vulkan 1.1 can be a supported floor for Xenos, a target device must report `independentBlend`, `fragmentStoresAndAtomics`, and `vertexPipelineStoresAndAtomics`. If any is false, the current SDK rejects the device; an app CVar does not bypass it. The project must either scope support to devices that expose these capabilities or design and parity-test a genuine backend fallback before weakening those hard gates.
2. **Mobile default blocker:** Android defaults to requiring geometry shaders and non-solid fill even though the backend has fallback paths. First test those paths with `vulkan_require_geometry_shader=false` and `vulkan_require_fill_mode_non_solid=false` on a device missing either feature; then verify actual retail draw classes and image output before changing the app's defaults.
3. **No Android runtime qualification:** Linux ARM64 release artifacts do not cover the Android toolchain or surface path. A separate NDK/Android application build and lifecycle test remains necessary.
4. **No retail X6 scene proof:** the earlier Xenos diagnostic report records pipeline lookup and a placeholder-frame skip, not a completed guest Vulkan draw or presented retail frame. It therefore cannot establish NFS-specific feature requirements or X6 success.

**Minimum decisive run:** use the exact v0.10.0 source/tag (or a deliberately pinned newer source tree) on a physical Vulkan 1.1 device or software implementation whose `VkPhysicalDeviceProperties.apiVersion` actually reports 1.1. Log the instance/device API versions, required features, enabled extensions, graphics/compute and present queue support, surface formats, and relevant limits. Create the Xenos GPU system with swapchain; force the render-pass path using `vulkan_dynamic_rendering=false`; first run the default geometry/fill requirements, then only if necessary run the two documented fallbacks. Run a known Xenos test draw to isolate API/device bring-up, then run the first retail SHIFT draw under validation and record the real pipeline (not placeholder), `vkQueuePresentKHR`, and resulting frame. A synthetic triangle is only backend/API plumbing evidence; it does not satisfy the retail X6 scene gate. A later-API implementation with its reported version merely overridden to 1.1 is not a substitute for a genuine 1.1 implementation unless the test also removes newer extensions/features and documents that limitation.

## Recommended plan order

1. Keep the project ledger's SDK commit and X6 result unchanged until the project explicitly adopts this pinned runtime and the target-device run is captured. This report narrows the blocker but is not an integration or runtime pass.
2. Add a small capability report to the first real Xenos device run, exposing the exact required optional feature bits and device limits before title shader execution. Preserve the hard gates for independent blend and the two storage/atomic features until an alternative has a measured correctness case.
3. Test geometry and non-solid fallback modes on a real mobile Vulkan device. If they preserve all retail draw classes seen in SHIFT, set Android-specific app defaults accordingly; otherwise keep the device requirement explicit.
4. Complete a real SHIFT Vulkan draw and present on a Vulkan 1.1 device for X6; then perform Linux ARM64 and Android ARM64 builds/runs as separate X5 host gates.

## Evidence and limits

**Confirmed:** installed SDK version/platform/timestamp; local plugin and generated version header match files in the official v0.10.0 Linux AMD64 release asset; tag/source tree identities; current `main` tree identity; latest `development` revision and absence of drift in Vulkan/Xenos implementation files; Vulkan API-version negotiation; source-level feature gates, extension detection, SPIR-V selection, and dynamic-rendering fallback; Linux ARM64 release workflow and Android WSI preprocessor/source hooks.

**Not established:** runtime behavior on any Vulkan 1.1 device; the feature profile of the target Redmi phone; Android NDK build or surface presentation; successful Vulkan validation on Android; title-specific use of optional Xenos paths; or a completed retail SHIFT Vulkan draw/present. The Xbox XEX and game assets were not copied into this report branch. `coordination/xbox360_rexglue_status.json` and renderer/runtime source remain unchanged.

## Source references

- [Official v0.10.0 release and assets](https://github.com/rexglue/rexglue-sdk/releases/tag/v0.10.0)
- [v0.10.0 tag source tree](https://github.com/rexglue/rexglue-sdk/tree/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2)
- [v0.10.0 Xenos device checks, extension requests and feature enablement](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/ui/vulkan/vulkan_device.cpp)
- [Vulkan instance/API version and WSI extensions](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/ui/vulkan/vulkan_instance.cpp)
- [Vulkan1.1 SPIR-V selection](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/graphics/pipeline/shader/spirv_translator.cpp)
- [Xenos feature gates and dynamic-rendering fallback](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/graphics/vulkan/command_processor.cpp)
- [Primitive geometry and fill fallback checks](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/graphics/vulkan/primitive_processor.cpp)
- [Android Vulkan platform macro](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/include/rex/ui/vulkan/api.h)
- [Android surface presenter path](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/src/ui/vulkan/vulkan_presenter.cpp)
- [CMake Vulkan header/tool pins](https://github.com/rexglue/rexglue-sdk/blob/f5337cdc947ff6d4c4196737e2c807a48f2a1fc2/cmake/rexglue_vulkan_stack.cmake)
- [Current upstream main at c94f5eb](https://github.com/rexglue/rexglue-sdk/tree/c94f5ebdcb3c9d1a460ca48e04f9758448f8d518); [development at bd833a2](https://github.com/rexglue/rexglue-sdk/tree/bd833a2ab69d305f99ddf57418fc38ffec8af93d)
- [Khronos feature reporting and enablement](https://docs.vulkan.org/spec/latest/chapters/features.html); [Khronos `VkApplicationInfo::apiVersion` behavior](https://docs.vulkan.org/refpages/latest/refpages/source/VkApplicationInfo.html); [Vulkan version guide](https://docs.vulkan.org/guide/latest/versions.html)
- [Khronos Android Vulkan platform requirements](https://docs.vulkan.org/guide/latest/platforms.html)
