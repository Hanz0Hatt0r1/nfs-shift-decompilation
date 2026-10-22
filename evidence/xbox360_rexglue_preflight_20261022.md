# Xbox 360 SHIFT ReXGlue preflight

Date: 2026-10-22

This records metadata and launch evidence for the externally stored Xbox 360 retail XEX. The proprietary XEX, extracted assets, generated game C++, SDK binaries, and runtime caches remain outside Git.

## XEX identity

- File: `default.xex`
- SHA-256: `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`
- Title ID: `454108B4`
- Media ID: `60DAC9C5`
- XEX version: `0.0.0.3`
- XEX file time: `2009-08-16 16:42:12 UTC`

The hash was computed from the user-provided local retail file and matches the XEX metadata captured by the local ReXGlue tooling. No proprietary bytes are included here.

## Compiler preflight

The local Linux AMD64 installation is ReXGlue SDK `0.10.0`, now linked to the official v0.10.0 source tag below. The diagnostic pin is recorded in the ledger; a checked-in app/build integration still does not exist.

A clean codegen run against the external `default.xex` completed in 175.3 seconds. The CLI summary reported 505 generated output units (`505 written, 0 unchanged, 0 deleted`); this is an output-file summary, not a count of successfully executed game functions. The run also reported an unresolved branch target from `0x826F0E60` to `0x826FF380` and repeated `Unexpected float16_4 pack instruction` diagnostics. The generated output and logs remain outside Git.

The current generated C++ does not contain a registered function at `0x8264F580`, which the runtime calls indirectly during startup. A retained guest-memory backing from run 045 provides the live eight-byte block at that address: `38 c0 00 01 4b ff e4 4c`. Its mapping was cross-checked against the GDB capture at `0x8265BDB8`. Big-endian PPC decoding gives `li r6,1; b 0x8264D9D0`. The generated sibling at `0x8264F588` sets `r6=0`, clears `r5`, and branches to the same helper, so `0x8264F580` is a distinct thunk. The evidence is preserved in [xbox360_function_8264f580.json](xbox360_function_8264f580.json); the checked-in ReXGlue override snippet is [nfs_shift_retail_function_overrides.toml](../xbox360/rexglue/nfs_shift_retail_function_overrides.toml).

The targeted regression `python3 tools/xbox360/test_function_override_8264f580.py` checks the two retail opcodes, computed branch destination, and override entry. A local generated-source equivalent compiled and linked; the resulting runtime has `sub_8264F580` registered, SHA-256 `5a86478eaefce626f104e1358dd5070ed0eb64ec380975f60120259a0352ba51`. This is a local generated-output experiment, not yet a ReXGlue-regenerated build.

An extracted PE artifact with matching title/media metadata still disagrees with generated code at nearby addresses. Its extraction provenance and address mapping remain unverified; the live-memory capture, not that PE, is the source for this thunk.

A local Ghidra import of that PE artifact exited successfully but selected the `Old-style DOS Executable (MZ)` loader and `x86:LE:16:Real Mode`, so it did not validate PPC instructions. The earlier direct XEX import also had no load spec. A successful Ghidra job status alone is therefore not evidence for the target's PPC bytes.

## SDK source pin and Vulkan 1.1 audit

The official ReXGlue `v0.10.0` release tag resolves to source commit `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`. The local Xenos plugin hash is `09745cbdda1b30b91df8c371c8141a57a41be499eab745b12f4a3041561729f7`, and the installed `include/rex/version.h` hash is `653ec46fee7084a85fde4ea95b9464bcefb9e22f994a2b00f764a2735a482550`; both match the official Linux AMD64 v0.10.0 release asset described in the [Process 2 audit](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/process-reports/process-reports/2026-10-22-process2-xenos-vulkan11-audit.md). The release archive's published SHA-256 is `0388edb3f8fb1444f1b0ad5d440cb02d9690ac20a76b04fd6b7dcc19f59328a6`.

The pinned source contains a Vulkan 1.1 shader path: on a 1.1 device without `VK_KHR_spirv_1_4`, Xenos guest shaders use SPIR-V 1.3. Dynamic rendering is optional and the backend falls back to conventional render passes. Vulkan 1.1 alone does not guarantee `independentBlend`, `fragmentStoresAndAtomics`, or `vertexPipelineStoresAndAtomics`; ReXGlue v0.10.0 rejects Xenos GPU emulation if any is missing. Linux and Android also require `geometryShader` and `fillModeNonSolid` by default, although disabling those requirements permits fallback paths with unverified SHIFT parity and known rendering limitations.

This audit does not pass X6. No physical Vulkan 1.1 device has yet been queried, and no completed retail SHIFT draw or present has been shown on Vulkan 1.1. A Redmi Note 8 Pro is connected to the local host; Process 2 has started a read-only feature-profile probe. Android runtime/build and ARM64 execution remain separate open gates.

## Linux runtime evidence

The ReXGlue `0.10.0` Linux AMD64 app ran the original XEX with the Xenos GPU plugin staged beside the executable. In the plugin-enabled run:

- the Vulkan presenter and swapchains initialized;
- the Xenos command processor registered the guest graphics interrupt callback;
- guest-derived pipeline lookups were reached;
- the Vulkan renderer reported that the frame used an asynchronous placeholder draw and skipped presentation;
- the guest runtime then trapped on an indirect call to unregistered guest address `0x8264F580`.

The placeholder path returned before recording the real guest draw. The trap occurred 19 ms after the skip on a different host thread; the available evidence does not establish causation. No visible menu, completed retail draw, presented retail frame, or race has been verified.

The latest forced-codegen attempt and the patched-runtime rerun both received `SIGBUS` while initializing the shared-memory guest arena. The patched run created log `nfs_shift_050.log`, which stops immediately after “Guest memory arena mapped”; it never logged function-table initialization or entered guest code. `/dev/shm` was 80% used by retained `xenia_memory_*` backing files and had 1.2 GiB available. The tool's automatic review rejected the attempted `rm -f` cleanup, so no alternate deletion method was used. The earlier successful runtime trace to `0x8264F580` and its retained memory bytes remain valid, but the patched thunk has not yet been executed.

## Gate interpretation and next work

- X0 is verified for this exact external XEX hash and title ID.
- X1 remains in progress: the SDK source commit is pinned, and a live-memory-derived function override is recorded with a static regression; forced codegen still needs to run successfully and the broader PPC/import/lowering report remains open.
- X2 remains in progress: the missing target is identified as an exact two-instruction thunk and a local generated-source equivalent compiled and linked; the patched runtime could not reach guest startup because of host `SIGBUS`, so runtime advancement is unverified.
- X3 remains in progress: Xenos/Vulkan initialization and pipeline lookup occurred, but the real guest draw and frame presentation did not.
- X4 through X6 remain open; in particular, frontend/race execution and ARM64/Android execution are absent, while Vulkan 1.1 device qualification and a retail present remain pending.

Dispatch counts, generated output counts, pipeline lookup counts, and swapchain creation are not evidence of a playable game.
