# Process 2 — Xbox 360 renderer frontier for Need for Speed: Shift

Date: 2026-10-22
Scope: Xbox 360 XEX / Xenos graphics initialization and the earliest evidenced path toward a guest draw and presentation. This is a renderer-only handoff; it does not inspect the Process 1 guest trap or modify Process 1 files.

## Result

The earliest graphics path confirmed by both generated guest code and an actual ReXGlue guest execution reaches Xbox video-service setup: the title registers a graphics-interrupt callback, allocates/configures a command ring, and invokes ring-buffer services. In the captured host run those three services were ignored because no GPU plugin was configured. The evidence stops before any confirmed guest Xenos draw packet, resolve/flip, or Vulkan present. Therefore a retail SHIFT draw through Vulkan is **not yet demonstrated**.

The nearest bounded task is to make the existing app load ReXGlue's Xenos GPU plugin and stage it with the executable, then instrument the guest ring through the first guest-originated PM4 draw and same-frame resolve/flip/present. This is a plugin wiring task, not an invitation to replace Xenos translation, lighting, or shaders speculatively.

## Binary, run, and evidence provenance

- Target: Need for Speed: Shift Europe Xbox 360, Title ID 454108B4, Media ID 60DAC9C5.
- XEX path used locally: /home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/360 Utility Batch Create Extract v1.2 Language Support/Need for Speed - Shift (Europe) xbox/default.xex.
- SHA-256: 8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58.
- Host run: generated ReXGlue app, Linux amd64 release, ReXGlue 0.10.0, executable /home/pes/work/nfsshift-rex/out/build/linux-amd64-release/nfs_shift.
- Run log: /home/pes/work/nfsshift-rex/out/build/linux-amd64-release/logs/nfs_shift_012.log, lines 26–28. It reports “no GPU emulation loaded (gpu_plugin not set); call ignored” for VdSetGraphicsInterruptCallback, VdInitializeRingBuffer, and VdEnableRingBufferRPtrWriteBack.
- GDB observations below were taken at the guest kernel import wrappers while the title was executing. The PowerPC context LR was read at PPCContext base + 0x100, consistent with the register layout in include/rex/ppc/context.h. These observations are distinct from the static instruction-comment listing.
- Static listing source: ReXGlue-generated recompilation files under /home/pes/work/nfsshift-rex/generated/default/. Each complete function body is reproduced below. The comments identify original PowerPC instructions, while the surrounding C is generated translation; this is **not raw XEX objdump output**. No raw objdump was present in the accessible evidence package, so these blocks are explicitly not mislabeled as one.

## Earliest confirmed graphics-init chain

### Guest execution and arguments

1. GDB stopped in the host wrapper for VdSetGraphicsInterruptCallback. Guest LR was 0x823B9E38, so its guest call instruction is at 0x823B9E34. The guest caller was sub_823B9DA0. Captured guest arguments: r3 callback 0x823B37B8; r4 user data 0xB7365F00.
2. The caller chain observed at that import was sub_823B9DA0 → sub_823A0560 → sub_8264C858 → sub_82FC1550 → sub_82FBDF58 → sub_82D30380. Independently, the complete translated body of sub_823A0560 calls sub_823B9DA0 at guest instruction 0x823A0688 (LR becomes 0x823A068C).
3. In sub_823B9DA0, the call to sub_823B3A48 is at guest instruction 0x823B9E90 (LR 0x823B9E94). That helper sets up the command ring.
4. GDB stopped in VdInitializeRingBuffer with guest LR 0x823B3C4C; the call instruction is 0x823B3C48, inside sub_823B3A48. Immediately before it, that function calls MmGetPhysicalAddress at 0x823B3C40 (LR 0x823B3C44) on the ring storage pointer. Captured Vd arguments: r3 physical address 0x09752580, r4 12. The API defines r4 as size-log2, so this invocation requests a 4 KiB ring.
5. GDB stopped in VdEnableRingBufferRPtrWriteBack with guest LR 0x823B3C84; the call instruction is 0x823B3C80, again in sub_823B3A48. Captured arguments: r3 0x17AF403C, r4 6; the API's block-size-log2 argument makes this a 64-byte write-back block.
6. The app log independently confirms all three host calls were no-ops because the app had no GPU plugin. The runtime capture was terminated before a guest draw was recorded.

The ring storage is prepared inside sub_823B3A48 after calls to sub_82FBF360; the ring pointer is then converted by the guest MmGetPhysicalAddress import before Vd initialization. The exact allocation policy is not asserted here. The RPtr write-back target is formed from graphics-object memory by the guest helper and is corroborated by the captured argument value. The callback address and both ring arguments are guest values, not synthetic host draws.

### Current integration boundary and one testable task

The generated app currently calls rexglue_setup_target(nfs_shift) with no GPU plugin selection in /home/pes/work/nfsshift-rex/CMakeLists.txt:24; its app header has the OnPreSetup(RuntimeConfig&) override commented out at /home/pes/work/nfsshift-rex/src/nfs_shift_app.h:21. The installed Xenos plugin binary exists at /home/pes/opt/rexglue-0.10.0/linux-amd64/lib/librexgpu-xenos.so; its dynamic symbols reference ReXGlue Vulkan provider/allocator code, but this does not establish that the plugin is staged, selected, successfully initialized, or that this title reaches a frame.

**Minimal task:** in the ReXGlue app integration, set RuntimeConfig::gpu_plugin to xenos in OnPreSetup and configure the target with GPU_PLUGINS xenos, then run on the existing Linux Vulkan build. Keep the generic Xenos command processor and graphics-system setup separate from XCB/Wayland surface code so the same renderer core can later be built for ARM64/Android. Do not port host-window code into the renderer core.

**Runtime acceptance criterion:**

- startup log proves the Xenos plugin was loaded and the guest graphics system initialized;
- the three Vd calls above no longer produce “no GPU emulation loaded” warnings;
- a trace shows a guest-originated command-ring packet being consumed as a Xenos indexed draw, followed by the relevant color/depth resolve or swap/flip work and a Vulkan host submission/present for the same frame;
- retain packet/register/resource provenance so the result can be compared to the retail title's actual inputs.

A plugin-load log alone is only infrastructure progress. A synthetic clear, test triangle, or standalone UI frame is not a retail draw and does not satisfy this criterion.

### Evidence versus inference

**Confirmed:** XEX hash; the guest function/call addresses in the generated listing; observed guest LR and r3/r4 values at three video-service imports; observed guest caller stack for callback registration; and log messages showing that the host video-service calls were ignored with no plugin configured.

**Supported inference:** sub_823A0560 and sub_823B9DA0 form the title's early graphics initialization path, and sub_823B3A48 configures ring-buffer resources. This follows from the continuous guest translations, observed callers, service names, and arguments.

**Not established:** which guest function submits the first actual retail draw; any PM4 opcode/packet contents; render target formats or dimensions for that draw; shader bytecode or translated SPIR-V; resolve/flip chain; a Vulkan frame from this title; visual parity; ARM64/Android build success; or Vulkan 1.1 validation success. No lighting rewrite, normal mapping, or other rendering enhancement is justified by this evidence.

## ReXGlue interface references

These upstream source files explain the plugin boundary. The local run evidence remains the version-specific 0.10.0 log and binary; upstream main is architectural corroboration, not a claim that the installed build was byte-for-byte current.

- [RuntimeConfig and gpu_plugin](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/runtime.h)
- [RexApp::OnPreSetup](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/rex_app.h)
- [App setup and GPU plugin loading](https://github.com/rexglue/rexglue-sdk/blob/main/src/ui/rex_app.cpp)
- [GPU plugin loader](https://github.com/rexglue/rexglue-sdk/blob/main/src/system/gpu_plugin_loader.cpp)
- [IGraphicsSystem guest GPU setup and ring-buffer interface](https://github.com/rexglue/rexglue-sdk/blob/main/include/rex/system/interfaces/graphics.h)
- [Xbox video imports forwarded to the graphics system](https://github.com/rexglue/rexglue-sdk/blob/main/src/kernel/xboxkrnl/xboxkrnl_video.cpp)
- [Xenos plugin backend construction](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/plugin_main.cpp)
- [CMake GPU plugin staging option](https://github.com/rexglue/rexglue-sdk/blob/main/cmake/rexglue_helpers.cmake)

## Complete uninterrupted generated function translations

These are complete function bodies from the SHA-identified XEX's ReXGlue-generated guest translation. They include every translated branch and instruction annotation relied upon above. They are included inline so the report remains useful without access to a local generated file. They are not original raw machine-code objdump listings.

### sub_823A0560 — caller of sub_823B9DA0

Source: generated/default/nfs_shift_recomp.88.cpp, lines 4630–4818 inclusive.

```cpp
DEFINE_REX_FUNC(sub_823A0560) {
	REX_FUNC_PROLOGUE();
	uint32_t ea{};
	// mflr r12
	ctx.r12.u64 = ctx.lr;
	// bl 0x826d98c4
	ctx.lr = 0x823A0568;
	__savegprlr_27(ctx, base);
	// stwu r1,-128(r1)
	ea = -128 + ctx.r1.u32;
	REX_STORE_U32(ea, ctx.r1.u32);
	ctx.r1.u32 = ea;
	// li r11,0
	ctx.r11.s64 = 0;
	// mr r29,r4
	ctx.r29.u64 = ctx.r4.u64;
	// stw r11,0(r8)
	REX_STORE_U32(ctx.r8.u32 + 0, ctx.r11.u32);
	// lis r4,9344
	ctx.r4.s64 = 612368384;
	// li r3,24192
	ctx.r3.s64 = 24192;
	// mr r30,r6
	ctx.r30.u64 = ctx.r6.u64;
	// mr r28,r7
	ctx.r28.u64 = ctx.r7.u64;
	// mr r27,r8
	ctx.r27.u64 = ctx.r8.u64;
	// bl 0x82fbf360
	ctx.lr = 0x823A0590;
	sub_82FBF360(ctx, base);
	// mr. r11,r3
	ctx.r11.u64 = ctx.r3.u64;
	ctx.cr0.compare<int32_t>(ctx.r11.s32, 0, ctx.xer);
	// beq 0x823a0608
	if (ctx.cr0.eq) goto loc_823A0608;
	// addi r10,r11,131
	ctx.r10.s64 = ctx.r11.s64 + 131;
	// li r5,24064
	ctx.r5.s64 = 24064;
	// rlwinm r31,r10,0,0,24
	ctx.r31.u64 = __builtin_rotateleft64(ctx.r10.u32 | (ctx.r10.u64 << 32), 0) & 0xFFFFFF80;
	// li r4,0
	ctx.r4.s64 = 0;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// stw r11,-4(r31)
	REX_STORE_U32(ctx.r31.u32 + -4, ctx.r11.u32);
	// bl 0x826d9e70
	ctx.lr = 0x823A05B4;
	sub_826D9E70(ctx, base);
	// lis r11,-31986
	ctx.r11.s64 = -2096234496;
	// li r10,1
	ctx.r10.s64 = 1;
	// stw r10,60(r31)
	REX_STORE_U32(ctx.r31.u32 + 60, ctx.r10.u32);
	// ld r11,-22672(r11)
	ctx.r11.u64 = REX_LOAD_U64(ctx.r11.u32 + -22672);
	// std r11,10880(r31)
	REX_STORE_U64(ctx.r31.u32 + 10880, ctx.r11.u64);
	// bl 0x826f0380
	ctx.lr = 0x823A05CC;
	sub_826F0380(ctx, base);
	// stw r3,10888(r31)
	REX_STORE_U32(ctx.r31.u32 + 10888, ctx.r3.u32);
	// bl 0x83063abc
	ctx.lr = 0x823A05D4;
	__imp__KeGetCurrentProcessType(ctx, base);
	// addi r11,r3,-2
	ctx.r11.s64 = ctx.r3.s64 + -2;
	// lis r4,-19072
	ctx.r4.s64 = -1249902592;
	// cntlzw r11,r11
	ctx.r11.u64 = ctx.r11.u32 == 0 ? 32 : __builtin_clz(ctx.r11.u32);
	// li r3,4800
	ctx.r3.s64 = 4800;
	// rlwinm r11,r11,27,31,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 27) & 0x1;
	// stw r11,10892(r31)
	REX_STORE_U32(ctx.r31.u32 + 10892, ctx.r11.u32);
	// bl 0x82fbf360
	ctx.lr = 0x823A05F0;
	sub_82FBF360(ctx, base);
	// stw r3,16728(r31)
	REX_STORE_U32(ctx.r31.u32 + 16728, ctx.r3.u32);
	// cmplwi r3,0
	ctx.cr0.compare<uint32_t>(ctx.r3.u32, 0, ctx.xer);
	// bne 0x823a0614
	if (!ctx.cr0.eq) goto loc_823A0614;
	// lis r4,9344
	ctx.r4.s64 = 612368384;
	// lwz r3,-4(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + -4);
	// bl 0x82fbf110
	ctx.lr = 0x823A0608;
	sub_82FBF110(ctx, base);
loc_823A0608:
	// lis r3,-32761
	ctx.r3.s64 = -2147024896;
	// ori r3,r3,14
	ctx.r3.u64 = ctx.r3.u64 | 14;
	// b 0x823a0660
	goto loc_823A0660;
loc_823A0614:
	// cmpwi cr6,r29,2
	ctx.cr6.compare<int32_t>(ctx.r29.s32, 2, ctx.xer);
	// bne cr6,0x823a0668
	if (!ctx.cr6.eq) goto loc_823A0668;
	// lbz r11,10940(r31)
	ctx.r11.u64 = REX_LOAD_U8(ctx.r31.u32 + 10940);
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// ori r11,r11,128
	ctx.r11.u64 = ctx.r11.u64 | 128;
	// stb r11,10940(r31)
	REX_STORE_U8(ctx.r31.u32 + 10940, ctx.r11.u8);
	// bl 0x823b2278
	ctx.lr = 0x823A0630;
	sub_823B2278(ctx, base);
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b2278
	ctx.lr = 0x823A0638;
	sub_823B2278(ctx, base);
	// li r11,-1
	ctx.r11.s64 = -1;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// stw r11,21560(r31)
	REX_STORE_U32(ctx.r31.u32 + 21560, ctx.r11.u32);
	// stw r11,21564(r31)
	REX_STORE_U32(ctx.r31.u32 + 21564, ctx.r11.u32);
	// stw r11,14936(r31)
	REX_STORE_U32(ctx.r31.u32 + 14936, ctx.r11.u32);
	// bl 0x823b9440
	ctx.lr = 0x823A0650;
	sub_823B9440(ctx, base);
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b96d0
	ctx.lr = 0x823A0658;
	sub_823B96D0(ctx, base);
loc_823A0658:
	// stw r31,0(r27)
	REX_STORE_U32(ctx.r27.u32 + 0, ctx.r31.u32);
	// li r3,0
	ctx.r3.s64 = 0;
loc_823A0660:
	// addi r1,r1,128
	ctx.r1.s64 = ctx.r1.s64 + 128;
	// b 0x826d9914
	__restgprlr_27(ctx, base);
	return;
loc_823A0668:
	// rlwinm. r11,r30,0,23,23
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r30.u32 | (ctx.r30.u64 << 32), 0) & 0x100;
	ctx.cr0.compare<int32_t>(ctx.r11.s32, 0, ctx.xer);
	// bne 0x823a067c
	if (!ctx.cr0.eq) goto loc_823A067C;
	// rlwinm. r11,r30,0,2,7
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r30.u32 | (ctx.r30.u64 << 32), 0) & 0x3F000000;
	ctx.cr0.compare<int32_t>(ctx.r11.s32, 0, ctx.xer);
	// bne 0x823a067c
	if (!ctx.cr0.eq) goto loc_823A067C;
	// oris r30,r30,3072
	ctx.r30.u64 = ctx.r30.u64 | 201326592;
loc_823A067C:
	// stw r30,23980(r31)
	REX_STORE_U32(ctx.r31.u32 + 23980, ctx.r30.u32);
	// mr r4,r28
	ctx.r4.u64 = ctx.r28.u64;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b9da0
	ctx.lr = 0x823A068C;
	sub_823B9DA0(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// bne 0x823a0658
	if (!ctx.cr0.eq) goto loc_823A0658;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823a06b8
	ctx.lr = 0x823A069C;
	sub_823A06B8(ctx, base);
	// b 0x823a0608
	goto loc_823A0608;
}

```
### sub_823B9DA0 — callback registration and ring setup caller

Source: generated/default/nfs_shift_recomp.196.cpp, lines 4932–5292 inclusive.

```cpp
DEFINE_REX_FUNC(sub_823B9DA0) {
	REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	uint32_t ea{};
	// mflr r12
	ctx.r12.u64 = ctx.lr;
	// bl 0x826d98cc
	ctx.lr = 0x823B9DA8;
	__savegprlr_29(ctx, base);
	// stwu r1,-128(r1)
	ea = -128 + ctx.r1.u32;
	REX_STORE_U32(ea, ctx.r1.u32);
	ctx.r1.u32 = ea;
	// mr r31,r3
	ctx.r31.u64 = ctx.r3.u64;
	// addi r3,r3,14944
	ctx.r3.s64 = ctx.r3.s64 + 14944;
	// mr r30,r4
	ctx.r30.u64 = ctx.r4.u64;
	// bl 0x830634dc
	ctx.lr = 0x823B9DBC;
	__imp__RtlInitializeCriticalSection(ctx, base);
	// addi r3,r31,14972
	ctx.r3.s64 = ctx.r31.s64 + 14972;
	// bl 0x830634dc
	ctx.lr = 0x823B9DC4;
	__imp__RtlInitializeCriticalSection(ctx, base);
	// lis r11,-32241
	ctx.r11.s64 = -2112946176;
	// lis r10,-32241
	ctx.r10.s64 = -2112946176;
	// addi r7,r11,-20136
	ctx.r7.s64 = ctx.r11.s64 + -20136;
	// lis r9,-32196
	ctx.r9.s64 = -2109997056;
	// addi r6,r10,-21288
	ctx.r6.s64 = ctx.r10.s64 + -21288;
	// li r5,0
	ctx.r5.s64 = 0;
	// addi r4,r9,-25352
	ctx.r4.s64 = ctx.r9.s64 + -25352;
	// lis r3,8276
	ctx.r3.s64 = 542375936;
	// lbz r11,10942(r31)
	ctx.r11.u64 = REX_LOAD_U8(ctx.r31.u32 + 10942);
	// ori r11,r11,4
	ctx.r11.u64 = ctx.r11.u64 | 4;
	// stb r11,10942(r31)
	REX_STORE_U8(ctx.r31.u32 + 10942, ctx.r11.u8);
	// bl 0x83063dcc
	ctx.lr = 0x823B9DF4;
	__imp__VdInitializeEngines(ctx, base);
	// bl 0x83063abc
	ctx.lr = 0x823B9DF8;
	__imp__KeGetCurrentProcessType(ctx, base);
	// cmpwi cr6,r3,2
	ctx.cr6.compare<int32_t>(ctx.r3.s32, 2, ctx.xer);
	// beq cr6,0x823b9e20
	if (ctx.cr6.eq) goto loc_823B9E20;
	// lis r11,-31987
	ctx.r11.s64 = -2096300032;
	// li r4,1
	ctx.r4.s64 = 1;
	// addi r3,r11,20248
	ctx.r3.s64 = ctx.r11.s64 + 20248;
	// bl 0x83063a5c
	ctx.lr = 0x823B9E10;
	__imp__ExRegisterTitleTerminateNotification(ctx, base);
	// lis r11,-31987
	ctx.r11.s64 = -2096300032;
	// li r4,1
	ctx.r4.s64 = 1;
	// addi r3,r11,20264
	ctx.r3.s64 = ctx.r11.s64 + 20264;
	// bl 0x83063a5c
	ctx.lr = 0x823B9E20;
	__imp__ExRegisterTitleTerminateNotification(ctx, base);
loc_823B9E20:
	// li r29,0
	ctx.r29.s64 = 0;
	// lis r11,-32197
	ctx.r11.s64 = -2110062592;
	// stw r29,16712(r31)
	REX_STORE_U32(ctx.r31.u32 + 16712, ctx.r29.u32);
	// mr r4,r31
	ctx.r4.u64 = ctx.r31.u64;
	// addi r3,r11,14264
	ctx.r3.s64 = ctx.r11.s64 + 14264;
	// bl 0x83063dbc
	ctx.lr = 0x823B9E38;
	__imp__VdSetGraphicsInterruptCallback(ctx, base);
	// bl 0x83063abc
	ctx.lr = 0x823B9E3C;
	__imp__KeGetCurrentProcessType(ctx, base);
	// cmpwi cr6,r3,2
	ctx.cr6.compare<int32_t>(ctx.r3.s32, 2, ctx.xer);
	// beq cr6,0x823b9e50
	if (ctx.cr6.eq) goto loc_823B9E50;
	// lis r11,-32256
	ctx.r11.s64 = -2113929216;
	// lwz r11,1708(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 1708);
	// b 0x823b9e58
	goto loc_823B9E58;
loc_823B9E50:
	// lis r11,-32256
	ctx.r11.s64 = -2113929216;
	// lwz r11,1712(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 1712);
loc_823B9E58:
	// stw r31,0(r11)
	REX_STORE_U32(ctx.r11.u32 + 0, ctx.r31.u32);
	// addi r7,r1,80
	ctx.r7.s64 = ctx.r1.s64 + 80;
	// sth r29,80(r1)
	REX_STORE_U16(ctx.r1.u32 + 80, ctx.r29.u16);
	// li r6,4
	ctx.r6.s64 = 4;
	// addi r5,r31,16716
	ctx.r5.s64 = ctx.r31.s64 + 16716;
	// li r4,10
	ctx.r4.s64 = 10;
	// li r3,3
	ctx.r3.s64 = 3;
	// bl 0x830636bc
	ctx.lr = 0x823B9E78;
	__imp__ExGetXConfigSetting(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// bge 0x823b9e88
	if (!ctx.cr0.lt) goto loc_823B9E88;
loc_823B9E80:
	// li r3,0
	ctx.r3.s64 = 0;
	// b 0x823ba000
	goto loc_823BA000;
loc_823B9E88:
	// addi r4,r30,72
	ctx.r4.s64 = ctx.r30.s64 + 72;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b3a48
	ctx.lr = 0x823B9E94;
	sub_823B3A48(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// bne 0x823b9e80
	if (!ctx.cr0.eq) goto loc_823B9E80;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823a03e8
	ctx.lr = 0x823B9EA4;
	sub_823A03E8(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// beq 0x823b9e80
	if (ctx.cr0.eq) goto loc_823B9E80;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b90f0
	ctx.lr = 0x823B9EB4;
	sub_823B90F0(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// beq 0x823b9e80
	if (ctx.cr0.eq) goto loc_823B9E80;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823a8970
	ctx.lr = 0x823B9EC4;
	sub_823A8970(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// beq 0x823b9e80
	if (ctx.cr0.eq) goto loc_823B9E80;
	// li r11,-1
	ctx.r11.s64 = -1;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// stw r11,21560(r31)
	REX_STORE_U32(ctx.r31.u32 + 21560, ctx.r11.u32);
	// stw r11,21564(r31)
	REX_STORE_U32(ctx.r31.u32 + 21564, ctx.r11.u32);
	// bl 0x823b9440
	ctx.lr = 0x823B9EE0;
	sub_823B9440(ctx, base);
	// mr r4,r30
	ctx.r4.u64 = ctx.r30.u64;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b9940
	ctx.lr = 0x823B9EEC;
	sub_823B9940(ctx, base);
	// cmpwi r3,0
	ctx.cr0.compare<int32_t>(ctx.r3.s32, 0, ctx.xer);
	// beq 0x823b9e80
	if (ctx.cr0.eq) goto loc_823B9E80;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b96d0
	ctx.lr = 0x823B9EFC;
	sub_823B96D0(ctx, base);
	// lis r4,-20096
	ctx.r4.s64 = -1317011456;
	// li r3,0
	ctx.r3.s64 = 0;
	// bl 0x82fbf110
	ctx.lr = 0x823B9F08;
	sub_82FBF110(ctx, base);
	// lis r11,-32256
	ctx.r11.s64 = -2113929216;
	// lwz r11,1956(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 1956);
	// lwz r11,0(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 0);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beq cr6,0x823b9f24
	if (ctx.cr6.eq) goto loc_823B9F24;
	// lwz r11,32(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 32);
	// b 0x823b9f28
	goto loc_823B9F28;
loc_823B9F24:
	// mr r11,r29
	ctx.r11.u64 = ctx.r29.u64;
loc_823B9F28:
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beq cr6,0x823b9f5c
	if (ctx.cr6.eq) goto loc_823B9F5C;
	// lwz r10,0(r11)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r11.u32 + 0);
	// cmplwi cr6,r10,8
	ctx.cr6.compare<uint32_t>(ctx.r10.u32, 8, ctx.xer);
	// ble cr6,0x823b9f4c
	if (!ctx.cr6.gt) goto loc_823B9F4C;
	// addi r10,r31,16720
	ctx.r10.s64 = ctx.r31.s64 + 16720;
	// addi r9,r31,16724
	ctx.r9.s64 = ctx.r31.s64 + 16724;
	// stw r10,4(r11)
	REX_STORE_U32(ctx.r11.u32 + 4, ctx.r10.u32);
	// stw r9,8(r11)
	REX_STORE_U32(ctx.r11.u32 + 8, ctx.r9.u32);
loc_823B9F4C:
	// addi r10,r31,16560
	ctx.r10.s64 = ctx.r31.s64 + 16560;
	// addi r9,r31,21576
	ctx.r9.s64 = ctx.r31.s64 + 21576;
	// stw r10,24(r11)
	REX_STORE_U32(ctx.r11.u32 + 24, ctx.r10.u32);
	// stw r9,28(r11)
	REX_STORE_U32(ctx.r11.u32 + 28, ctx.r9.u32);
loc_823B9F5C:
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b33a0
	ctx.lr = 0x823B9F64;
	sub_823B33A0(ctx, base);
	// addi r3,r1,88
	ctx.r3.s64 = ctx.r1.s64 + 88;
	// bl 0x826f0390
	ctx.lr = 0x823B9F6C;
	sub_826F0390(ctx, base);
	// lfd f13,88(r1)
	ctx.fpscr.disableFlushMode();
	ctx.f13.u64 = REX_LOAD_U64(ctx.r1.u32 + 88);
	// fcfid f13,f13
	ctx.f13.f64 = double(ctx.f13.s64);
	// lis r11,-32240
	ctx.r11.s64 = -2112880640;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// addi r11,r11,-560
	ctx.r11.s64 = ctx.r11.s64 + -560;
	// lfs f0,12(r11)
	temp.u32 = REX_LOAD_U32(ctx.r11.u32 + 12);
	ctx.f0.f64 = double(temp.f32);
	// frsp f13,f13
	ctx.f13.f64 = double(float(ctx.f13.f64));
	// stfs f13,21588(r31)
	temp.f32 = float(ctx.f13.f64);
	REX_STORE_U32(ctx.r31.u32 + 21588, temp.u32);
	// fdivs f0,f0,f13
	ctx.f0.f64 = double(float(ctx.f0.f64 / ctx.f13.f64));
	// stfs f0,21592(r31)
	temp.f32 = float(ctx.f0.f64);
	REX_STORE_U32(ctx.r31.u32 + 21592, temp.u32);
	// bl 0x823c1b30
	ctx.lr = 0x823B9F98;
	sub_823C1B30(ctx, base);
	// li r5,1
	ctx.r5.s64 = 1;
	// li r4,1
	ctx.r4.s64 = 1;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823c2188
	ctx.lr = 0x823B9FA8;
	sub_823C2188(ctx, base);
	// li r4,0
	ctx.r4.s64 = 0;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823a0998
	ctx.lr = 0x823B9FB4;
	sub_823A0998(ctx, base);
	// lis r30,-31973
	ctx.r30.s64 = -2095382528;
	// lwz r11,14368(r30)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r30.u32 + 14368);
	// cmpwi cr6,r11,0
	ctx.cr6.compare<int32_t>(ctx.r11.s32, 0, ctx.xer);
	// bne cr6,0x823b9fd4
	if (!ctx.cr6.eq) goto loc_823B9FD4;
	// bl 0x83063ddc
	ctx.lr = 0x823B9FC8;
	__imp__VdIsHSIOTrainingSucceeded(ctx, base);
	// cntlzw r11,r3
	ctx.r11.u64 = ctx.r3.u32 == 0 ? 32 : __builtin_clz(ctx.r3.u32);
	// rlwinm r11,r11,27,31,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 27) & 0x1;
	// stw r11,14368(r30)
	REX_STORE_U32(ctx.r30.u32 + 14368, ctx.r11.u32);
loc_823B9FD4:
	// bl 0x83063abc
	ctx.lr = 0x823B9FD8;
	__imp__KeGetCurrentProcessType(ctx, base);
	// cmpwi cr6,r3,2
	ctx.cr6.compare<int32_t>(ctx.r3.s32, 2, ctx.xer);
	// beq cr6,0x823b9ffc
	if (ctx.cr6.eq) goto loc_823B9FFC;
	// li r11,41
	ctx.r11.s64 = 41;
	// addi r10,r31,23380
	ctx.r10.s64 = ctx.r31.s64 + 23380;
	// li r9,-1
	ctx.r9.s64 = -1;
	// addi r10,r10,-4
	ctx.r10.s64 = ctx.r10.s64 + -4;
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
loc_823B9FF4:
	// stwu r9,4(r10)
	ea = 4 + ctx.r10.u32;
	REX_STORE_U32(ea, ctx.r9.u32);
	ctx.r10.u32 = ea;
	// bdnz 0x823b9ff4
	--ctx.ctr.u64;
	if (ctx.ctr.u32 != 0) goto loc_823B9FF4;
loc_823B9FFC:
	// li r3,1
	ctx.r3.s64 = 1;
loc_823BA000:
	// addi r1,r1,128
	ctx.r1.s64 = ctx.r1.s64 + 128;
	// b 0x826d991c
	__restgprlr_29(ctx, base);
	return;
}

```
### sub_823B3A48 — ring-buffer resource setup

Source: generated/default/nfs_shift_recomp.74.cpp, lines 4871–5522 inclusive.

```cpp
DEFINE_REX_FUNC(sub_823B3A48) {
	REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	uint32_t ea{};
	// mflr r12
	ctx.r12.u64 = ctx.lr;
	// bl 0x826d98b4
	ctx.lr = 0x823B3A50;
	__savegprlr_23(ctx, base);
	// stwu r1,-320(r1)
	ea = -320 + ctx.r1.u32;
	REX_STORE_U32(ea, ctx.r1.u32);
	ctx.r1.u32 = ea;
	// lwz r11,10908(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 10908);
	// mr r31,r3
	ctx.r31.u64 = ctx.r3.u64;
	// mr r26,r4
	ctx.r26.u64 = ctx.r4.u64;
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beq cr6,0x823b3a94
	if (ctx.cr6.eq) goto loc_823B3A94;
	// lwz r11,48(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beq cr6,0x823b3a94
	if (ctx.cr6.eq) goto loc_823B3A94;
	// bl 0x823b3850
	ctx.lr = 0x823B3A78;
	sub_823B3850(ctx, base);
	// b 0x823b3a84
	goto loc_823B3A84;
loc_823B3A7C:
	// li r3,1
	ctx.r3.s64 = 1;
	// bl 0x826f00e0
	ctx.lr = 0x823B3A84;
	sub_826F00E0(ctx, base);
loc_823B3A84:
	// lwz r10,10988(r31)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r31.u32 + 10988);
	// lwz r11,10992(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10992);
	// cmpw cr6,r11,r10
	ctx.cr6.compare<int32_t>(ctx.r11.s32, ctx.r10.s32, ctx.xer);
	// bne cr6,0x823b3a7c
	if (!ctx.cr6.eq) goto loc_823B3A7C;
loc_823B3A94:
	// lwz r11,14904(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 14904);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beq cr6,0x823b3adc
	if (ctx.cr6.eq) goto loc_823B3ADC;
	// lwz r8,14908(r31)
	ctx.r8.u64 = REX_LOAD_U32(ctx.r31.u32 + 14908);
	// rlwinm r10,r11,12,20,31
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 12) & 0xFFF;
	// clrlwi r9,r11,3
	ctx.r9.u64 = ctx.r11.u32 & 0x1FFFFFFF;
	// rlwinm r11,r8,12,20,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r8.u32 | (ctx.r8.u64 << 32), 12) & 0xFFF;
	// addi r7,r10,512
	ctx.r7.s64 = ctx.r10.s64 + 512;
	// addi r10,r11,512
	ctx.r10.s64 = ctx.r11.s64 + 512;
	// clrlwi r11,r8,3
	ctx.r11.u64 = ctx.r8.u32 & 0x1FFFFFFF;
	// rlwinm r10,r10,0,19,19
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r10.u32 | (ctx.r10.u64 << 32), 0) & 0x1000;
	// rlwinm r8,r7,0,19,19
	ctx.r8.u64 = __builtin_rotateleft64(ctx.r7.u32 | (ctx.r7.u64 << 32), 0) & 0x1000;
	// add r11,r10,r11
	ctx.r11.u64 = ctx.r10.u64 + ctx.r11.u64;
	// lis r7,16384
	ctx.r7.s64 = 1073741824;
	// add r10,r8,r9
	ctx.r10.u64 = ctx.r8.u64 + ctx.r9.u64;
	// subf r4,r7,r11
	ctx.r4.u64 = ctx.r11.u64 - ctx.r7.u64;
	// subf r3,r7,r10
	ctx.r3.u64 = ctx.r10.u64 - ctx.r7.u64;
	// bl 0x823b9628
	ctx.lr = 0x823B3ADC;
	sub_823B9628(ctx, base);
loc_823B3ADC:
	// lis r4,-20096
	ctx.r4.s64 = -1317011456;
	// lwz r3,14836(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 14836);
	// bl 0x82fbf110
	ctx.lr = 0x823B3AE8;
	sub_82FBF110(ctx, base);
	// lis r4,-20096
	ctx.r4.s64 = -1317011456;
	// lwz r3,14840(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 14840);
	// bl 0x82fbf110
	ctx.lr = 0x823B3AF4;
	sub_82FBF110(ctx, base);
	// li r29,0
	ctx.r29.s64 = 0;
	// li r3,0
	ctx.r3.s64 = 0;
	// stw r29,14836(r31)
	REX_STORE_U32(ctx.r31.u32 + 14836, ctx.r29.u32);
	// stw r29,14840(r31)
	REX_STORE_U32(ctx.r31.u32 + 14840, ctx.r29.u32);
	// stw r29,48(r31)
	REX_STORE_U32(ctx.r31.u32 + 48, ctx.r29.u32);
	// stw r29,52(r31)
	REX_STORE_U32(ctx.r31.u32 + 52, ctx.r29.u32);
	// bl 0x83063cec
	ctx.lr = 0x823B3B10;
	__imp__VdSetSystemCommandBufferGpuIdentifierAddress(ctx, base);
	// lis r4,-20096
	ctx.r4.s64 = -1317011456;
	// lwz r3,10900(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 10900);
	// bl 0x82fbf110
	ctx.lr = 0x823B3B1C;
	sub_82FBF110(ctx, base);
	// lis r4,-20096
	ctx.r4.s64 = -1317011456;
	// lwz r3,10896(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// bl 0x82fbf110
	ctx.lr = 0x823B3B28;
	sub_82FBF110(ctx, base);
	// stw r29,10900(r31)
	REX_STORE_U32(ctx.r31.u32 + 10900, ctx.r29.u32);
	// cmplwi cr6,r26,0
	ctx.cr6.compare<uint32_t>(ctx.r26.u32, 0, ctx.xer);
	// stw r29,10896(r31)
	REX_STORE_U32(ctx.r31.u32 + 10896, ctx.r29.u32);
	// bne cr6,0x823b3b40
	if (!ctx.cr6.eq) goto loc_823B3B40;
	// li r3,0
	ctx.r3.s64 = 0;
	// b 0x823b3ea8
	goto loc_823B3EA8;
loc_823B3B40:
	// lwz r25,4(r26)
	ctx.r25.u64 = REX_LOAD_U32(ctx.r26.u32 + 4);
	// lwz r27,8(r26)
	ctx.r27.u64 = REX_LOAD_U32(ctx.r26.u32 + 8);
	// lwz r28,12(r26)
	ctx.r28.u64 = REX_LOAD_U32(ctx.r26.u32 + 12);
	// cmplwi cr6,r25,0
	ctx.cr6.compare<uint32_t>(ctx.r25.u32, 0, ctx.xer);
	// lwz r30,16(r26)
	ctx.r30.u64 = REX_LOAD_U32(ctx.r26.u32 + 16);
	// lwz r11,20(r26)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r26.u32 + 20);
	// bne cr6,0x823b3b64
	if (!ctx.cr6.eq) goto loc_823B3B64;
	// lis r25,0
	ctx.r25.s64 = 0;
	// ori r25,r25,32768
	ctx.r25.u64 = ctx.r25.u64 | 32768;
loc_823B3B64:
	// cmplwi cr6,r28,0
	ctx.cr6.compare<uint32_t>(ctx.r28.u32, 0, ctx.xer);
	// bne cr6,0x823b3b70
	if (!ctx.cr6.eq) goto loc_823B3B70;
	// lis r28,32
	ctx.r28.s64 = 2097152;
loc_823B3B70:
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// bne cr6,0x823b3b7c
	if (!ctx.cr6.eq) goto loc_823B3B7C;
	// li r11,32
	ctx.r11.s64 = 32;
loc_823B3B7C:
	// divwu r26,r28,r11
	ctx.r26.u64 = uint32_t(ctx.r11.u32 ? ctx.r28.u32 / ctx.r11.u32 : 0);
	// twllei r11,0
	if (ctx.r11.s32 == 0 || ctx.r11.u32 < 0u) ppc_trap(ctx, base, 0);
	// cmplwi cr6,r27,0
	ctx.cr6.compare<uint32_t>(ctx.r27.u32, 0, ctx.xer);
	// bne cr6,0x823b3ba0
	if (!ctx.cr6.eq) goto loc_823B3BA0;
	// lis r4,-19072
	ctx.r4.s64 = -1249902592;
	// mr r3,r25
	ctx.r3.u64 = ctx.r25.u64;
	// bl 0x82fbf360
	ctx.lr = 0x823B3B98;
	sub_82FBF360(ctx, base);
	// mr r27,r3
	ctx.r27.u64 = ctx.r3.u64;
	// stw r3,14836(r31)
	REX_STORE_U32(ctx.r31.u32 + 14836, ctx.r3.u32);
loc_823B3BA0:
	// li r24,3
	ctx.r24.s64 = 3;
	// cmplwi cr6,r30,0
	ctx.cr6.compare<uint32_t>(ctx.r30.u32, 0, ctx.xer);
	// bne cr6,0x823b3bd4
	if (!ctx.cr6.eq) goto loc_823B3BD4;
	// lis r11,8
	ctx.r11.s64 = 524288;
	// lis r4,-30848
	ctx.r4.s64 = -2021654528;
	// subfc r11,r11,r28
	ctx.xer.ca = ctx.r28.u32 >= ctx.r11.u32;
	ctx.r11.u64 = ctx.r28.u64 - ctx.r11.u64;
	// mr r3,r28
	ctx.r3.u64 = ctx.r28.u64;
	// subfe r11,r11,r11
	temp.u8 = (~ctx.r11.u32 + ctx.r11.u32 < ~ctx.r11.u32) | (~ctx.r11.u32 + ctx.r11.u32 + ctx.xer.ca < ctx.xer.ca);
	ctx.r11.u64 = ~ctx.r11.u64 + ctx.r11.u64 + ctx.xer.ca;
	ctx.xer.ca = temp.u8;
	// and r11,r11,r24
	ctx.r11.u64 = ctx.r11.u64 & ctx.r24.u64;
	// rlwimi r4,r11,28,1,3
	ctx.r4.u64 = (__builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 28) & 0x70000000) | (ctx.r4.u64 & 0xFFFFFFFF8FFFFFFF);
	// bl 0x82fbf360
	ctx.lr = 0x823B3BCC;
	sub_82FBF360(ctx, base);
	// mr r30,r3
	ctx.r30.u64 = ctx.r3.u64;
	// stw r3,14840(r31)
	REX_STORE_U32(ctx.r31.u32 + 14840, ctx.r3.u32);
loc_823B3BD4:
	// cmplwi cr6,r27,0
	ctx.cr6.compare<uint32_t>(ctx.r27.u32, 0, ctx.xer);
	// beq cr6,0x823b3ea0
	if (ctx.cr6.eq) goto loc_823B3EA0;
	// cmplwi cr6,r30,0
	ctx.cr6.compare<uint32_t>(ctx.r30.u32, 0, ctx.xer);
	// beq cr6,0x823b3ea0
	if (ctx.cr6.eq) goto loc_823B3EA0;
	// lis r4,-23168
	ctx.r4.s64 = -1518338048;
	// li r3,96
	ctx.r3.s64 = 96;
	// bl 0x82fbf360
	ctx.lr = 0x823B3BF0;
	sub_82FBF360(ctx, base);
	// stw r3,10896(r31)
	REX_STORE_U32(ctx.r31.u32 + 10896, ctx.r3.u32);
	// cmplwi r3,0
	ctx.cr0.compare<uint32_t>(ctx.r3.u32, 0, ctx.xer);
	// beq 0x823b3ea0
	if (ctx.cr0.eq) goto loc_823B3EA0;
	// lis r4,-27264
	ctx.r4.s64 = -1786773504;
	// li r3,32
	ctx.r3.s64 = 32;
	// bl 0x82fbf360
	ctx.lr = 0x823B3C08;
	sub_82FBF360(ctx, base);
	// stw r3,10900(r31)
	REX_STORE_U32(ctx.r31.u32 + 10900, ctx.r3.u32);
	// cmplwi r3,0
	ctx.cr0.compare<uint32_t>(ctx.r3.u32, 0, ctx.xer);
	// beq 0x823b3ea0
	if (ctx.cr0.eq) goto loc_823B3EA0;
	// li r5,96
	ctx.r5.s64 = 96;
	// lwz r3,10896(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// li r4,0
	ctx.r4.s64 = 0;
	// bl 0x826d9e70
	ctx.lr = 0x823B3C24;
	sub_826D9E70(ctx, base);
	// li r5,32
	ctx.r5.s64 = 32;
	// li r4,0
	ctx.r4.s64 = 0;
	// lwz r3,10900(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 10900);
	// bl 0x826d9e70
	ctx.lr = 0x823B3C34;
	sub_826D9E70(ctx, base);
	// cntlzw r11,r25
	ctx.r11.u64 = ctx.r25.u32 == 0 ? 32 : __builtin_clz(ctx.r25.u32);
	// mr r3,r27
	ctx.r3.u64 = ctx.r27.u64;
	// subfic r23,r11,28
	ctx.xer.ca = ctx.r11.u32 <= 28;
	ctx.r23.u64 = static_cast<uint64_t>(28) - ctx.r11.u64;
	// bl 0x83063d0c
	ctx.lr = 0x823B3C44;
	__imp__MmGetPhysicalAddress(ctx, base);
	// mr r4,r23
	ctx.r4.u64 = ctx.r23.u64;
	// bl 0x83063d3c
	ctx.lr = 0x823B3C4C;
	__imp__VdInitializeRingBuffer(ctx, base);
	// rlwinm r11,r25,23,9,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r25.u32 | (ctx.r25.u64 << 32), 23) & 0x7FFFFF;
	// cntlzw r11,r11
	ctx.r11.u64 = ctx.r11.u32 == 0 ? 32 : __builtin_clz(ctx.r11.u32);
	// subfic r4,r11,31
	ctx.xer.ca = ctx.r11.u32 <= 31;
	ctx.r4.u64 = static_cast<uint64_t>(31) - ctx.r11.u64;
	// cmplwi cr6,r4,19
	ctx.cr6.compare<uint32_t>(ctx.r4.u32, 19, ctx.xer);
	// ble cr6,0x823b3c64
	if (!ctx.cr6.gt) goto loc_823B3C64;
	// li r4,19
	ctx.r4.s64 = 19;
loc_823B3C64:
	// lwz r11,10896(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// addi r11,r11,60
	ctx.r11.s64 = ctx.r11.s64 + 60;
	// rlwinm r10,r11,12,20,31
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 12) & 0xFFF;
	// clrlwi r11,r11,3
	ctx.r11.u64 = ctx.r11.u32 & 0x1FFFFFFF;
	// addi r10,r10,512
	ctx.r10.s64 = ctx.r10.s64 + 512;
	// rlwinm r10,r10,0,19,19
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r10.u32 | (ctx.r10.u64 << 32), 0) & 0x1000;
	// add r3,r10,r11
	ctx.r3.u64 = ctx.r10.u64 + ctx.r11.u64;
	// bl 0x83063d2c
	ctx.lr = 0x823B3C84;
	__imp__VdEnableRingBufferRPtrWriteBack(ctx, base);
	// rlwinm r11,r28,0,0,29
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r28.u32 | (ctx.r28.u64 << 32), 0) & 0xFFFFFFFC;
	// lis r9,2989
	ctx.r9.s64 = 195887104;
	// add r11,r11,r30
	ctx.r11.u64 = ctx.r11.u64 + ctx.r30.u64;
	// ori r7,r9,61453
	ctx.r7.u64 = ctx.r9.u64 | 61453;
	// rlwinm r8,r25,30,2,31
	ctx.r8.u64 = __builtin_rotateleft64(ctx.r25.u32 | (ctx.r25.u64 << 32), 30) & 0x3FFFFFFF;
	// rlwinm r10,r26,0,0,29
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r26.u32 | (ctx.r26.u64 << 32), 0) & 0xFFFFFFFC;
	// addi r9,r11,-4
	ctx.r9.s64 = ctx.r11.s64 + -4;
	// stw r7,-4(r11)
	REX_STORE_U32(ctx.r11.u32 + -4, ctx.r7.u32);
	// rlwinm r11,r28,30,2,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r28.u32 | (ctx.r28.u64 << 32), 30) & 0x3FFFFFFF;
	// add r10,r10,r30
	ctx.r10.u64 = ctx.r10.u64 + ctx.r30.u64;
	// stw r9,14908(r31)
	REX_STORE_U32(ctx.r31.u32 + 14908, ctx.r9.u32);
	// addi r8,r8,-1
	ctx.r8.s64 = ctx.r8.s64 + -1;
	// stw r11,14936(r31)
	REX_STORE_U32(ctx.r31.u32 + 14936, ctx.r11.u32);
	// stw r27,14896(r31)
	REX_STORE_U32(ctx.r31.u32 + 14896, ctx.r27.u32);
	// addi r9,r30,-4
	ctx.r9.s64 = ctx.r30.s64 + -4;
	// stw r30,14904(r31)
	REX_STORE_U32(ctx.r31.u32 + 14904, ctx.r30.u32);
	// addi r7,r10,-160
	ctx.r7.s64 = ctx.r10.s64 + -160;
	// stw r30,14924(r31)
	REX_STORE_U32(ctx.r31.u32 + 14924, ctx.r30.u32);
	// stw r30,14928(r31)
	REX_STORE_U32(ctx.r31.u32 + 14928, ctx.r30.u32);
	// stw r26,14912(r31)
	REX_STORE_U32(ctx.r31.u32 + 14912, ctx.r26.u32);
	// stw r8,14900(r31)
	REX_STORE_U32(ctx.r31.u32 + 14900, ctx.r8.u32);
	// lwz r11,10896(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// stw r29,60(r11)
	REX_STORE_U32(ctx.r11.u32 + 60, ctx.r29.u32);
	// lwz r11,10908(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10908);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// stw r29,10956(r31)
	REX_STORE_U32(ctx.r31.u32 + 10956, ctx.r29.u32);
	// stw r9,48(r31)
	REX_STORE_U32(ctx.r31.u32 + 48, ctx.r9.u32);
	// stw r10,52(r31)
	REX_STORE_U32(ctx.r31.u32 + 52, ctx.r10.u32);
	// stw r7,56(r31)
	REX_STORE_U32(ctx.r31.u32 + 56, ctx.r7.u32);
	// stw r29,14916(r31)
	REX_STORE_U32(ctx.r31.u32 + 14916, ctx.r29.u32);
	// bne cr6,0x823b3d04
	if (!ctx.cr6.eq) goto loc_823B3D04;
	// stw r24,10908(r31)
	REX_STORE_U32(ctx.r31.u32 + 10908, ctx.r24.u32);
loc_823B3D04:
	// lwz r11,10908(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10908);
	// lwz r10,10896(r31)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// addi r11,r11,-2
	ctx.r11.s64 = ctx.r11.s64 + -2;
	// stw r11,0(r10)
	REX_STORE_U32(ctx.r10.u32 + 0, ctx.r11.u32);
	// lwz r11,48(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 48);
	// lwz r10,10896(r31)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// lwz r9,14920(r31)
	ctx.r9.u64 = REX_LOAD_U32(ctx.r31.u32 + 14920);
	// clrlwi r9,r9,30
	ctx.r9.u64 = ctx.r9.u32 & 0x3;
	// or r11,r9,r11
	ctx.r11.u64 = ctx.r9.u64 | ctx.r11.u64;
	// stw r11,4(r10)
	REX_STORE_U32(ctx.r10.u32 + 4, ctx.r11.u32);
	// lwz r11,10896(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 10896);
	// addi r3,r11,8
	ctx.r3.s64 = ctx.r11.s64 + 8;
	// bl 0x83063cec
	ctx.lr = 0x823B3D38;
	__imp__VdSetSystemCommandBufferGpuIdentifierAddress(ctx, base);
	// li r11,8
	ctx.r11.s64 = 8;
	// lis r9,-16367
	ctx.r9.s64 = -1072627712;
	// stw r29,88(r1)
	REX_STORE_U32(ctx.r1.u32 + 88, ctx.r29.u32);
	// lis r10,-32236
	ctx.r10.s64 = -2112618496;
	// ori r8,r9,18432
	ctx.r8.u64 = ctx.r9.u64 | 18432;
	// addi r10,r10,24136
	ctx.r10.s64 = ctx.r10.s64 + 24136;
	// li r7,1023
	ctx.r7.s64 = 1023;
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// addi r9,r1,92
	ctx.r9.s64 = ctx.r1.s64 + 92;
	// stw r8,80(r1)
	REX_STORE_U32(ctx.r1.u32 + 80, ctx.r8.u32);
	// stw r7,84(r1)
	REX_STORE_U32(ctx.r1.u32 + 84, ctx.r7.u32);
	// addi r11,r10,-4
	ctx.r11.s64 = ctx.r10.s64 + -4;
	// stw r29,92(r1)
	REX_STORE_U32(ctx.r1.u32 + 92, ctx.r29.u32);
loc_823B3D6C:
	// lwzu r10,4(r11)
	ea = 4 + ctx.r11.u32;
	ctx.r10.u64 = REX_LOAD_U32(ea);
	ctx.r11.u32 = ea;
	// stwu r10,4(r9)
	ea = 4 + ctx.r9.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r9.u32 = ea;
	// bdnz 0x823b3d6c
	--ctx.ctr.u64;
	if (ctx.ctr.u32 != 0) goto loc_823B3D6C;
	// li r10,1
	ctx.r10.s64 = 1;
	// stw r29,136(r1)
	REX_STORE_U32(ctx.r1.u32 + 136, ctx.r29.u32);
	// li r11,2048
	ctx.r11.s64 = 2048;
	// stw r29,140(r1)
	REX_STORE_U32(ctx.r1.u32 + 140, ctx.r29.u32);
	// li r9,7
	ctx.r9.s64 = 7;
	// sth r10,10924(r31)
	REX_STORE_U16(ctx.r31.u32 + 10924, ctx.r10.u16);
	// sth r11,10926(r31)
	REX_STORE_U16(ctx.r31.u32 + 10926, ctx.r11.u16);
	// li r4,19
	ctx.r4.s64 = 19;
	// sth r11,130(r1)
	REX_STORE_U16(ctx.r1.u32 + 130, ctx.r11.u16);
	// addi r3,r1,80
	ctx.r3.s64 = ctx.r1.s64 + 80;
	// sth r10,128(r1)
	REX_STORE_U16(ctx.r1.u32 + 128, ctx.r10.u16);
	// stw r9,132(r1)
	REX_STORE_U32(ctx.r1.u32 + 132, ctx.r9.u32);
	// stw r29,144(r1)
	REX_STORE_U32(ctx.r1.u32 + 144, ctx.r29.u32);
	// stw r29,148(r1)
	REX_STORE_U32(ctx.r1.u32 + 148, ctx.r29.u32);
	// stw r29,152(r1)
	REX_STORE_U32(ctx.r1.u32 + 152, ctx.r29.u32);
	// bl 0x83063cfc
	ctx.lr = 0x823B3DB8;
	__imp__KiApcNormalRoutineNop(ctx, base);
	// li r5,19
	ctx.r5.s64 = 19;
	// addi r4,r1,80
	ctx.r4.s64 = ctx.r1.s64 + 80;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b29e8
	ctx.lr = 0x823B3DC8;
	sub_823B29E8(ctx, base);
	// lwz r3,48(r31)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r31.u32 + 48);
	// lwz r11,56(r31)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 56);
	// cmplw cr6,r3,r11
	ctx.cr6.compare<uint32_t>(ctx.r3.u32, ctx.r11.u32, ctx.xer);
	// ble cr6,0x823b3de0
	if (!ctx.cr6.gt) goto loc_823B3DE0;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b33a0
	ctx.lr = 0x823B3DE0;
	sub_823B33A0(ctx, base);
loc_823B3DE0:
	// li r11,3330
	ctx.r11.s64 = 3330;
	// lis r10,1
	ctx.r10.s64 = 65536;
	// stwu r11,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r11.u32);
	ctx.r3.u32 = ea;
	// lis r11,3
	ctx.r11.s64 = 196608;
	// ori r10,r10,2048
	ctx.r10.u64 = ctx.r10.u64 | 2048;
	// ori r11,r11,2562
	ctx.r11.u64 = ctx.r11.u64 | 2562;
	// lis r9,-16368
	ctx.r9.s64 = -1072693248;
	// lis r8,2032
	ctx.r8.s64 = 133169152;
	// stwu r10,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r3.u32 = ea;
	// lis r7,-16384
	ctx.r7.s64 = -1073741824;
	// lis r10,16
	ctx.r10.s64 = 1048576;
	// li r6,477
	ctx.r6.s64 = 477;
	// li r5,476
	ctx.r5.s64 = 476;
	// lis r4,2
	ctx.r4.s64 = 131072;
	// stwu r11,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r11.u32);
	ctx.r3.u32 = ea;
	// ori r4,r4,55
	ctx.r4.u64 = ctx.r4.u64 | 55;
	// stwu r9,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r9.u32);
	ctx.r3.u32 = ea;
	// stwu r8,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r8.u32);
	ctx.r3.u32 = ea;
	// stwu r7,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r7.u32);
	ctx.r3.u32 = ea;
	// stwu r10,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r3.u32 = ea;
	// stwu r6,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r6.u32);
	ctx.r3.u32 = ea;
	// lwz r10,10900(r31)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r31.u32 + 10900);
	// rlwinm r11,r10,12,20,31
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r10.u32 | (ctx.r10.u64 << 32), 12) & 0xFFF;
	// clrlwi r10,r10,3
	ctx.r10.u64 = ctx.r10.u32 & 0x1FFFFFFF;
	// addi r11,r11,512
	ctx.r11.s64 = ctx.r11.s64 + 512;
	// rlwinm r11,r11,0,19,19
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 0) & 0x1000;
	// add r11,r11,r10
	ctx.r11.u64 = ctx.r11.u64 + ctx.r10.u64;
	// stwu r11,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r11.u32);
	ctx.r3.u32 = ea;
	// stwu r5,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r5.u32);
	ctx.r3.u32 = ea;
	// stwu r4,4(r3)
	ea = 4 + ctx.r3.u32;
	REX_STORE_U32(ea, ctx.r4.u32);
	ctx.r3.u32 = ea;
	// rotlwi r11,r3,0
	ctx.r11.u64 = __builtin_rotateleft32(ctx.r3.u32, 0);
	// stw r3,48(r31)
	REX_STORE_U32(ctx.r31.u32 + 48, ctx.r3.u32);
	// lwz r10,56(r31)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r31.u32 + 56);
	// cmplw cr6,r11,r10
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, ctx.r10.u32, ctx.xer);
	// ble cr6,0x823b3e78
	if (!ctx.cr6.gt) goto loc_823B3E78;
	// mr r3,r31
	ctx.r3.u64 = ctx.r31.u64;
	// bl 0x823b33a0
	ctx.lr = 0x823B3E74;
	sub_823B33A0(ctx, base);
	// mr r11,r3
	ctx.r11.u64 = ctx.r3.u64;
loc_823B3E78:
	// li r10,1480
	ctx.r10.s64 = 1480;
	// lis r9,2
	ctx.r9.s64 = 131072;
	// stwu r10,4(r11)
	ea = 4 + ctx.r11.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r11.u32 = ea;
	// li r10,3332
	ctx.r10.s64 = 3332;
	// li r3,0
	ctx.r3.s64 = 0;
	// stwu r9,4(r11)
	ea = 4 + ctx.r11.u32;
	REX_STORE_U32(ea, ctx.r9.u32);
	ctx.r11.u32 = ea;
	// stwu r10,4(r11)
	ea = 4 + ctx.r11.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r11.u32 = ea;
	// stwu r29,4(r11)
	ea = 4 + ctx.r11.u32;
	REX_STORE_U32(ea, ctx.r29.u32);
	ctx.r11.u32 = ea;
	// stw r11,48(r31)
	REX_STORE_U32(ctx.r31.u32 + 48, ctx.r11.u32);
	// b 0x823b3ea8
	goto loc_823B3EA8;
loc_823B3EA0:
	// lis r3,-32761
	ctx.r3.s64 = -2147024896;
	// ori r3,r3,14
	ctx.r3.u64 = ctx.r3.u64 | 14;
loc_823B3EA8:
	// addi r1,r1,320
	ctx.r1.s64 = ctx.r1.s64 + 320;
	// b 0x826d9904
	__restgprlr_23(ctx, base);
	return;
}

```
