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

The local Linux AMD64 installation is ReXGlue SDK `0.10.0`. Its exact upstream source commit has not been established, so this package is not yet pinned for a reproducible project build.

A clean codegen run against the external `default.xex` completed in 175.3 seconds. The CLI summary reported 505 generated output units (`505 written, 0 unchanged, 0 deleted`); this is an output-file summary, not a count of successfully executed game functions. The run also reported an unresolved branch target from `0x826F0E60` to `0x826FF380` and repeated `Unexpected float16_4 pack instruction` diagnostics. The generated output and logs remain outside Git.

The current generated C++ does not contain a registered function at `0x8264F580`, which the runtime later calls indirectly during startup. Nearby generated functions include `0x8264F588`. The exact guest bytes for the live runtime image have not yet been captured. An extracted PE artifact with matching title/media metadata disagrees with generated code at nearby addresses; its extraction provenance and address mapping are unverified, so do not use it to define an override until that discrepancy is reconciled.

A local Ghidra import of that PE artifact exited successfully but selected the `Old-style DOS Executable (MZ)` loader and `x86:LE:16:Real Mode`, so it did not validate PPC instructions. The earlier direct XEX import also had no load spec. A successful Ghidra job status alone is therefore not evidence for the target's PPC bytes.

## Linux runtime evidence

The ReXGlue `0.10.0` Linux AMD64 app ran the original XEX with the Xenos GPU plugin staged beside the executable. In the plugin-enabled run:

- the Vulkan presenter and swapchains initialized;
- the Xenos command processor registered the guest graphics interrupt callback;
- guest-derived pipeline lookups were reached;
- the Vulkan renderer reported that the frame used an asynchronous placeholder draw and skipped presentation;
- the guest runtime then trapped on an indirect call to unregistered guest address `0x8264F580`.

The placeholder path returned before recording the real guest draw. The trap occurred 19 ms after the skip on a different host thread; the available evidence does not establish causation. No visible menu, completed retail draw, presented retail frame, or race has been verified.

The latest debugger attempts did not reach guest startup: they received `SIGBUS` inside the host `Memory::InitializeFunctionTable` while writing the shared-memory guest arena. At that point `/dev/shm` was 80% used by stale `xenia_memory_*` backing files and no process held those files open. These attempts do not replace the earlier direct runtime trace to `0x8264F580`.

## Gate interpretation and next work

- X0 is verified for this exact external XEX hash and title ID.
- X1 remains in progress until the SDK source commit is pinned and the codegen output, unresolved PPC targets, imports, and lowering diagnostics are reproducibly recorded.
- X2 remains in progress: original guest code ran on Linux AMD64, but startup stops at an unresolved indirect target.
- X3 remains in progress: Xenos/Vulkan initialization and pipeline lookup occurred, but the real guest draw and frame presentation did not.
- X4 through X6 remain open; in particular, frontend/race execution, ARM64/Android execution, and Vulkan 1.1 capability proof are absent.

Dispatch counts, generated output counts, pipeline lookup counts, and swapchain creation are not evidence of a playable game.
