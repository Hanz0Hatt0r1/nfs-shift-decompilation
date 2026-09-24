# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 78. The phase-71 CI workflow completed successfully for both Python and native regression jobs.

The immediate target is a deterministic pipeline:

`BFF -> IR -> VHF/MEB/BMT/DDS -> shader permutation -> DrawPacket -> renderer`

The milestone is complete when a real BMW M3 asset can be rendered without reading
the original BFF archives at runtime.

### Workstream status

| Workstream | State | Exit criterion |
|---|---|---|
| BFF/XMem-LZX | verified | native and Python paths agree on regression fixtures |
| Resource IR | active/verified | manifest + content-addressed blobs + typed analysis |
| BAS skeleton | verified parser | hierarchy/transforms covered by fixtures |
| BAB bone table | verified parser | bone table + conservative opaque animation tail |
| BAB <-> BAS linkage | implemented | deterministic bone mapping and diagnostics |
| MEB vertex semantics | verified for known BMW samples | semantic usage/index mappings covered by tests |
| Exact vertex packing | mostly proven | deterministic locations/stride/ABI evidence and collision guards; color 460/461 declaration/channel order remains explicitly ambiguous with candidate tooling |
| BMT -> FX -> FXO | implemented selection path | deterministic permutation selection, CTAB sampler/uniform linkage, linked GLSL payload |
| Shader backend | active/validated | selected LinkedShaderPair stages can be compile/link-checked with `glslangValidator`; unsupported toolchains report `unavailable` |
| DrawPacket | implemented contract | canonical DrawPacket carries StaticDraw readiness and explicit blockers |
| Desktop reference renderer | geometry + shader-reference oracle | DrawPacket/RenderCommand execution, DDS DXT/uncompressed decode, multi-sampler textures, VS→PS semantic linkage, external samplerCube and complete DDS cubemap input; full BMW shader/material coverage remains incomplete |
| Skinning | bind-pose verified contract | explicit SkinPose, CPU reference, GLES ABI, bind-pose equivalence check; animated pose decoding remains |
| BAB animation payload | evidence tooling | corpus fingerprints and byte-level differential analysis; keyframe grammar still unproven |
| SGB scene graph | later | one track section assembles from IR |
| Android runtime | later | renderer consumes IR without importer dependencies |

## Execution order

1. Keep CI green and preserve explicit evidence/regression coverage.
2. Resolve the remaining COLOR0/COLOR1 declaration/type and byte-order ambiguity using real BMW evidence; keep ambiguous draws blocked.
3. Validate selected generated shader permutations with an actual GLES compiler where the toolchain is available, then use the result as the RenderCommand submission gate.
4. Keep the material execution ABI authoritative: CTAB float/vector values arrive through SHIFT.MaterialConstantPayload/1.
5. Keep the desktop reference renderer as the golden oracle: embedded VS→PS execution, sampler2D/samplerCube resources, UV families and skin inputs must agree with RenderCommand.
6. Keep explicit SkinPose deformation and SkinnedMeshReference as the CPU oracle, and expose the same payload through RenderCommand.
7. Drive the GLES 3.1 skinning ABI directly from RenderCommand, run the explicit RenderCommand ↔ GLES parity gate, then cross-check shader-driven skinning against the CPU reference.
8. Expand reference execution toward real BMW permutations: TEXCOORD5+ families, remaining D3D9 control flow, exact sampler state and lighting/blend semantics.
9. Prove the exact MEB vertex stream packing for real BMW meshes, especially COLOR0/1.
10. Decode BAB animation payload from multiple clips sharing one skeleton, using corpus and byte-diff evidence.
11. Implement SGB scene semantics and track assembly after the vehicle path is stable.
12. Port the proven IR/render boundary to Android.
13. Only then expand into physics, input, camera, audio and gameplay systems.
## Evidence rules

- A parser result is not considered verified merely because it is syntactically
  plausible.
- Ambiguous fields remain explicitly marked as unknown/inferred until supported by
  multiple samples or runtime-equivalent evidence.
- Candidate shader permutations must not be selected by incidental file order.
- Regression fixtures should cover both positive resolution and unresolved/ambiguous
  cases.


## Phase 44: renderer submission baseline

The neutral renderer path now spans `RenderBinding/1 -> StaticDraw/1 -> RenderResources/1 -> RenderCommand/1 -> desktop reference renderer`. RenderCommand validates vertex ABI, index ranges, shader-source presence, uniform/constant ranges and multi-texture sampler-register/state integrity. The desktop oracle can execute geometry-only and UV0 texture reference paths, while the shader backend can compile/link selected GLES shader pairs when the validator is installed.

## Current blocker for the BMW milestone

The project does **not** yet claim a full real BMW M3 material render. Remaining work is the semantic execution of generated shader code: material constants, multiple texture reads and shader operations must be mapped into a deterministic reference evaluator (and later GLES/Vulkan execution) without inventing undocumented behavior.


## Phase 50-51 baseline

Phases 50 and 51 are already merged on `main`: the shader-backed reference renderer accepts multiple sampler-register texture images and maps `TEXCOORD0..4` to MEB UV layers 130..134. Missing sampler images and missing required UV layers remain explicit execution errors.

## Phase 52: material constant payload

Phase 52 adds `SHIFT.MaterialConstantPayload/1` as the deterministic bridge from `SHIFT.MaterialUniformBinding/1` into the renderer submission contract. Proven float/vector values are packed into 16-byte D3D9-style c-register slots; matrix orientation, non-float types, register conflicts and overflow remain blocking rather than guessed.

The reference shader executor consumes the serialized payload when it is present, keeping the software oracle aligned with the exact RenderCommand data that a future GLES backend will upload.


## Phase 54: vertex-shader reference execution

The desktop reference path now has an explicit VS->PS execution boundary: the embedded vertex ShaderProgram/1 executes against the known MEB semantic inputs, its POSITION output drives clip-space rasterization, and VS outputs are matched to pixel inputs by semantic key before perspective-correct interpolation. The next rendering gap is expanding the proven vertex/material ABI without guessing unresolved MEB COLOR bytes, additional TEXCOORD families or renderer-global resources.


## Phase 55: alternate MEB TEXCOORD family

Phase 55 closes the known 230..234 UVW semantic gap across the desktop renderer and standalone vertex adapter. The next execution milestone is the proven skin-input path (`BLENDWEIGHT0`/`BLENDINDICES0`) or the unresolved COLOR0/1 channel-order/type evidence, followed by renderer-global samplers and the remaining shader control-flow/lighting surface.


## Phase 56: proven skin input semantics

Phase 56 wires MEB 310/580 into the integrated VS reference path. The next rendering/vehicle step is to resolve COLOR0/1 exact type/channel order and then prove the minimal SkinPose adapter that can transform a vertex using known bone weights/indices without conflating that with BAB animation decoding.


## Phase 57: explicit external sampler resources

Phase 57 makes external sampler requirements executable rather than passive: RenderCommand preserves the requirement, the reference renderer accepts explicit sampler2D images by `sN`, and the CLI can reproduce those bindings from DDS files. The next resource milestone is a real cube-map representation for `environmentMap/s3`; in parallel, COLOR0/1 and skin deformation remain separate ABI tracks.


## Phase 58: cube-map external resources

Phase 58 adds the software cube-map resource needed by the documented `environmentMap/s3` path. The next environment step is evidence-backed ingestion of the game's actual cubemap/face payload into `ReferenceCubeTexture/1`; this must not be inferred from a regular 2D DDS. In parallel, COLOR0/1 ABI and actual skin deformation remain independent rendering tracks.


## Phase 59: native DDS cubemap decode

Phase 59 closes the decoder-side half of `environmentMap/s3`: complete DDS cubemaps can become `ReferenceCubeTexture/1`. The remaining environment gap is extracting/identifying the game's actual environment-map DDS payload and proving its binding/face orientation through the asset corpus. COLOR0/1 ABI and skin deformation remain separate tracks.


## Phase 60: explicit skinned-mesh CPU reference

`SHIFT.SkinnedMeshReference/1` turns a ready `SHIFT.SkinnedDraw/1` plus an explicit `SHIFT.SkinPose/1` into a transformed neutral mesh. POSITION is linearly blended from the four declared influences; known direction streams NORMAL/TANGENT/BINORMAL use the direction-only transform and normalization already covered by the CPU skinning reference. UV, color, blend weights and blend indices remain unchanged from the input mesh.

The phase intentionally does not infer animation frames, parent-composed transforms or inverse-bind matrices. It is a render adapter, not a BAB decoder.


## Phase 61: skinned reference render

The desktop reference renderer can now consume a ready SkinnedDraw after explicit SkinPose deformation. The next step is to feed that transformed mesh through the existing VS→PS shader reference path so skinning, material constants, textures and shader semantics can be validated together without deriving pose data from BAB/BAS.


## Phase 62: skinned VS→PS reference

The desktop shader reference now accepts a transformed neutral mesh from an explicit SkinPose and runs it through the same embedded VS→PS path as static material draws. This proves the local chain without introducing animation decoding or inverse-bind inference.


Phase 63 adds a `SHIFT.RenderCommand/1` adapter for `SHIFT.SkinnedDraw/1`. The command preserves the common vertex/material/resource submission ABI plus an explicit `SHIFT.Skinning/1` payload containing SkinPose and bind-palette metadata. The next step is to connect this command to the existing GLES 3.1 skinning contract and keep the desktop reference path as the oracle.


## Phase 64: RenderCommand → GLES skinning ABI

The GLES 3.1 skinning contract can now be built directly from a skinned `SHIFT.RenderCommand/1`. This keeps SkinPose, palette size and BLENDWEIGHT0/BLENDINDICES0 locations identical between the neutral submission layer and the future Android renderer.


## Phase 65: explicit extended shader semantics

`TEXCOORD5` is proven in the BMW bodywork shader interface, but no MEB property id for its source stream has been established. The reference path therefore accepts an explicit per-vertex semantic stream keyed by `(TEXCOORD, 5)` instead of inventing a property mapping. Without that stream, the shader remains blocked.

This mechanism is generic enough to carry future evidence-backed semantics while keeping the MEB ABI table strict. The next evidence milestone remains exact COLOR0/COLOR1 declaration and channel order.


## Phase 66: COLOR ABI evidence CLI

The existing `color_abi.py` evidence logic is now exposed through `shift_importer.py color-evidence`. It accepts a raw 4-byte-per-sample stream for MEB property 460 or 461 and emits deterministic RGBA/BGRA candidates, hashes and channel statistics. An optional expected RGBA8 stream adds exact byte comparison but cannot select an ABI automatically.


## Phase 67: MEB JSON COLOR evidence

COLOR ABI evidence can now be generated directly from MEB JSON output: 460 → `colors`, 461 → `colors2`. The report retains both channel-order candidates and optional external RGBA comparison without promoting an ABI choice to verified.


## Phase 68: direct BFF/MEB COLOR evidence

The color investigation now has a direct archive path: BFF entry → MEB decoder → property 460/461 stream → ColorABIEvidence/1. This keeps the evidence tied to the original resource bytes and records the resource SHA256 and property payload metadata. ABI selection remains blocked until external declaration/channel-order evidence is proven.


## Phase 69: COLOR evidence corpus

The COLOR ABI investigation now supports corpus-level aggregation of `SHIFT.ColorABIEvidence/1` reports. The aggregator groups reports by property 460/461, tracks unique candidate hashes, computes cross-report candidate stability and averaged channel statistics, and explicitly keeps `selection` at `not-selected`. This provides a reproducible gate for deciding whether external declaration/channel-order evidence is strong enough to change the MEB ABI.


## Phase 70: BFF corpus COLOR evidence

The unresolved 460/461 investigation can now scan the actual BFF corpus directly. Every decoded MEB color stream contributes a provenance-tagged evidence report, while corpus aggregation measures candidate consistency and never selects an ABI automatically.


## Phase 71: Skinned RenderCommand reference

A dedicated `render_skinned_render_command_reference()` entry point now executes a ready skinned RenderCommand through the desktop shader reference. The same command-level payload carries SkinPose, skin attributes, textures and ShaderProgram/1 into the reference raster path. The next step is comparing this oracle with the generated GLES 3.1 draw setup and then resolving the remaining COLOR0/1 ABI evidence.

## Phase 72: packed-color declaration evidence

The full `SHIFT.exe.c` source now provides a concrete packed-color observation:
`FUN_008310c0` forms `0xAARRGGBB` from float RGBA input, yielding BGRA memory order on
the original little-endian target, and `FUN_00854e70` writes that packed value during
vertex-buffer conversion. The project records this as supporting evidence for the
`D3DCOLOR` candidate but does not promote MEB 460/461 to verified, because the exact
source declaration linkage is still not proven.

The evidence report now names the coupled D3D9 candidates explicitly and retains
`selection=not-selected`.

## Phase 73: RenderCommand ↔ GLES skinning parity

The neutral skinned RenderCommand is now cross-checkable against the generated
GLES 3.1 skinning contract. The parity gate verifies attribute locations and
formats, four influences, SkinPose identity (including deterministic matrix
hash), bind-palette identity and readiness/blockers. A mismatch is a hard,
machine-readable backend blocker; no alternate payload is synthesized silently.

## Phase 82: direct PE image resolver

Phase 82 adds direct PE address resolution for `SHIFT.exe`. The resolver parses the DOS/PE headers, section table, image base and maps the recovered virtual addresses for `DAT_00b90088` and `PTR_DAT_00b901d0` to file offsets. It distinguishes file-backed bytes from runtime-only memory and leaves `MEB 460/461 -> type code` unresolved until the actual declaration table contents are evidenced.

## Phase 87: D3D9 Stream-group topology

Phase 87 formalizes how the renderer groups declaration records by Stream and derives per-stream byte size from the Type table. This is the next bridge for exact MEB vertex-stream reconstruction; the direct property-to-Type mapping remains the blocker.

## Phase 86: D3D9 Type semantic validation

Phase 86 introduces an explicit oracle for comparing future raw Type-table values with the `D3DDECLTYPE` semantics already recovered from `FUN_00854e70`. This lets the next memory dump prove table contents without hardcoding guessed values into the renderer.

## Phase 85: D3D9 Type layout tables

Phase 85 formalizes the runtime meaning of the two opaque Type-indexed layout tables and the 18-entry address-span hint. This closes another source-side part of the declaration ABI; MEB 460/461 -> Type remains the unresolved bridge.

## Phase 84: D3D9 declaration canonicalizer

Phase 84 formalizes the recovered declaration interning/comparison path in `FUN_00830f80`. All six bytes/word fields of the 8-byte declaration record are part of the equality check; the remaining blocker is still the MEB property-to-Type linkage.

## Phase 83: STREAM declaration record semantics

Phase 83 turns the recovered 8-byte STREAM descriptor construction into machine-readable evidence and identifies its field layout as `D3DVERTEXELEMENT9`-shaped. This closes the XML-side path `Type/Usage/Channel -> declaration record`; the MEB property-to-Type ordinal link remains the active blocker.

## Phase 81: raw memory table decoder

Phase 81 adds a deterministic decoder for raw loaded-memory evidence of the opaque D3D9 tables. This is the bridge needed to recover the actual Type-table values from a future Ghidra/WinDbg memory export; the tool does not treat the absence of such bytes as a verified ABI.

## Phase 80: recovered Usage semantics

Phase 80 records the source-backed XML STREAM Usage table and the exact `Colour = usage 6` branch. The usage table is independent from the opaque primitive Type table; no MEB 460/461 declaration type is selected.

## Phase 79: D3D9 lookup-table shape evidence

Phase 79 records symbol-address spans, 4-byte table indexing, the 17-entry XML type ordinal domain and the exact declaration/type lookup callsite. The report intentionally labels adjacent-address capacity as a layout hint because Ghidra emitted the global initializers as opaque `undefined` objects.

## Phase 78: D3D9 primitive type semantics

Phase 78 formalizes the recovered declaration conversion switch in FUN_00854e70. All 17 codes 0..16 are observed and aligned with the D3D9 D3DDECLTYPE numeric table, with source behaviors retained per case. Type code 4 is explicitly tied to the packed-color helper, but MEB 460/461 -> type code 4 remains a separate unresolved linkage.

## Phase 77: CPrimitiveType source anchors

Phase 77 extracts original CPrimitiveType.cpp line numbers from embedded diagnostic calls. The evidence report now carries both decompiler and original-source line coordinates; this improves source navigation but does not by itself identify MEB 460/461 declaration types.

## Phase 76: type-table reference census

Phase 76 adds a source callsite census for FUN_00853c20 and records embedded CPrimitiveType.cpp source-path references. Exact source line lists are retained; the opaque DAT_00b90088 contents are still unavailable, so the COLOR ABI remains blocked.

## Phase 75: source type-table chain evidence

Phase 75 extends the source evidence scanner with line-addressed observations and the recovered declaration type-table chain. The scanner now records FUN_00853c20 -> DAT_00b90088, the XML Type lookup through PTR_DAT_00b901d0, XML Usage/Channel, and the XML Colour stream family. This narrows the source-level ABI path without making an undocumented ABI choice.

COLOR0/1 remains explicitly blocked until the declaration-table contents or equivalent runtime evidence proves MEB 460/461 -> D3D9 type and byte order.

## Phase 74: machine-readable D3D9 source evidence

The recovered SHIFT.exe Ghidra C source is now consumable by a dedicated source
evidence scanner. It records the packed-color helper, the declaration conversion
path and the STREAM Type/Usage/Channel parser as explicit observations. The report
keeps the critical `460/461 -> type 4` linkage unresolved because the exported
global table contents are not sufficient to prove that mapping.

## Phase 88: declaration topology and PE address consistency

Phase 88 makes the STREAM grouping topology machine-readable and regression-tested. FUN_00854e70 groups declaration elements by Stream using a 0x14-byte per-stream record, tracks element count and declaration-record pointers, and accumulates byte size through DAT_00b8eef0. The report remains conservative about MEB property linkage.

The PE resolver is corrected to the source-backed Type layout addresses DAT_00b8eef0 (element size) and DAT_00b8ef38 (source component count), both covering the recovered 18-entry domain including sentinel Type 0x11. This removes the stale DAT_00b900d8 alias from the PE path while preserving the separate declaration lookup table at DAT_00b90088.


## Phase 89: PE Type-table semantic validation

`source-d3d9-pe-evidence` now validates file-backed DAT_00b8eef0 and DAT_00b8ef38 contents against the recovered D3D9 Type semantic profile. The result is machine-readable and fail-closed: missing bytes are `unavailable`, conflicting values are `mismatch`, and only a complete semantic match reaches `match`. This validates table contents but does not select an MEB 460/461 declaration Type.

## Phase 90: D3D9 declaration evidence chain

Phase 90 связывает уже проверенные слои в один machine-readable contract. `SHIFT.D3D9DeclarationChainEvidence/1` проверяет согласованность PE Type-profile validation, `FUN_00854e70` STREAM grouping, `FUN_008587e0` 8-byte `D3DVERTEXELEMENT9`-shaped record и `FUN_00830f80` full-record canonicalization. Любое отсутствующее или противоречивое звено блокирует итог `observed`; цепочка не выбирает MEB 460/461 → Type ordinal и явно фиксирует отсутствие runtime memory/declaration evidence.

## Phase 91: raw D3D9 declaration instance

Phase 91 добавляет instance-level decoder для фактических 8-байтных declaration records. Он декодирует поля `Stream/Offset/Type/Method/Usage/UsageIndex`, проверяет Type against the recovered profile и fail-closed различает `match`, `partial` и `mismatch`. Source-backed Method=0 проверяется отдельно; Usage byte остаётся сырым значением без недоказанного преобразования. MEB 460/461 → Type ordinal остаётся `not-proven`.

## Phase 92: declaration instance in the full chain

Phase 92 подключает `SHIFT.D3D9DeclarationInstanceEvidence/1` обратно в `SHIFT.D3D9DeclarationChainEvidence/1`. Когда runtime declaration report передан, chain требует `match`, stride 8 и observed D3DVERTEXELEMENT9 shape; mismatch/partial становится явным blocker. Без runtime report цепочка остаётся source-backed и не выдаёт runtime proof.


## Phase 93: declaration instance integrity

Phase 93 усиливает instance-level evidence: декодер распознаёт точную форму `D3DDECL_END`, а declaration chain не принимает report со статусом `match`, если фактический stride или D3DVERTEXELEMENT9 shape не совпадают с recovered ABI. Следующий практический вход — реальный runtime/memory dump.


## Phase 94: runtime memory declaration evidence

Phase 94 adds SHIFT.D3D9MemoryDeclarationEvidence/1 as the reproducible bridge from a raw loaded-memory dump to the already recovered D3D9 declaration ABI. The capture records the virtual base/range, little-endian interpretation, complete and slice SHA-256 provenance, exact bytes, and a declaration instance trimmed through the exact D3DDECL_END shape. Extra bytes after the sentinel remain explicitly outside the declaration array.

The declaration chain can now consume the wrapper directly and fail closed on incoherent provenance, bytes, stride, or declaration shape. This is runtime evidence infrastructure only: it does not authenticate an external dump and does not infer MEB 460/461 -> Type.


## Phase 95: runtime declaration layout

Phase 95 adds SHIFT.D3D9RuntimeDeclarationLayoutEvidence/1. Runtime declaration records are grouped by Stream and checked against the recovered Type byte sizes: each Stream starts at Offset 0 and every following Offset advances by the packed size of its preceding Type. The report exposes per-Stream byte-size totals and explicit mismatch rows.

The declaration chain can consume this as an additional runtime gate. This proves consistency of the supplied declaration bytes with the recovered offset-building rule; it does not infer MEB 460/461 -> Type or authenticate dump provenance.


## Phase 96: source provenance coherence

Phase 96 adds an optional but strict source-provenance guard to the D3D9 declaration chain. Once SHA-256 provenance is present, all source-backed reports must identify the same SHIFT.exe.c snapshot by hash, size and line count. Missing provenance in legacy reports remains explicitly not-supplied rather than being invented.
