# Need for Speed: SHIFT — decompilation and Linux reimplementation

Evidence-driven reconstruction of *Need for Speed: SHIFT* resource formats,
runtime contracts and game systems, with an offline Linux/Vulkan runtime as the
primary execution target.

**Merged baseline: Phase 635. Current development: Phase 636.**

The repository has grown from a BFF extractor into a connected resource,
scene, renderer, physics, AI/track and native-runtime reconstruction. The
current vertical-slice goal is to move authentic Silverstone scene data and a
real vehicle from retail resources through evidence-backed IR into the Linux
runtime without inventing unresolved retail behavior.

## Principles

The project is deliberately fail-closed.

- Static/source evidence, runtime observations and renderer contracts are kept
  distinct.
- Ambiguous values remain ambiguous.
- Missing evidence becomes an explicit blocker rather than a guessed value.
- Different serialized formats may share a neutral renderer contract without
  being declared equivalent.
- Native execution requires explicit provenance gates in addition to a valid
  RenderCommand.
- Runtime-only resources and renderer-global state are never silently
  synthesized.

Typical evidence states are `proven`, `verified`, `inferred`,
`ambiguous`, `unknown`, `unsupported` and `blocked`.

## Architecture

### Resource pipeline

```text
BFF
  → extraction / decompression / hashes
  → typed analysis
  → neutral resource IR
  → scene / material / geometry / physics contracts
```

The active corpus supports SHIFT BFF Type 0/1/2 extraction and X12d=2
encryption. Type 3 remains dependent on an externally supplied
Oodle-compatible runtime.

### Render pipeline

```text
BFF
  → MEB / IMB / IMX / BMT / DDS / FX / FXO
  → DrawPacket
  → StaticDraw
  → RenderCommand
  → Vulkan artifacts
  → native executor/runtime
```

Two important render slices share this contract:

- **BMW/MEB** — the established material, shader, DDS and Vulkan regression
  slice;
- **SGB/MeshInst** — source-backed IMB binary and IMX XML geometry feed the
  same neutral renderer boundary without asserting container equivalence.

The desktop/reference renderer remains the deterministic oracle. Vulkan is the
native backend direction.

### Silverstone scene pipeline

```text
SGB
  → NODE / SUMM / PART / FLAT / OBJECT
  → scene placement
  → OBJECT resource + world transform
  → MeshInst
  → IMBNeutralGeometry / IMXNeutralGeometry
  → RenderBinding
  → runtime shader attribution
  → RuntimeProvenDraw
  → NativeSceneBundle
  → NativeSceneVulkanSet
  → NativeSceneVulkanSetPrepare
  → ordered prepared VulkanDrawBundle children
```

Key contracts near the native boundary:

- `SHIFT.IMBNeutralGeometry/1` — source-backed binary MeshInst normalization;
- `SHIFT.IMXNeutralGeometry/1` — source-backed XML MeshInst normalization;
- `SHIFT.IMBRuntimeShaderAdmission/1` — exact runtime shader selection
  admission;
- `SHIFT.RuntimeProvenDraw/1` — runtime proof preserved through
  StaticDraw/RenderCommand;
- `SHIFT.NativeSceneBundle/1` — deterministic scene manifest containing only
  runtime-proven draws;
- `SHIFT.VulkanDrawBundle/1` — neutral atomic Vulkan artifact bundle;
- `SHIFT.NativeSceneVulkanSet/1` — ordered scene-level set that re-resolves
  exact IMB/DDS resources and builds one child bundle per proven draw;
- `SHIFT.VulkanWorldTransformPacket/1` (`SVWT`) — exact native transport of
  the source-backed SGB world matrix.

Phase 581 proves the SVWT transport convention without assigning any retail
shader constant register. Phase 582 begins real material-path consumption with
translation-only execution. Phase 583 upgrades the native geometry packet to
semantic-aware SVGP v3 so POSITION 200, NORMAL 220, TANGENT 240 and TANGENT2
250 are explicit. Phase 584 uses those semantics for full non-singular affine
execution in the standalone native material path: affine POSITION transform,
inverse-transpose NORMAL and linear normalized tangent bases. Phase 585 adds
neutral per-child SPIR-V/interface/provenance preparation and an ordered
`SHIFT.NativeSceneVulkanSetPrepare/1` without relabeling scene draws as BMW.
Phases 586–587 execute that prepared neutral scene set in `native_runtime` and
prove affine SVWT execution through runtime telemetry. Phase 588 adds explicit
external `sampler2D` snapshot transport through the existing SVTP ABI while
keeping unsupplied renderer-owned resources fail-closed. Phase 589 joins those
snapshots to exact scene draw/resource/primitive/register identity before they
can satisfy a NativeSceneVulkanSet external-resource blocker. Phase 590 carries
only strong-attributed draw-local texture observations from the D3D9 capture
pipeline and converts an unambiguous captured PPM directly into that exact
Phase 589 contract. Phase 591 adds repeated-instance transform matching from
strong-attributed VS constant windows. Phase 592 reconstructs the retail `.imx`
Phase 593 adds exact six-face external `samplerCube` capture→scene→native transport at the proven s3 boundary. Phase 594 adds fail-closed reconstruction of the current MultiMatrix root from one exact runtime-observed MatrixNumber slot world matrix. Phase 595 adds a non-circular pre-admission runtime-resource→SGB candidate join. Phase 596 adds an owner-scoped (`wrapper + owner_path`) cross-resource root witness requiring at least two exact runtime resources and two distinct cumulative local chains. Phase 597 applies only ready owner roots back into the existing OBJECT handoff/MultiMatrix evaluator, producing numeric MatrixNumber worlds without inferring a world-register semantic or historical update sequence.
XML mesh grammar and admits IMX MeshInst resources to generic RenderBinding.

### Native Linux runtime

`native_runtime/` contains the offline Linux shell:

```text
prepared native IR / Vulkan bundles
  → XCB window
  → Vulkan surface + swapchain
  → indexed material draw(s)
  → fixed 60 Hz state/tick boundary
```

The runtime supports the established prepared bundle path, multi-draw material
sets, per-draw pipeline state, constant buffers, 2D textures, optional cube
resources and validation-layer coverage. Phase 599 makes the recovered six-word CameraManager snapshot and guarded two-buffer swap live inside `SHIFT.NativeRuntimeState/1`; Phase 600 seeds that scheduler from recovered camera scalar evidence. Phase 601 adds deterministic `SHIFT.NativeRuntimeInputScript/1` control snapshots that traverse the same `VehicleControlIntent` → physics-tick boundary as the live keyboard path. Phase 602 admits the source-backed participant registry/selector structural ABI into `SHIFT.NativeRuntimeState/1`; Phase 605 keeps registry and selector identity domains explicitly separate. Phase 607 adds a fail-closed runtime pointer join that can promote one concrete participant while preserving registry index and selector ordinal separately. Phases 603–604 port the source-backed builtin solve/reset kernels, Phase 606 adds an explicit prepared provider-absent solver-frame packet with Python/native oracle parity, and Phase 608 executes that exact frame on native fixed steps only when Phase 607 participant evidence and workspace cardinality gates are satisfied. Phase 609 ports the exact `FUN_007b4110` JOINT/HINGE/BAR BODY projection behind a separate proof-gated SBPS packet with Python/native oracle parity. Phase 610 joins the actual Phase 608 solver result to that projection on each fixed step only after scalar/body/constraint cardinality and solved-vector identity checks. Phases 612–615 add exact BODY export and fixed-step SBEX→SBFR gating; Phase 616 ports the deterministic front of `FUN_007bc680`; Phase 617 ports the source-backed `FUN_007bac60` JOINT three-lane projection and bounded BODY solver-vector write; Phase 618 ports both branches of the source-backed `FUN_007bae40` HINGE two-lane projection; Phase 619 ports the source-backed `FUN_007bb090` BAR weighted one-lane projection including its nonzero-side bias correction. Phase 620 ports the exact `FUN_007bbb80` JOINT self/JOINT/HINGE/BAR matrix block algebra with lower-triangle orientation/sign handling. Phase 621 ports the HINGE/HINGE self/pair block algebra from `FUN_007bb250` with the retail `FUN_007aefb0` float transform boundary. Phase 622 closes the remaining HINGE↔BAR 2x1 block algebra in that same function. Phase 623 ports the complete source-backed `FUN_007bb6c0` BAR/BAR self/pair coefficient algebra and lower-triangle addressing. Phase 624 joins the Phase 616–623 primitives over explicit prepared JOINT/HINGE/BAR arrays, producing the complete BODY-local solver vector and logical lower-triangle matrix in recovered retail order. Phase 625 maps that matrix through exact prepared BODY `+0x15c` row indices into the `+0x154` pool / `+0x158` row-pointer view, including noncanonical row order and alias/range rejection. Phase 626 joins generated contributions through `FUN_007ba570`, Phase 627 transports contribution-free prepared BODY/sample inputs as GBCF, and Phase 628 regenerates and requires exact GBCF→SBFR matrix/RHS equality on every admitted fixed step before reset/solve. Phase 629 ports the exact source-backed `FUN_007b3ed0` JOINT/HINGE/BAR refresh kernels and array order, including `FUN_007aefb0/FUN_007af0a0` float-boundary transforms and BAR normalized world-direction construction. Phase 630 adds the fail-closed CSRF relation-ownership packet and joins each source-order relation to its exact positive/negative BODY-owned GBCF samples before refresh; it also makes the retail 1 relation → 2 endpoint-samples cardinality explicit. Phase 631 admits CSRF on native fixed steps, executes `FUN_007b3ed0` before every generated BODY contribution join and keeps 4/4/20 relation counts separate from 8/8/40 endpoint samples. Phase 632 adds CRRF and independently derives `FUN_007b2210` reset rows from source-order `relation+0x70 & 1` state joined back to positive BODY-owned sample scalar bases; the normalized derived set must exactly match the prepared SBFR reset set before the unchanged reset/solve oracle may execute. Phase 633 ports the source-backed set-only writer `FUN_00757d2c`: an unordered BODY pair sets matching JOINT/HINGE bit0 state, while one BODY endpoint sets matching BAR bit0 state. Phase 634 adds the named FL/FR/RL/RR slot dispatcher: the null-spindle branch selects `wheel ↔ rear_axle`, while the present-spindle branch selects BAR relations through `spindle`, preserving the exact `0x400 + slot*0xA80` component geometry. Phase 635 extends the full retail GDB probe with a non-mutating `FUN_00757d2c` observer that records exact slot/BODY-pointer branch inputs and a shared timeline sequence against frame-entry/reset/solve/post-solve anchors. The dispatcher remains deliberately outside the fixed-step scheduler until authentic retail capture and offline timing correlation close the event-provenance gate. Phase 636 classifies every statically reachable `FUN_00757d20` caller from the captured return address: four fixed-slot setup calls in `FUN_0076ed60` and one slot-dynamic runtime-threshold call in `FUN_0079a050`. Fixed setup callers must agree with the captured slot; unknown callers remain recorded but are not call-site-ready. Authentic per-frame BODY/raw-relation state, event timing, provider dispatch and persistent vehicle-state integration remain evidence-gated.

The Linux target intentionally excludes EA services, DRM, login/profile/cloud,
matchmaking/online networking and Bink/video playback.

## Current status

| Area | State | Main open boundary |
|---|---|---|
| BFF / XMem-LZX | verified for active corpus | uncommon variants; external Type 3 codec |
| Resource IR | active / verified | remaining format-specific joins |
| MEB / vertex ABI | strong static coverage | additional same-instance proof |
| MeshInst geometry | source-backed IMB v0.4 + source-backed IMX XML | broader variants and runtime IMX same-instance proof |
| BMT / material state | source-backed subset | unresolved alpha-test/bias/stencil cases |
| FX / FXO | parser + attribution pipeline | authentic captures for tied permutations |
| Desktop renderer | active oracle | broader exact D3D9 parity |
| Vulkan | active native backend | authentic capture content/renderer-owned resource types beyond sampler2D/samplerCube-s3; remaining alpha-test/bias/stencil state |
| SGB / scene | strong structural/render handoff | authentic Silverstone capture content, streaming/LOD, production coverage of Phase 597 consensus-resolved MatrixNumber rows, and remaining historical update sequence |
| Camera | config/state/event/control + native snapshot/double-buffer handoff active | retail update timing, controller behavior and exact render/view integration |
| Native input | live X11 keyboard + deterministic fixed-step control script | gamepad/analog normalization and retail filtering semantics |
| AI / track | source-backed core | remaining linked/local runtime search behavior |
| Vehicle physics | structural reconstruction active through Phase 636: participant promotion, fixed-step solve/post-solve, native projection/matrix kernels, GBCF/CSRF refresh, generated matrix/RHS gating, relation-state-derived reset selection, source-backed bit0 mutation, named four-slot dispatch, retail mutation-event capture and exact caller classification | authentic mutation-event capture/correlation, per-frame BODY/raw-relation state, provider-present dispatch and persistent vehicle-state integration |
| Specialized providers | capture-ready | authentic runtime frame |
| BAB animation | evidence-backed grammar | remaining axis/order/trailing semantics |
| Android | deferred | waits for stable desktop/native runtime boundary |

## Silverstone evidence status

The supplied Silverstone Era3 corpus closes the current static scene dependency
surface far enough for runtime shader attribution:

- 427/427 selected IMBs decode through the v0.4 neutral geometry path;
- 428 primitive material references resolve in the track corpus;
- archive-local BMT/DDS dependencies are audited;
- all referenced global FX families resolve through the render archive;
- compiled FXO candidates are content-deduplicated;
- all 428 primitive shader contexts are structurally valid but statically
  ambiguous;
- the tied runtime search surface collapses to 51 pixel-shader byte hashes.

The executable evidence path is already implemented:

```text
runtime target set
  → raw D3D9 shader/draw prefilter
  → exact IMB resource + draw-range routing
  → same-instance binding evidence
  → unique VS/PS/pair match
  → runtime shader admission
  → exact MaterialBinding relink
  → exact scene primitive
  → RuntimeProvenDraw
```

An authentic Silverstone D3D9 capture is still required to produce real
runtime-proven shader selections. The code no longer needs to guess among tied
FXO candidates.

## BMW M3 E36 render slice

BMW remains the stable renderer regression path:

```text
VHF → MEB → BMT → FX/FXO → DrawPacket → RenderCommand → Vulkan
```

This path exercises material textures, renderer-owned external resources,
pipeline state, shader compilation/reflection, native submission gates and
multi-draw execution. Concrete tied retail FXO selection still requires an
authentic same-instance BMW body D3D9 capture.

## Vehicle physics

The main asset/runtime path is:

```text
CDF + EDF + GDF + SDF
  → VehiclePhysicsAssetGraph
  → participant admission
  → construction / provider selection
  → solver frame
  → post-solve boundary
```

The specialized-provider structure is capture-ready, including:

- 40- and 34-scalar domains;
- selector/reset lifecycle;
- row/workspace topology;
- source-derived factor/dependency/update/operator IR;
- participant creation/load and manager ingestion;
- participant registry/reselection/finalization;
- capture bundle verification and source-mutation correlation.

Exact retail numeric parity still requires an authentic provider frame. The
runtime intentionally stops before inventing unresolved force/integration
equations.

## Build and test

Python regression suite:

```bash
python -m pytest
```

Live-memory tooling tests:

```bash
make -C tools/shift_live_dump test
```

Native Linux runtime:

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
```

Native Vulkan utilities/executor:

```bash
cmake -S native_vulkan -B native_vulkan/build
cmake --build native_vulkan/build --parallel
```

Linux CI runs software Vulkan/lavapipe, shader compilation/reflection,
validation-layer checks, material rendering, multi-draw submission and the
native runtime frame loop.

## Scene pipeline commands

Decode and place an SGB scene:

```bash
python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json

python shift_importer.py sgb-placement-join \
  out/sgb-runtime.json \
  out/sgb-placement.json

python shift_importer.py sgb-scene-placement \
  out/sgb-placement.json \
  out/scene-placement.json

python shift_importer.py sgb-object-render-handoff \
  out/sgb-runtime.json \
  out/object-render-handoff.json
```

Join placement to renderable resources:

```bash
python shift_importer.py sgb-render-binding-admission \
  out/scene-placement.json \
  out/object-render-handoff.json \
  out/scene-render-admission.json

python shift_importer.py sgb-render-binding-bridge \
  out/scene-render-admission.json \
  out/ir \
  out/scene-render-binding.json \
  --runtime-shader-admission out/runtime-shader-admission.json
```

Freeze runtime-proven scene draws and resolve their Vulkan children:

```bash
python shift_importer.py native-scene-bundle \
  out/scene-render-binding.json \
  out/native-scene-bundle.json

python shift_importer.py native-scene-external-capture \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/silverstone-runtime-attribution.json \
  out/scene-external-capture.json \
  --capture-root out/capture \
  --snapshot-output out/scene-external-snapshots.json \
  --cube-snapshot-output out/scene-external-cube-snapshots.json

python shift_importer.py native-scene-vulkan-set \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan \
  --external-sampler-snapshots out/scene-external-snapshots.json \
  --external-sampler-cube-snapshots out/scene-external-cube-snapshots.json

python shift_importer.py native-scene-vulkan-prepare \
  out/native-scene-vulkan \
  --validator glslangValidator
```

Build a neutral atomic Vulkan draw:

```bash
python shift_importer.py vulkan-draw-bundle \
  out/render-command.json \
  out/neutral-mesh.json \
  out/vulkan-draw
```

Inspect/serialize a scene world transform independently:

```bash
python shift_importer.py vulkan-world-transform-packet \
  out/render-command.json \
  out/world_transform.svwt

native_vulkan/build/shift_vulkan_world_transform_check \
  out/world_transform.svwt
```

## Runtime capture

Capture is used where static evidence cannot uniquely determine runtime identity
or numerical behavior.

Examples:

```bash
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR

python tools/preflight_specialized_provider_capture.py \
  SHIFT.zip \
  out/provider-capture \
  --probe-script tools/gdb_sdf_solver_probe.py
```

The repository also contains BMW and IMB/Silverstone D3D9 shader target,
prefilter, same-instance evidence and admission tooling.

## Main blockers

These are independent; resolving one does not justify guessing another.

1. **Silverstone exact shader attribution** — authentic D3D9 capture required
   for tied IMB permutations.
2. **Renderer-owned scene evidence** — Phase 590 can automatically convert an
   unambiguous strong-attributed D3D9 `CreateTexture` + captured PPM into the
   exact Phase 589 scene contract. Phase 591 can also disambiguate repeated
   scene instances from exact strong-attributed draw-local VS constant windows;
   authentic Silverstone capture content and remaining resource types are still
   required.
3. **Scene runtime completeness** — some per-instance MatrixNumber update
   history and higher-level streaming/LOD behavior remain unresolved.
4. **Vehicle provider numeric parity** — authentic provider frame required.
5. **BMW tied FXO selection** — authentic same-instance body capture required.
6. **IMX runtime proof** — the source-backed XML neutral adapter is implemented;
   authentic IMX same-instance shader/resource evidence is not yet established.

## Repository map

| Path | Purpose |
|---|---|
| `shift_importer.py` | primary importer/analysis/orchestration CLI |
| `src/formats/` | resource/material/geometry/collision parsers |
| `src/render/` | neutral render contracts and reference renderer |
| `src/render/vulkan/` | Vulkan packet/bundle preparation |
| `src/scene/` | SGB, MeshInst, IMB and native-scene contracts |
| `src/bmw/` | BMW retail material/shader/capture regression path |
| `src/track/` | track metadata and runtime query contracts |
| `native_vulkan/` | native Vulkan probes/material executor |
| `native_runtime/` | offline Linux XCB/Vulkan runtime |
| `native_capture/` | D3D9 capture producer |
| `tools/` | capture, audit, trace and evidence utilities |
| `tests/` | regression suite |
| `docs/status/` | current subsystem status |
| `docs/PHASE*.md` | detailed historical phase records |

## Documentation

For current state, prefer operational status documents over old phase notes:

- `ROADMAP.md` — execution order and open milestones;
- `docs/status/TRACK_SCENE_STATUS.md` — track/SGB/scene state;
- `docs/status/NATIVE_RUNTIME_STATUS.md` — native Linux runtime state;
- `docs/PHASE578_NATIVE_SCENE_BUNDLE.md`;
- `docs/PHASE579_GENERIC_VULKAN_DRAW_BUNDLE.md`;
- `docs/PHASE580_NATIVE_SCENE_VULKAN_SET.md`;
- `docs/PHASE581_VULKAN_WORLD_TRANSFORM_PACKET.md`;
- `docs/PHASE582_NATIVE_TRANSLATION_SVWT.md`;
- `docs/PHASE583_SVGP_SEMANTIC_ABI.md`;\n- `docs/PHASE584_AFFINE_SVWT_EXECUTION.md`;\n- `docs/PHASE585_NATIVE_SCENE_VULKAN_PREPARE.md`.

Historical phase files preserve the evidence trail and are not rewritten
retroactively when newer work changes the current operational boundary.
