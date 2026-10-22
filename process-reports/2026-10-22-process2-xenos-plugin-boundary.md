# Process 2 — ReXGlue 0.10.0 Xenos GPU plugin boundary

Date: 2026-10-22
Scope: Xbox 360/Xenos graphics integration in the generated ReXGlue app only. No Process 1 trap, P-code, scheduler, or guest-runtime analysis is included. This is a report-only task.

## Finding

The no-GPU warnings have a direct configuration cause: the app's RuntimeConfig has no graphics object and gpu_plugin is empty. ReXGlue 0.10.0 ships a compatible Xenos plugin. The installed plugin exports the ABI v1 factory functions and its ABI-version function returns 1, matching the installed SDK header. However, it is not currently staged next to the nfs_shift executable, the app CMake target does not request it, and the app's OnPreSetup override is commented out. Thus there is no evidence that the host loader has loaded the plugin or that guest GPU setup has run.

The minimum next step is two-part: select the plugin by setting gpu_plugin to xenos, and stage the matching library beside the executable. These are separate operations. Selecting a plugin name does not stage the shared library; staging it does not select it.

## Target and runtime evidence

Target: Need for Speed: Shift Europe Xbox 360, Title ID 454108B4, Media ID 60DAC9C5. The XEX SHA-256 is 8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58.

The supplied run configuration is ReXGlue 0.10.0, Linux AMD64, --video_driver=wayland and --audio_mute, with gpu_plugin unset. Its log reports the following at graphics initialization:

- VdSetGraphicsInterruptCallback: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VdInitializeRingBuffer: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VdEnableRingBufferRPtrWriteBack: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VFS path ShaderDumpxe:\CompareBackEnds resolves to [no device].

The matching local run logs under /home/pes/work/nfsshift-rex/out/build/linux-amd64-release/logs/ independently show the same three no-plugin warnings at lines 26–28, including nfs_shift_032.log. The [no device] message is a VFS path/device result; by itself it does not establish a shader-translation failure.

The supplied observation that the run avoided InvalidFunctionTrap for 2:35 while Core 2/0:Main held around 99% CPU is not evidence of a guest draw, menu, or present. A busy guest thread could continue running without a functioning GPU, but that explanation remains unproven. No trap internals are examined here.

## SDK 0.10.0 plugin and ABI contract

Version-specific local SDK artifacts are installed under /home/pes/opt/rexglue-0.10.0/linux-amd64.

The installed header include/rex/system/gpu_plugin.h establishes:

- The package documents one current GPU plugin, rexgpu-xenos.
- kGpuPluginAbiVersion is 1. A comment requires bumping it when GpuCreateInfo or IGraphicsSystem changes.
- The required C exports are rex_gpu_abi_version() and rex_gpu_create(uint32_t abi_version, const GpuCreateInfo* info).
- GpuCreateInfo includes struct_size and a backend string. The documented backend requests are d3d12, vulkan, or any.
- LoadGpuPlugin(name, backend) loads rexgpu-<name> from the executable directory. It reports missing files, exports, ABI mismatch, or factory failure; the library is retained until process exit.
- The default backend request is any.

The installed release target is rex::gpu-xenos, resolving to lib/librexgpu-xenos.so. The SDK directory also has debug and relwithdebinfo variants of that same Xenos plugin; no other librexgpu-* implementation is present in this Linux AMD64 package.

Binary inspection of /home/pes/opt/rexglue-0.10.0/linux-amd64/lib/librexgpu-xenos.so confirms exported symbols rex_gpu_abi_version and rex_gpu_create. Loading this library directly and calling rex_gpu_abi_version returned 1, matching the installed header. Its SONAME is librexgpu-xenos.so and it depends on librexruntime.so. Its exported/undefined symbol and embedded-string tables include Vulkan provider and command-processor code. This supports that the package contains a Vulkan-capable Xenos build; it does not prove that the app loader selected it, that the factory created a system, that a Vulkan device/surface initialized, or that this title presented a frame.

The ABI's backend string is a request, not a promise that every plugin build contains every backend. The plugin itself has a diagnostic for a requested backend that was not compiled into it. The installed binary contains Vulkan code references, but a title run with a selected Vulkan backend was not performed for this report.

## Current app wiring

In /home/pes/work/nfsshift-rex/CMakeLists.txt:24 the target is currently configured as rexglue_setup_target(nfs_shift), without GPU_PLUGINS. The app header /home/pes/work/nfsshift-rex/src/nfs_shift_app.h:21 leaves its OnPreSetup(RuntimeConfig&) override commented out. The current build output directory has nfs_shift but no staged librexgpu-xenos.so. The runtime logs' “gpu_plugin not set” messages agree with those source/configuration facts.

The SDK's generated project helper at rexglue_evidence/generated/rexglue.cmake:77–108 accepts GPU_PLUGINS and forwards it to rexglue_configure_target. The installed SDK helper lib/cmake/rexglue/rexglue_helpers.cmake:145–165 copies each requested plugin next to the executable after build. This is needed because GPU plugins are runtime-loaded rather than linked.

The RuntimeConfig header says an empty graphics plugin name means no GPU emulation. ReXApp exposes OnPreSetup(RuntimeConfig&) before Runtime::Setup. The app also has the gpu_plugin CVar with description “GPU emulation plugin to load at startup (e.g. 'xenos'); empty disables GPU emulation”. The CVar CLI binding maps a non-boolean CVar named gpu_plugin to --gpu_plugin, so the equivalent launch option is --gpu_plugin=xenos. The durable source-level alternative is to assign config.gpu_plugin = "xenos" in OnPreSetup. Leave config.graphics unset when using the plugin path. The runtime hook can override the CVar-derived config; do not configure conflicting values in both places.

The minimal target configuration is:

```cmake
rexglue_setup_target(nfs_shift GPU_PLUGINS xenos)
```

For a persistent app-level selection, the hook is:

```cpp
void OnPreSetup(rex::RuntimeConfig& config) override {
  config.gpu_plugin = "xenos";
}
```

For a one-run check after rebuilding/staging, use --gpu_plugin=xenos together with the existing game and user data paths. The loader searches beside the executable; LD_LIBRARY_PATH alone does not satisfy that documented lookup rule.

## Minimal setup contract and guest resources

The installed include/rex/system/interfaces/graphics.h distinguishes presentation setup from guest GPU setup:

- SetupGuestGpu wires guest MMIO, the command processor, and a vsync worker using the Runtime FunctionDispatcher and KernelState.
- SetupPresentation must happen before SetupGuestGpu if a visible presentation is desired. The interface warns that Vulkan backends can bake swapchain support into the provider; a headless provider cannot be upgraded in place.
- The Xbox Vd services are optional methods on IGraphicsSystem. Without the concrete Xenos system, their default implementations are no-ops; the current kernel-import wrappers log and ignore these calls when no GPU system exists.

For this XEX, the already observed guest initialization values are:

- VdSetGraphicsInterruptCallback receives callback 0x823B37B8 and user data 0xB7365F00. The guest call instruction is 0x823B9E34.
- VdInitializeRingBuffer receives physical pointer 0x09752580 and size_log2 12, i.e. a 4 KiB ring. The guest call instruction is 0x823B3C48; the pointer is obtained through MmGetPhysicalAddress immediately beforehand.
- VdEnableRingBufferRPtrWriteBack receives pointer 0x17AF403C and block_size_log2 6, i.e. a 64-byte update block. The guest call instruction is 0x823B3C80.

These resources and calls are enough to identify the first host/guest GPU handoff boundary. They do not reveal the ring contents, a PM4 draw packet, shader inputs, render-target data, or a frame boundary. After plugin selection and staging, the first runtime criterion is that plugin loading and SetupGuestGpu succeed and the three no-plugin warnings disappear. The next criterion is observable ring consumption and packet/resource provenance. Only a guest-originated Xenos draw followed by its resolve/flip and same-frame host Vulkan submission/present proves the first retail frame.

## Facts, inferences, and limits

**Confirmed from the installed SDK and local app:** ABI v1 contract; matching plugin ABI return value; factory exports; the single Xenos plugin target in this Linux package; plugin lookup from the executable directory; CMake staging behavior; empty gpu_plugin semantics; app CMake/hook state; current no-plugin warnings; and observed XEX Vd arguments.

**Inference:** enabling and staging this matching plugin should route these guest services into ReXGlue Xenos GraphicsSystem/CommandProcessor. The guest ring allocation/arguments make that the next bounded integration experiment.

**Not established:** successful LoadGpuPlugin invocation by nfs_shift; successful Vulkan device or Wayland surface creation; successful SetupGuestGpu; guest command writes or read-pointer progress; first PM4 packet; DrawIndexedPrimitive-equivalent Xenos packet; resolve/flip; menu; Vulkan present; retail visual parity; or why Core 2/0:Main was busy. Do not infer any of these from the ABI probe, package contents, or thread CPU percentage.

No renderer/runtime files were changed, and no plugin-enabled game run or Vulkan validation was performed. The ABI probe only loaded the installed shared library and read its version export.

## Source references

Primary version-matched evidence is the installed ReXGlue 0.10.0 package: include/rex/system/gpu_plugin.h (ABI and loader contract), include/rex/system/interfaces/graphics.h (setup ordering and Vd services), include/rex/runtime.h (RuntimeConfig), include/rex/rex_app.h (OnPreSetup), include/rex/cvar_cli.h (CLI CVar spelling), lib/cmake/rexglue/rexglue_helpers.cmake (staging), and lib/cmake/rexglue/rexglueTargets-release.cmake (rex::gpu-xenos target). Local app evidence is CMakeLists.txt, src/nfs_shift_app.h, and out/build/linux-amd64-release/logs/nfs_shift_032.log.

Official upstream source navigation:

- [GPU plugin ABI](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/system/gpu_plugin.h)
- [GPU plugin loader](https://github.com/rexglue/rexglue-sdk/blob/main/src/system/gpu_plugin_loader.cpp)
- [Graphics system interface](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/system/interfaces/graphics.h)
- [Runtime configuration](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/runtime.h)
- [ReXApp setup hooks](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/rex_app.h)
- [App setup and CVar application](https://github.com/rexglue/rexglue-sdk/blob/main/src/ui/rex_app.cpp)
- [CVar CLI binding](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/cvar_cli.h)
- [CMake plugin staging](https://github.com/rexglue/rexglue-sdk/blob/main/cmake/rexglue_helpers.cmake)

Direct raw-GitHub retrieval timed out during this run. Therefore version-specific statements above are based on the locally installed SDK 0.10.0 headers, CMake metadata, runtime/plugin binaries, and local logs; upstream links are provided for review, not used to claim that this installed package matches the current main branch byte-for-byte.
