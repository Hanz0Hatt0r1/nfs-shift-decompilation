# Xbox 360 + ReXGlue migration plan

## Decision and scope

On 2026-10-22 the project selected the Xbox 360 retail version of Need for Speed: SHIFT as the **primary proposed** source for a native Linux / Android ARM64 port. ReXGlue SDK is the first-choice AOT compiler/runtime foundation. The older PC 1.02 P-code recompilation is preserved and moved to a research/maintenance role.

This is a **planning and repository reorganization**, not a successful XEX conversion. No local Xbox SHIFT XEX or launch trace is recorded in the new gate ledger.

## Proposed pipeline

```text
external, lawful Xbox 360 retail extraction
    -> original default.xex + version/hash lock
    -> XEX metadata, imports, PPC function/disassembly inventory
    -> pinned ReXGlue SDK PPC -> portable C++
    -> ReXGlue Xbox 360 kernel/runtime + SHIFT-specific integrations
    -> original game Xenos commands -> Vulkan backend
    -> Linux x86-64 validation
    -> Linux ARM64 validation
    -> Android ARM64 (window/input/audio/files/lifecycle)
```

Do not assume that the PC `SHIFT.exe` shares addresses, call conventions, resource variants, shader binaries or gameplay behavior with the Xbox executable. Match concepts only from observed cross-version evidence.

## Why ReXGlue, and what it does not guarantee

ReXGlue is an upstream, early-development PPC AOT project with Xbox 360 runtime infrastructure and an Xenos/Vulkan graphics backend. The SDK includes Linux x86-64/ARM64 build targets and Android-related platform interfaces; this is **not** proof that an NFS SHIFT Android executable builds, launches, renders or plays. Upstream versions may change APIs; lock a tested commit before importing headers or code.

References:
- https://github.com/rexglue/rexglue-sdk
- https://github.com/xenia-project/xenia
- https://github.com/arcanite24/pinyon-shift (precedent for a *different* Xbox 360 racing game, not SHIFT compatibility evidence)

## Implementation boundaries

| Boundary | Upstream starting point | SHIFT-specific verification needed |
| --- | --- | --- |
| PPC AOT | ReXGlue compiler/codegen | XEX coverage, indirect control flow, PPC floating/vector semantics, generated-code parity |
| Xbox OS/HLE | SDK runtime / Xenia-derived services | Imports, title storage, file formats, scheduling, threading, timing, exceptions |
| GPU | Xenos command processor and Vulkan path | Title's actual shaders, texture layouts, EDRAM/render target behavior, depth/blend, presentation |
| Assets | Existing PC importers may help conceptually | Xbox archive variants, compression, endianness, shader/resource identity |
| Hosts | Linux SDK platform layer | x86-64 initial test, ARM64 separate executable proof, Android lifecycle and input/audio |
| Vulkan | ReXGlue Vulkan backend | **Vulkan 1.1 minimum**; feature/extension audit and actual runtime check |

### Vulkan 1.1 compatibility is a release gate

The SDK can reference features introduced after 1.1 or available only as extensions. Do not assume the shader translator and GPU backend will run on a 1.1-only device merely because the project builds with Vulkan headers. Record the precise device extensions/features, their promotion level and fallback strategy. If a 1.2/1.3 dependency cannot reasonably be removed, document the cost and request an explicit project-level decision before changing the minimum.

### Migration without throwing away PC work

Preserve:
- `native_runtime/`, `native_vulkan/`, current graphics and capture code, `tools/`, `tests/`, `src/`, `evidence/`, and resource importers;
- hash/identity research, original PC draw captures and fixture regressions;
- existing PRs and generated historical playable-slice status.

No new Xbox runtime should depend on the PC Win32 shim by default. Reuse neutral library pieces (compression, geometry/data conversion, test harnesses) only after a format, ABI or behavior check. PC parity observations are reference data, not Xbox correctness proofs.

## Immediate engineering gates and artifacts

**X0 input intake:** keep an external extracted Xbox game directory, record SHA-256 for XEX and tested asset samples plus XEX build/region/title identification. Add reproducible manifest/evidence metadata only. If there is no verified `default.xex`, stop before claiming real SDK conversion.

**X1 compiler preflight:** freeze a ReXGlue commit, run its real XEX analysis/codegen path, record accepted/rejected functions or instructions, generated artifacts, unresolved PPC semantics and API/import inventory. Do not make up config layouts or addresses before inspecting the XEX.

**X2 Linux first boot:** produce a Linux x86-64 executable using that frozen version, record actual entrypoint execution and trace boundary, no synthetic substitutes or skipped exceptions.

**X3 renderer:** first *real Xbox SHIFT* GPU command and deterministic output; Vulkan validation and capability report; one synthetic SDK frame alone is not success.

**X4 gameplay:** actual frontend → controllable offline race; record input, audio, resource loading and sustained runtime outcomes.

**X5 host portability:** recompiled Linux ARM64 runtime tests followed by Android ARM64 separately, including input/storage/audio/lifecycle.

**X6 Vulkan 1.1:** successful required scene/draw coverage on a Vulkan 1.1-capable device using only supported capabilities, or an explicit evidence-backed blocker and design decision.

## Versioning, CI, review and fallback

- Track the current gate results in `coordination/xbox360_rexglue_status.json`; validator rejects unsubstantiated verified states.
- Keep the scaffold check independent of proprietary inputs. Real XEX integration CI may use local/private runners without publishing copyrighted artifacts.
- Avoid mass-closing PC PRs or moving source trees until the new Xbox compiler/bootstrap gates are independently demonstrated.
- At X1, X2 and X6, reconsider feasibility against the existing PC path if unresolved blockers dominate the budget.
- The archived original PC roadmap and README live in `docs/PC_RECOMPILATION_ROADMAP_20261022.md` and `docs/PC_RECOMPILATION_README_20261022.md`.
