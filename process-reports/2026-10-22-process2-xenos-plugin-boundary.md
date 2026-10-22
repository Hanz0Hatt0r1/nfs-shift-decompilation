# Process 2 — ReXGlue 0.10.0 Xenos GPU plugin boundary

Date: 2026-10-22
Scope: Xbox 360/Xenos graphics integration in the generated ReXGlue app only. P1-supplied guest runtime observations are used solely to classify graphics API boundaries; no P1 waiter implementation, trap, P-code, or scheduler code is inspected or changed. This is a report-only task.

## Finding

The earlier no-GPU warnings had a direct configuration cause: RuntimeConfig had no graphics object and gpu_plugin was empty. ReXGlue 0.10.0 ships a compatible Xenos plugin with ABI v1. The follow-up diagnostic confirms the loader boundary: --gpu_plugin=xenos alone failed because the loader looks beside the executable; after the SDK library was copied there, the retail run initialized the Vulkan presenter, registered the guest interrupt callback, created Xenos-derived Vulkan pipelines, and reached a placeholder-frame skip in IssueSwap.

The app's CMake and OnPreSetup source remain unconfigured, so a clean build still needs both plugin selection and reproducible staging. The manual copy in the diagnostic run demonstrates the library is loadable; use GPU_PLUGINS xenos to stage it on each build.

## Target and runtime evidence

Target: Need for Speed: Shift Europe Xbox 360, Title ID 454108B4, Media ID 60DAC9C5. The XEX SHA-256 is 8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58.

The supplied run configuration is ReXGlue 0.10.0, Linux AMD64, --video_driver=wayland and --audio_mute, with gpu_plugin unset. Its log reports the following at graphics initialization:

- VdSetGraphicsInterruptCallback: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VdInitializeRingBuffer: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VdEnableRingBufferRPtrWriteBack: no GPU emulation loaded (gpu_plugin not set); call ignored.
- VFS path ShaderDumpxe:\CompareBackEnds resolves to [no device].

The matching local run logs under /home/pes/work/nfsshift-rex/out/build/linux-amd64-release/logs/ independently show the same three no-plugin warnings at lines 26–28, including nfs_shift_032.log. The [no device] message is a VFS path/device result; by itself it does not establish a shader-translation failure.

The supplied observation that the run avoided InvalidFunctionTrap for 2:35 while Core 2/0:Main held around 99% CPU is not evidence of a guest draw, menu, or present. A busy guest thread could continue running without a functioning GPU, but that explanation remains unproven. No trap internals are examined here.

The later plugin-enabled diagnostic is recorded in /home/pes/work/nfsshift-rex/out/build/linux-amd64-release/logs/nfs_shift_039.log. It selected the NVIDIA GeForce GTX 950 Vulkan device and created swapchains (1536x864 at line 135, then 1920x1080 at line 149). The guest callback was registered at line 167. Xenos/Vulkan pipeline-state requests appear at lines 194, 230–231, and 239. At line 238 IssueSwap logged “Skipping Vulkan frame presentation due to async placeholder draw usage in this frame”; at line 254 the guest runtime logged an invalid/unregistered function at 0x8264F580. The skipped-frame warning and fatal are 19 ms apart and on different host thread IDs. The log contains no “no GPU emulation loaded” warning in this run. The user reports that setting --gpu_plugin=xenos without staging first failed with “GPU plugin 'xenos' not found at .../out/build/linux-amd64-release/librexgpu-xenos.so. Stage it next to the executable (GPU_PLUGINS xenos in rexglue_configure_target)”; after copying the exact SDK library there, plugin loading and Vulkan setup succeeded before the guest runtime later terminated at the invalid function.

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

The ABI's backend string is a request, not a promise that every plugin build contains every backend. The plugin itself has a diagnostic for a requested backend that was not compiled into it. In this diagnostic the host log identifies the NVIDIA Vulkan device, creates a Vulkan swapchain, and reaches the Vulkan placeholder-skip path, proving the Vulkan backend was active for this run.

## Current app wiring

In /home/pes/work/nfsshift-rex/CMakeLists.txt:24 the target is currently configured as rexglue_setup_target(nfs_shift), without GPU_PLUGINS. The app header /home/pes/work/nfsshift-rex/src/nfs_shift_app.h:21 leaves its OnPreSetup(RuntimeConfig&) override commented out. At the earlier no-plugin stage the build output lacked librexgpu-xenos.so. For the later diagnostic, the user copied the SDK plugin into the executable directory. SHA-256 of that staged file matches the installed SDK copy exactly (09745cbdda1b30b91df8c371c8141a57a41be499eab745b12f4a3041561729f7). The CMake source still lacks GPU_PLUGINS, so a clean rebuild will not reproduce that manual stage.

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

The earlier no-plugin calls alone did not reveal ring contents or draw state. The plugin-enabled diagnostic advances beyond them: SetInterruptCallback is logged, Vulkan/Xenos pipeline lookup is reached, and a PM4_XE_SWAP path reaches IssueSwap. The placeholder log confirms a guest-derived draw attempt, but that draw returns before the real guest pipeline is bound, and IssueSwap explicitly skips frame presentation. This proves ring/command-processor progress through at least a swap packet, but no raw ring dump or presented retail frame is available.

## New P1 display-path evidence: PersistDisplay is not Present

P1 supplied a GDB chain from this XEX: guest function 0x823A4E48 calls the VdPersistDisplay import at instruction 0x823A5518 (guest LR 0x823A551C), then execution reaches 0x823B34A0 and waiter 0x823A0310. The live waiter object was reported as 0xB7365F00 with the consumer-pointer field at obj+10896 equal to 1, producer field at obj+10908 equal to 21, and target index 3. These are P1-observed values; this report does not infer queue meaning from them.

The call name can be misleading. The local SDK 0.10.0 runtime exports rex::kernel::xboxkrnl::VdPersistDisplay_entry at host address 0x5A2FB0 (size 0x8A). Its local x86-64 disassembly conditionally obtains a kernel heap, allocates a 64-byte block with 32-byte alignment, stores the resulting guest pointer, and returns 1. It does not call the GPU graphics system or command processor. Upstream xboxkrnl_video.cpp describes the output pointer as a value later passed to MmFreePhysicalMemory(1, *ptr), and the implementation is the same allocation shim. Consequently this observed VdPersistDisplay call is not a Xenos command, buffer swap, D3D draw, or presentation event. It is serviced by the Xbox kernel compatibility layer even when gpu_plugin is unset.

ReXGlue's actual Xbox swap entry is VdSwap_entry. The upstream implementation takes a primary-ring buffer location, a six-dword frontbuffer texture-header fetch, frontbuffer address/format/colorspace/dimensions, converts the frontbuffer virtual address to a physical address, and writes a PM4_XE_SWAP packet plus signature, address, width, and height into the reserved ring area. The Xenos packet parser dispatches PM4_XE_SWAP to ExecutePacketType3_XE_SWAP, which advances the read pointer and invokes IssueSwap. The Vulkan implementation of IssueSwap requires a presenter and begins a host GPU submission; if no presenter is available it logs XELOG_GPU PRESENT: NO PRESENTER. That is the concrete ReXGlue display route that the Xenos plugin is meant to service.

Static XEX evidence gives a useful next breakpoint: generated/default/nfs_shift_recomp.173.cpp has a VdSwap import call at guest instruction 0x823A5114 (LR 0x823A5118), statically inside sub_823A4E48. The same function has the later VdPersistDisplay call at 0x823A5518. This static callsite does not prove the earlier branch executed in P1's run. P1's supplied GDB chain reports a hit at VdPersistDisplay, not a hit at VdSwap. Separately, the plugin-enabled log's placeholder skip proves that Vulkan IssueSwap was reached; the SDK packet dispatcher calls IssueSwap from PM4_XE_SWAP. This establishes command-processor swap handling in that run, but without a GDB hit it does not prove that the guest used this exact static VdSwap callsite at 0x823A5114 rather than writing the packet through another route. It still does not establish an executed real-pipeline draw or a screen present.

The Xenos plugin services the ring-buffer and PM4_XE_SWAP paths: the SDK's VdInitializeRingBuffer and VdEnableRingBufferRPtrWriteBack exports forward to IGraphicsSystem and its CommandProcessor; the processor decodes PM4_XE_SWAP through the backend's IssueSwap. In the plugin-enabled run, IssueSwap reached the placeholder-frame skip branch, so the presenter existed but that frame was intentionally not presented. The plugin does not service VdPersistDisplay, which is a kernel memory-allocation compatibility entrypoint. Whether GPU completion interrupts unblock the reported game waiter is not established.

**Minimal next check for this evidence:** keep the ABI-v1 Xenos plugin selected and staged as described above, then put a GDB breakpoint at guest VdSwap callsite 0x823A5114 (or its VdSwap import entry). If hit, preserve the call arguments and the 64-dword buffer after VdSwap returns; confirm PM4_XE_SWAP and its signature/address/dimensions reach the Xenos command processor, then confirm Vulkan IssueSwap has a presenter and reaches host presentation. If this callsite is not hit, the reported VdPersistDisplay/waiter chain still has no demonstrated connection to presentation. A visible frame and a game draw remain separate claims requiring their own capture evidence.

## Async placeholder path and 0x8264F580

Upstream VulkanCommandProcessor::IssueDraw sets frame_used_async_placeholder_pipeline_ when asynchronous shader compilation is enabled and pipeline lookup returns a placeholder, then returns true before binding the guest graphics pipeline or recording the guest draw itself. In the same function, ConfigurePipeline requests/queues the real pipeline; the Vulkan pipeline cache initially supplies a placeholder pixel shader whose source discards fragments. Upstream main defaults both async_shader_compilation and vulkan_async_skip_incomplete_frames to true (both are hot-reload CVars); the installed binary contains their names/descriptions, and the diagnostic log proves the skip condition was active.

IssueSwap first requires a graphics system and Presenter, then BeginSubmission. If async_shader_compilation, vulkan_async_skip_incomplete_frames, and frame_used_async_placeholder_pipeline_ are all true, it calls EndSubmission(true) and returns before the remainder of IssueSwap's presentation path. EndSubmission may queue-submit Vulkan work, but this branch does not call the presenter to present the frame. Therefore log 039's skip message proves that: (1) a presenter existed; (2) the command processor decoded a swap and entered Vulkan IssueSwap; and (3) a draw reached Vulkan pipeline lookup but the pipeline was still a placeholder. It does not prove a real Vk draw was recorded or a Vulkan present occurred. The swapchain-created log alone is not a present either.

In log 039 the placeholder-skip warning is at 20:56:48.760 on host thread 1797070. The guest fatal at 20:56:48.779 is on host thread 1797073, after two VFS failures resolving render\shaders\cache\. The placeholder branch ends its submission and returns; that branch contains no call into guest code. Temporal proximity therefore does not establish that the skipped present caused the guest invalid-function fatal. P1 also supplied a separate GDB run that segfaulted in generated sub_823A0B50 with a guest call chain; this report does not inspect that guest chain or assign it to the renderer.

**Controlled next run:** retain the matching plugin beside nfs_shift and run once with --no-vulkan_async_skip_incomplete_frames, leaving async compilation enabled. This changes only the skip policy, so IssueSwap can proceed beyond the placeholder gate; record whether the host Vulkan present call occurs and whether 0x8264F580 still fires. The diagnostic may display incomplete/stale content and is not parity evidence. Then, if the goal is a complete guest draw rather than only testing presentation transport, run with --no-async_shader_compilation so pipeline creation completes synchronously and the placeholder path is avoided. The CVar CLI accepts booleans as --name and --no-name.

## Facts, inferences, and limits

**Confirmed:** ABI v1 contract and matching staged plugin hash; loader lookup and manual staging requirement; plugin reached SetInterruptCallback; Vulkan device and swapchains were initialized; Xenos shader/pipeline state requests occurred; Vulkan IssueSwap took the placeholder-skip branch; a draw pipeline lookup marked the frame as placeholder; and the guest fatal followed 19 ms later on a different host thread. The P1-supplied VdPersistDisplay/waiter values remain evidence from a separate GDB observation.

**Supported inference:** the plugin-enabled run consumed a PM4_XE_SWAP packet and attempted a guest-derived draw path. The packet dispatcher and placeholder flag assignments in upstream ReXGlue source explain the observed skip log. The exact guest VdSwap callsite that supplied the packet was not captured.

**Not established:** execution of the guest VdSwap callsite at 0x823A5114; the exact guest draw packet variant, ring contents, or resources; a completed Vulkan draw using the retail shader pipeline; host vkQueuePresent/visible frame; menu; visual parity; or causation between the skipped present and 0x8264F580. Do not infer these from pipeline-state log lines or swapchain creation alone.

No renderer/runtime source was changed. This update analyzes the user's plugin-enabled diagnostic log; it does not claim that this agent ran the game or Vulkan validation.

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
- [Xbox video imports, including VdPersistDisplay and VdSwap](https://github.com/rexglue/rexglue-sdk/blob/main/src/kernel/xboxkrnl/xboxkrnl_video.cpp)
- [Xenos swap packet decode and IssueSwap dispatch](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/command_processor.cpp)
- [Vulkan IssueSwap and presenter requirement](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/vulkan/command_processor.cpp)
- [PM4_XE_SWAP packet constant](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/graphics/xenos.h)
- [Async shader and incomplete-frame CVar defaults](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/command_processor.cpp)
- [Placeholder draw handling and Vulkan IssueSwap skip path](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/vulkan/command_processor.cpp)
- [Placeholder pixel shader and async pipeline creation](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/vulkan/pipeline_cache.cpp)
- [CMake plugin staging](https://github.com/rexglue/rexglue-sdk/blob/main/cmake/rexglue_helpers.cmake)

Upstream main source was retrieved for call-routing and placeholder-path cross-checks. The exact source commit corresponding to the installed SDK 0.10.0 package was not identified. Version-specific ABI, plugin hash, PersistDisplay disassembly, logs, and staged output are local evidence; upstream source explains the code path and defaults but is not claimed to be byte-for-byte identical to the installed package.
