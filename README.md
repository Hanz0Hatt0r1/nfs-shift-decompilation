# Need for Speed: SHIFT — decompilation and Linux reimplementation

Evidence-driven reconstruction of *Need for Speed: SHIFT* resource formats,
runtime contracts and game systems, with an offline Linux/Vulkan runtime as the
primary execution target.

**Current development phase: 581.**

The project is no longer only a BFF extractor. It now contains a connected
resource, scene, render, physics, AI/track and native-runtime pipeline. The
current vertical-slice goal is to move a real Silverstone scene and a real
vehicle through evidence-backed IR into the Linux runtime without inventing
unknown retail behavior.

## Project rules

The reconstruction is deliberately fail-closed.

- Proven static/source behavior is separated from runtime observations.
- Ambiguous values remain ambiguous.
- Missing evidence is recorded as a blocker instead of replaced with a
  plausible value.
- Serialized container equivalence is never assumed merely because two formats
  can be normalized into the same renderer contract.
- Native execution requires explicit provenance gates in addition to a
  structurally valid RenderCommand.

Typical evidence states are `proven`, `verified`, `inferred`,
`ambiguous`, `unknown`, `unsupported` and `blocked`.

## Current architecture

### Resource path

```text
BFF
  → extraction / hashes / typed analysis
  → neutral resource IR
  → material / geometry / scene contracts
```

BFF support currently covers the SHIFT paths used by the project for Type
0/1/2 resources and X12d=2 encryption. Type 3 remains dependent on an external
Oodle-compatible runtime.

### Render path

```text
BFF
  → MEB / IMB / BMT / DDS / FX / FXO
  → DrawPacket
  → StaticDraw
  → RenderCommand
  → Vulkan bundle
  → native Linux runtime
```

The renderer path has two mature branches:

- BMW/MEB, used as the established material and Vulkan regression slice;
- SGB/MeshInst/IMB, used to bring Silverstone scene geometry into the same
  neutral RenderCommand and Vulkan contracts.

The desktop/reference renderer remains the deterministic oracle. Linux/Vulkan
is the native backend direction.

### Scene path

The current Silverstone path is:

```text
SGB
  → NODE / SUMM / PART / FLAT / OBJECT
  → scene placement
  → OBJECT resource + world-transform handoff
  → MeshInst
  → IMBNeutralGeometry
  → RenderBinding
  → runtime shader attribution
  → RuntimeProvenDraw
  → NativeSceneBundle
  → NativeSceneVulkanSet
```

Important contracts in the final part of that chain:

- `SHIFT.IMBNeutralGeometry/1` — source-backed IMB geometry normalization;
- `SHIFT.IMBRuntimeShaderAdmission/1` — exact runtime shader identity
  admission;
- `SHIFT.RuntimeProvenDraw/1` — proof carried through StaticDraw and
  RenderCommand;
- `SHIFT.NativeSceneBundle/1` — deterministic scene-level manifest containing
  only runtime-proven draws;
- `SHIFT.VulkanDrawBundle/1` — neutral atomic Vulkan artifact bundle;
- `SHIFT.NativeSceneVulkanSet/1` — ordered scene draw set that re-resolves
  exact IMB/DDS resources through IR and builds one Vulkan child bundle per
  admitted draw.

Phase 581 executes each proven SGB affine world matrix by baking it into the
neutral Vulkan geometry packet before child-bundle preparation. Legacy BMW and
geometry-only paths remain object-space unless this behavior is explicitly
requested. Renderer-owned external samplers are still not fabricated.

### Native Linux runtime

`native_runtime/` contains the offline Linux shell:

```text
native IR / prepared Vulkan bundles
  → XCB window
  → Vulkan swapchain
  → indexed draw(s)
  → fixed 60 Hz frame/state boundary
```

It currently supports the established prepared material/bundle path, per-draw
pipeline state, constants, 2D textures, optional cubemap resources, validation
layers and multi-draw submission. Camera state, vehicle-control intent and a
physics participant/tick boundary are represented without synthesizing unknown
retail integration semantics.

This runtime intentionally excludes EA services, DRM, login/cloud services,
matchmaking/online networking and Bink/video playback.

## Current status

| Area | State | Main open boundary |
|---|---|---|
| BFF / XMem-LZX | verified for active corpus | uncommon variants and external Type 3 codec |
| Resource IR | active / verified | remaining format-specific joins |
| MEB / vertex ABI | strong static coverage | more same-instance runtime proof |
| IMB / MeshInst | source-backed v0.4 path | IMX XML adapter and broader variants |
| BMT / material state | active / source-backed subset | enabled alpha-test, bias/stencil where not yet proven |
| FX / FXO | parser + runtime attribution pipeline | authentic retail captures for exact tied permutations |
| Desktop renderer | active oracle | broader exact D3D9 parity |
| Vulkan | active native backend | neutral scene-set preparation/runtime admission and native scene submission |
| SGB / scene | strong structural/render handoff | native world placement, streaming/LOD, some MatrixNumber history |
| Camera | active structural state | higher-level gameplay behavior |
| AI / track | source-backed core | remaining linked/local runtime search behavior |
| Vehicle physics | structural reconstruction active | exact numeric provider parity |
| Specialized providers | capture-ready | authentic runtime frame |
| BAB animation | evidence-backed grammar | remaining axis/order/trailing semantics |
| Android | deferred | waits for stable desktop/native runtime boundary |

## Silverstone scene progress

The supplied Silverstone Era3 corpus has been used to close the current static
scene dependency surface:

- 427/427 selected IMBs decode through the v0.4 neutral geometry path;
- 428 primitive material references resolve in the track corpus;
- archive-local BMT/DDS dependencies have been audited;
- the referenced global FX families resolve through the render archive;
- compiled FXO candidates are inventoried and content-deduplicated;
- all 428 primitive shader contexts are valid but remain statically ambiguous;
- the tied runtime search surface is reduced to 51 pixel-shader byte hashes.

The capture path is already implemented:

```text
runtime target set
  → raw D3D9 shader/draw prefilter
  → exact IMB resource + draw-range routing
  → same-instance runtime binding evidence
  → unique VS/PS/pair match
  → runtime shader admission
  → exact MaterialBinding relink
  → exact scene primitive
  → RuntimeProvenDraw
```

The external evidence blocker is still an authentic Silverstone D3D9 capture.
The code path no longer needs a guessed shader choice.

## BMW M3 E36 render slice

BMW remains the stable material/Vulkan regression path:

```text
VHF → MEB → BMT → FX/FXO → DrawPacket → RenderCommand → Vulkan
```

The retail BMW corpus has exact BMT/FX/DDS dependency handling and a runtime
shader target/match pipeline. Concrete tied retail FXO selection still requires
an authentic same-instance BMW body D3D9 capture.

The canonical paint bindings include material 2D textures plus renderer-owned
external resources such as environment/shadow inputs. External resources remain
explicit in the neutral renderer ABI.

## Vehicle physics

The asset path is:

```text
CDF + EDF + GDF + SDF
  → VehiclePhysicsAssetGraph
  → participant admission
  → construction / provider selection
  → solver frame
  → post-solve boundary
```

The project has reconstructed the specialized-provider control and workspace
shape far enough to capture and compare real frames:

- 40- and 34-scalar domains;
- provider selector/reset lifecycle;
- row/workspace topology;
- source-derived factor/dependency/update/operator IR;
- reset→solve ordering;
- participant creation/load and manager ingestion boundaries;
- participant registry/reselection/finalization contracts;
- capture bundle verification and source-mutation correlation.

Exact retail numeric parity remains blocked on one authentic runtime provider
frame. The runtime does not invent the missing force/integration equations.

## Build and test

Run the Python suite from the repository root:

```bash
python -m pytest
```

Run the live-dump utility tests:

```bash
make -C tools/shift_live_dump test
```

Build the native Linux runtime:

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
```

For headless Vulkan validation, see `native_runtime/README.md`. Linux CI uses
software Vulkan/Xvfb coverage for the native path.

## Scene pipeline commands

The scene pipeline is intentionally split into inspectable contracts.

Decode and place the SGB scene:

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

Join placement and OBJECT handoffs, then resolve resources through IR:

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

Freeze only runtime-proven scene draws:

```bash
python shift_importer.py native-scene-bundle \
  out/scene-render-binding.json \
  out/native-scene-bundle.json
```

Build a neutral atomic Vulkan draw directly:

```bash
python shift_importer.py vulkan-draw-bundle \
  out/render-command.json \
  out/neutral-mesh.json \
  out/vulkan-draw
```

Build the ordered Phase 580 scene Vulkan set:

```bash
python shift_importer.py native-scene-vulkan-set \
  out/native-scene-bundle.json \
  out/scene-render-binding.json \
  out/ir \
  out/native-scene-vulkan
```

`SHIFT.NativeSceneVulkanSet/1` revalidates the Phase 578 scene hashes,
re-resolves the exact IMB path/archive/SHA, checks the exact primitive range,
resolves ordinary material 2D DDS resources from IR and emits ordered
`SHIFT.VulkanDrawBundle/1` children.

Phase 581 automatically bakes each proven affine SGB world matrix into the
scene child's neutral geometry. A child set can therefore clear the transform
blocker while still remaining separate from actual `native_runtime` scene-set
admission. Required external runtime resources remain independent blockers.

## Runtime capture

The repository includes D3D9 and live-memory evidence tooling. Capture is used
only where static evidence cannot uniquely close a runtime identity or numeric
boundary.

Examples:

```bash
python tools/verify_specialized_provider_capture_bundle.py CAPTURE_DIR

python tools/verify_specialized_provider_capture_bundle.py \
  CAPTURE_DIR \
  --reset-events CAPTURE_DIR/scalar_reset_events.jsonl \
  -o provider_bundle_manifest.json

python tools/preflight_specialized_provider_capture.py \
  SHIFT.zip \
  out/provider-capture \
  --probe-script tools/gdb_sdf_solver_probe.py
```

The shader capture pipeline has separate BMW and IMB/Silverstone target,
prefilter, evidence and attribution contracts under `shift_importer.py` and
`tools/`.

## Main blockers

These blockers are independent; resolving one does not justify guessing the
others.

1. **Silverstone shader attribution** — authentic D3D9 capture needed to select
   concrete tied IMB shader permutations.
2. **Native scene-set admission** — Phase 581 produces transformed ordered
   Vulkan children, but `native_runtime` still consumes the older established
   BMW bundle/set contract rather than `SHIFT.NativeSceneVulkanSet/1` directly.
3. **Renderer-owned scene resources** — external samplers/resources require an
   explicit runtime binding contract.
4. **Scene runtime completeness** — some per-instance MatrixNumber update
   history, higher-level streaming and LOD behavior remain unresolved.
5. **Vehicle provider numeric parity** — authentic provider frame required.
6. **BMW exact tied FXO selection** — authentic same-instance body capture
   required.
7. **IMX** — XML MeshInst neutral adapter remains separate from the source-backed
   IMB path.

## Repository map

| Path | Purpose |
|---|---|
| `shift_importer.py` | primary importer/analysis/orchestration CLI |
| `src/formats/` | resource/material/geometry/collision parsers |
| `src/render/` | neutral render contracts, resources and reference renderer |
| `src/render/vulkan/` | Vulkan-neutral packet/bundle preparation |
| `src/scene/` | SGB, MeshInst, IMB and scene/native bundle reconstruction |
| `src/bmw/` | BMW retail material/shader/capture/Vulkan evidence path |
| `src/track/` | track metadata and runtime selection/query contracts |
| `native_runtime/` | offline Linux XCB/Vulkan runtime |
| `native_capture/` | Windows D3D9 capture producer |
| `native_vulkan/` | native Vulkan support/build path |
| `tools/` | evidence, trace, capture and audit utilities |
| `tests/` | regression suite |
| `docs/status/` | current subsystem status |
| `docs/PHASE*.md` | detailed historical phase records |

## Documentation

Use operational status files for the current state and phase files for detailed
history:

- `ROADMAP.md` — execution order and open milestones;
- `docs/status/TRACK_SCENE_STATUS.md` — track/SGB/scene state;
- `docs/status/NATIVE_RUNTIME_STATUS.md` — native runtime state;
- `docs/PHASE578_NATIVE_SCENE_BUNDLE.md` — runtime-proven scene manifest;
- `docs/PHASE579_GENERIC_VULKAN_DRAW_BUNDLE.md` — neutral atomic Vulkan
  bundle;
- `docs/PHASE580_NATIVE_SCENE_VULKAN_SET.md` — ordered native-scene Vulkan set;
- `docs/PHASE581_VULKAN_SCENE_TRANSFORM.md` — affine scene transform execution.

Historical phase documents are not rewritten retroactively when newer evidence
changes the current operational boundary.
