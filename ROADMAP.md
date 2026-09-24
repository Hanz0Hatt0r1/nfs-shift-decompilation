# SHIFT Decompilation Roadmap

This roadmap tracks the runtime-oriented path from verified resource parsing to a
minimal reproducible render of one real SHIFT vehicle.

## Current milestone: BMW M3 static render

Baseline `main` is at phase 142. The phase-71 CI workflow completed successfully for both Python and native regression jobs.

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
2. Use the supplied 1.02 corpus to unblock COLOR0 at the D3D9 Type/Usage/Channel level; keep COLOR1 explicitly unresolved because property 461 is absent from the supplied corpus and retain the runtime-instance correlation as the next proof target.
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


## Phase 97: D3D9 declaration bind API

Phase 97 adds SHIFT.D3D9ApiBindEvidence/1 for the recovered FUN_0082e510 wrapper. The source shows a cached current declaration pointer and a device COM-vtable dispatch at byte offset 0x15c. The documented IDirect3DDevice9 ordering identifies slot 87 as SetVertexDeclaration, creating a source-backed bridge from the recovered declaration object to the actual D3D9 bind API boundary.

The declaration chain can consume this evidence and includes its source provenance in snapshot coherence. MEB 460/461 -> Type remains not-proven.


## Phase 98: D3D9 render API boundary

Phase 98 adds SHIFT.D3D9RenderApiBoundaryEvidence/1. The recovered mesh render setup is now tied to the D3D9 API boundary: SetVertexDeclaration (slot 87), SetStreamSource (slot 100), SetIndices (slot 104), and an indexed draw dispatch at DrawIndexedPrimitive (slot 82). The source-side mesh setup order is recorded separately from the external API slot identity.

This closes the source-backed setup path down to the draw boundary. It does not establish MEB 460/461 -> Type, runtime dump authenticity, or a specific mesh draw call identity beyond the recovered dispatch evidence.


## Phase 99: D3D9 declaration creation

Phase 99 formalizes the recovered FUN_00830f80 creation boundary. The canonicalizer allocates element_count * 8 + 8 bytes, copies the recovered declaration-record array, and dispatches through IDirect3DDevice9 vtable slot 86 (0x158) as CreateVertexDeclaration. The resulting declaration object is retained by the interned declaration record.

Together with Phase 97, this gives a source-backed creation-to-bind path without assuming the unresolved MEB 460/461 -> Type mapping.


## Phase 100: declaration count boundary

Phase 100 formalizes the recovered declaration-count helper FUN_0082ea90. It walks 8-byte records using the first WORD (Stream) and stops counting when Stream >= 0xff; FUN_00830f80 then allocates count * 8 + 8 bytes for declaration creation. The report deliberately does not equate that one-field stop rule with the full D3DDECL_END sentinel.


## Phase 101: exact D3DDECL_END producer

Phase 101 formalizes the producer-side terminator in FUN_008587e0. The source writes Stream=0xffff, Offset=0, Type=0x11, Method=0, Usage=0, UsageIndex=0 at the record immediately after the parsed declaration elements. This closes the exact sentinel semantics that Phase 100 intentionally left separate from the one-field Stream >= 0xff count rule.


## Phase 102: runtime/source sentinel coherence

Phase 102 correlates the exact runtime D3DDECL_END record with the source-backed sentinel producer in FUN_008587e0. The chain checks all six sentinel fields and confirms that the runtime sentinel index agrees with the declaration-array boundary. A missing or altered field is an explicit blocker rather than a recoverable guess.


Phase 102 follow-up: the sentinel producer extractor now matches the actual uploaded decompiler form using field/address expressions rather than a single local-variable spelling.


## Phase 103: D3D9 declaration lifecycle call chain

Phase 103 adds SHIFT.D3D9DeclarationLifecycleEvidence/1. The recovered source call graph now explicitly links mesh construction to FUN_008587e0, declaration creation through FUN_00830f80 and CreateVertexDeclaration, and the render path through FUN_00854d30, FUN_0082e510 and SetVertexDeclaration. This is a static lifecycle contract, not runtime frame attribution.


## Phase 104: D3D9 binding argument semantics

Phase 104 formalizes the resource arguments forwarded by FUN_00854da0 and FUN_00854e10. SetStreamSource receives the stream number, per-stream vertex-buffer pointer, zero byte offset and computed stride; SetIndices receives the recovered index-buffer pointer. These are source-backed argument semantics and do not infer MEB property mapping.

## Phase 105: MEB COLOR Type constraint bridge

`d3d9_color_bridge_evidence.py` formalizes the strongest currently defensible constraint for MEB properties 460/461: 4-byte normalized `u8x4` storage is compatible with D3D9 Type 4 (`D3DCOLOR`) or Type 8 (`UBYTE4N`). This narrows the search space but does not select a Type.

The recovered SHIFT source independently proves the `Colour` stream family and a Type-4 packed-color conversion path. Because the exported source does not expose a MEB property id → declaration-record identity edge, the bridge remains `not-proven`. Runtime COLOR declaration records are observations, not automatic attributions to MEB 460/461.

Next evidence target: correlate one real .meb color payload with the exact declaration record consumed by the same mesh instance, preferably with runtime memory/API capture and a source-backed property identity.

## Phase 106: integrate MEB color constraints into the D3D9 chain

The common declaration-chain validator now consumes the Phase 105 color bridge
as an optional evidence gate. The gate requires both 460 and 461 storage
constraints plus the candidate D3D9 Type set {4, 8}; it deliberately rejects
the input as complete when either property is missing or the bridge claims a
resolved Type.

This makes the MEB boundary machine-checkable without turning a candidate into
a false proof. The next closure target remains a same-instance correlation
between an actual MEB color payload and the exact D3D9 declaration record used
by that mesh.

## Phase 107: preserve MEB property descriptor bytes

MEB vertex-property descriptors are now retained with their exact file-relative offset, three LE DWORD values and raw 12-byte representation. Regression coverage uses synthetic 460/461 descriptors and verifies the offsets and payload ordering.

This removes a provenance gap at the MEB boundary: future runtime correlation can start from exact descriptor bytes rather than a derived property-name table. The D3D9 Type selection remains unresolved until the same mesh instance is tied to a concrete declaration record.

## Phase 108: exact MEB COLOR resource provenance

The BFF-backed COLOR evidence path now preserves the exact descriptor and payload byte ranges from each decoded `.meb`, including descriptor raw bytes and payload SHA-256. It also checks that the parser's decoded 460/461 stream is identical to the selected raw payload range.

The result is a reproducible bridge from an actual archive/resource to the MEB property byte range. It still does not prove which D3D9 declaration Type consumes that range; that requires same-instance runtime correlation.

## Phase 109: bind real MEB resource provenance to the color bridge

The Phase 105 color bridge now accepts real BFF-backed COLOR evidence as an optional resource proof. It correlates the report property ID with its preserved MEB descriptor, exact descriptor/payload ranges, payload hash, and decoded stream bytes. Multiple reports remain independent for 460 and 461, so a bad or unknown report cannot falsely resolve the other property.

The final Type identity is still not-proven. The next closure condition is a same-instance runtime correlation from this exact MEB resource/payload to the D3D9 declaration record.

## Phase 110: prove the MEB 460/461 descriptor triple

Static analysis now identifies the binary mesh loader `FUN_00859800` as consuming 12-byte triples `[Type ordinal, Usage ordinal, Channel]`, resolving Type and Usage through the recovered D3D9 lookup functions and copying Channel into UsageIndex. The source also contains the `.meb` resource-extension registration and the `LoadBinaryMeshFromResource` diagnostic.

The new descriptor-triple validator consumes exact `MEBMesh.property_descriptors`. Under complete source evidence, 460 must be `[4,6,0]` and 461 must be `[4,6,1]` for a `match`, which resolves their D3D9 Type code to 4. Incorrect descriptors fail as `mismatch`; missing descriptors remain `partial`.

Next target: correlate the resolved Type-4 descriptor with the actual runtime declaration record for the same mesh instance, including the D3D9 Usage byte produced by the opaque usage table.

## Phase 112: one-command Linux MEB evidence collector

`tools/collect_meb_evidence.py` provides a single-command collection path for the unresolved MEB↔D3D9 work. It recursively scans direct `.meb` files and `.bff` archives, parses every MEB, records property histograms, and preserves exact 460/461 descriptor and payload bytes with BFF/resource provenance and hashes. Optional `--source SHIFT.exe.c` adds source-backed D3D9 and exact descriptor-triple proofs.

The output is one self-describing ZIP; full BFF archives are never copied into it. The collector is designed so the next analysis pass can operate entirely from the returned bundle.


## Phase 116: corpus-backed COLOR0 evidence

The supplied `shift_meb_evidence.zip` was analyzed without committing the 166 MB raw archive. The scan covered 70,370 MEB resources across 1,834 BFF files with zero errors. Property 460 appears in all 70,370 resources and every descriptor is exactly `[4, 6, 0]`; the decoded 460 stream matches its recorded raw payload for all 70,370 resources.

Together with the recovered `FUN_00859800` binary triple semantics and the source-backed Type/Usage tables, this establishes the resource-level bridge `COLOR0 -> D3D9 Type 4 (D3DCOLOR), Usage 6, UsageIndex 0`. Property 461 was not observed in the supplied game corpus, so COLOR1 remains unresolved rather than being inferred from 460. The remaining proof target is same-instance correlation with an actual runtime declaration generated by the renderer.

## Phase 117: runtime D3D9 capture bridge

Phase 117 adds `SHIFT.D3D9RuntimeBindingEvidence/1` for external runtime capture. Declaration creation bytes are decoded with the existing 8-byte declaration-instance contract; `SetVertexDeclaration`, stream/index bindings and indexed draws are grouped by frame. Same-resource correlation accepts explicit SHA-256 or normalized resource path, while Usage-ordinal mappings remain external and are never guessed.

A real BMW M3 E36 LODA golden manifest was also added with stable MEB identity, geometry, primitive/material references and the corpus-proven COLOR0 descriptor `[4,6,0]`.

## Phase 118: executable BMW golden render gate

`SHIFT.BMWGoldenRenderGate/1` now validates that a render-facing `DrawPacket/1` still points at the exact selected BMW MEB, preserves vertex/triangle counts and primitive ranges, carries the proven COLOR0 descriptor, and has unique shader/linked-GLSL state before the render is accepted as a golden result.

The next implementation target is the first real end-to-end BMW material packet: resolve the selected `.mtx/.bmt` through BMT -> FX -> FXO, require a unique VS/PS pair, construct `RenderCommand/1`, compile-check GLSL when available, and generate a deterministic desktop PPM hash.


## Phase 119: resource identity propagation

`DrawPacket/1` and `RenderBinding/1` now preserve the decoded MEB content SHA-256 when present. The BMW golden gate requires this identity rather than accepting path-only matches. This keeps the selected real M3 MEB stable through the render pipeline.

Next: construct the first real BMW material slice end-to-end and turn its linked shader/RenderCommand output into a deterministic golden image.


## Phase 120: exact BMW render slice

`SHIFT.BMWRenderSlice/1` selects the golden M3 packet from `RenderBinding/1` using both normalized resource path and exact MEB SHA-256. The selected packet keeps its matching `StaticDraw/1` and `RenderCommand/1` entries by packet index. Path-only or SHA-only matches remain blockers.

Next: execute this exact real-material slice through BMT -> FX -> FXO, shader translation and RenderCommand, then record the first desktop golden image hash.


## Phase 121: exact BMW material slice

`SHIFT.BMWMaterialSlice/1` narrows the exact BMW render slice to one real primitive/material. The selector requires unique shader selection, unique VS/PS pairing, linked GLSL, resolved material data, explicit sampler registers and a ready `RenderCommand/1` when present.

Next: execute the selected material through the desktop shader reference and compare the result against the linked shader IR and RenderCommand inputs.


## Phase 122: BMW desktop reference render

`SHIFT.BMWReferenceRender/1` now executes a ready BMW material slice through the existing desktop `RenderCommand/1` oracle and records a deterministic PPM SHA-256. Shader-reference mode reuses the existing `render_textured_render_command` path and requires explicit reference texture data rather than loading BFFs at render time.

Next: feed one actual BMW material slice with a real mesh payload, inspect the selected FXO VS/PS pair and drive the first non-synthetic golden image.


## Phase 123: shader permutation identity

`SHIFT.ShaderPermutationIdentity/1` is now computed from exact VS/PS bytes plus shader-model and reflection data. Blob offsets are excluded from the canonical fingerprint. `MaterialBinding/1` exposes the identity and the BMW golden gate requires it whenever shader selection is unique.

Next: execute the exact BMW material slice with the selected permutation through the desktop shader-reference path and record the first real-material render evidence.


## Phase 124: D3D9 shader runtime lifecycle

The source evidence layer now covers the unified `FUN_0084f000` state flush: pixel shader `0x1ac`, vertex shader `0x170`, declaration `0x15c`, stream source `0x190` and indices `0x1a0`. Runtime JSONL capture also accepts shader-object creation/bind events and computes `SHIFT.ShaderPermutationIdentity/1` when both shader stages are captured for a frame.

Next: correlate the runtime shader identity with the exact BMW material slice and require sampler/register/constant/interface parity before accepting a real-material golden render.


## Phase 125: BMW runtime shader join

`SHIFT.BMWRuntimeShaderJoin/1` now correlates an exact BMW material slice with a captured D3D9 frame using the stable shader permutation identity and exact MEB resource identity. It also checks runtime pixel-shader sampler types against the material/external sampler contract.

Next: add constant-bank parity and declaration/vertex-input parity to this same join, then drive the joined frame into the desktop shader-reference renderer.


## Phase 126: BMW runtime parity

`SHIFT.BMWRuntimeParity/1` now combines the exact runtime shader/resource join with constant-bank parity and an explicitly evidenced declaration subset. Material `register_set=2` ranges are checked against VS/PS shader constant usage; COLOR0 property 460 is checked against a captured D3D9 Type/Usage/UsageIndex only when an explicit Usage-ordinal map is supplied.

Next: use this parity gate on the first real BMW runtime capture, then feed the accepted frame into the desktop shader-reference renderer and record the first non-synthetic image hash.


## Phase 127: runtime shader constant capture

`SHIFT.D3D9RuntimeBindingEvidence/1` now accepts `set_vertex_shader_constant_f` and `set_pixel_shader_constant_f` events with exact float4 payloads. `SHIFT.BMWRuntimeParity/1` can require exact constant-value parity against material uniforms, while source evidence records the recovered vertex constant wrapper at `0x178` and pixel constant wrapper at `0x1b4`.

Next: use a real BMW runtime trace with these events, then close the remaining declaration/VS-input parity and drive the accepted frame into the reference renderer.


## Phase 128: unified BMW runtime golden gate

`SHIFT.BMWRuntimeGoldenGate/1` is now the final readiness contract before accepting a BMW draw as golden. It combines exact shader/resource identity, sampler parity, constant register/value parity, the currently evidenced D3D9 declaration subset, and `RenderCommand/1` readiness. The gate explicitly requires a Usage-ordinal map and captured constant values.

Next: feed a concrete runtime capture into this gate. Once it is ready, execute the same command through `bmw-reference-render` and record the first real-material PPM hash.


## Phase 129: runtime trace integrity

`SHIFT.D3D9RuntimeTraceIntegrity/1` now validates object creation-before-bind ordering, pointer/byte identity reuse, and complete draw state (declaration, VS, PS, stream, indices, draw). The report is attached to `SHIFT.D3D9RuntimeBindingEvidence/1`, and the BMW runtime golden gate requires integrity `observed`.

Next: obtain a real capture and run the complete `bmw-runtime-golden-gate` -> `bmw-reference-render` sequence on an exact BMW material draw.


## Phase 130: exact BMW runtime draw correlation

`SHIFT.BMWRuntimeDrawCorrelation/1` now binds the selected BMW material primitive to exactly one captured D3D9 indexed draw by `start_index == first_index` and `primitive_count == index_count / 3`. Multiple or missing matches are blockers. `SHIFT.BMWRuntimeGoldenGate/1` consumes this correlation, so shader/resource/frame agreement is no longer sufficient by itself to accept a particular M3 submesh as golden.

Next: run the full gate against an actual runtime capture. A ready gate becomes the only allowed input to the first real-material desktop golden render and image hash recording.


## Phase 131: BMW vertex-input parity

`SHIFT.BMWVertexInputParity/1` now verifies shader `DCL` `(usage,index)` against the MEB-derived `VertexLayout/1`, then checks evidence-backed D3D9 Type/Usage/UsageIndex for mappings whose MEB Usage ordinal is known. The unified BMW golden gate consumes this result. Repacked target `Stream/Offset` values remain explicitly non-comparable to original runtime streams until direct packing capture exists.

Next: obtain one real BMW runtime capture containing declaration, VS/PS, constant writes and indexed draw events, then make that capture pass the complete `bmw-runtime-golden-gate` before generating the first real image hash.


## Phase 132: BMW MEB descriptor parity

The MEB descriptor triples now survive from resource analysis into `DrawPacket/1`, golden manifest generation, `BMWMaterialSlice/1` and runtime vertex-input parity. `SHIFT.BMWMEBDescriptorParity/1` checks exact 12-byte raw descriptor encoding against decoded `[Type, Usage, Channel]`, and the BMW vertex-input gate derives its runtime declaration expectations from those resource-derived triples.

Next: use the compact BMW descriptor snapshot with a real runtime capture to prove the remaining Usage ordinal -> D3D9 Usage byte mapping and then execute the first accepted material draw through the desktop renderer.


## Phase 133: MEB Usage ordinal bridge

`SHIFT.MEBRuntimeUsageOrdinalBridge/1` now derives MEB Usage-ordinal → D3D9 Usage-byte candidates only from exact same-resource runtime declaration observations. Type and UsageIndex must agree with the preserved MEB descriptor; multiple observed Usage bytes produce `ambiguous`, missing observations remain `unmapped`. The resulting bridge report can be supplied directly to the existing parity/golden-gate `--usage-map` input.

Next: run the bridge on a real BMW capture and promote only unique same-resource mappings. Then execute the complete `bmw-runtime-golden-gate` and reference render.


## Phase 134: D3D9 runtime capture schema

`SHIFT.D3D9RuntimeCaptureSchema/1` is now enforced at JSONL ingestion and exposed as `validate-d3d9-capture`. It validates frame/object identity fields, shader/declaration bytes, stream/draw numerics and constant vector lengths without inferring any runtime semantics. This turns the capture itself into a versioned input contract for the BMW golden pipeline.

Next: obtain one concrete BMW runtime capture through this schema, derive the Usage bridge, pass full runtime parity and run the first non-synthetic reference render.


## Phase 135: RenderCommand constant parity

`SHIFT.RenderCommandConstantParity/1` now verifies the offline c-register chain from `MaterialUniformBinding/1` through `MaterialConstantPayload/1` into `RenderCommand/1 constant_commands`. Constant-bearing commands are blocked if ranges, byte offsets or payload register presence diverge. The unified BMW runtime golden gate consumes this result.

Next: obtain the first real BMW runtime capture and run the complete gate. After a ready result, the exact RenderCommand can be handed to the desktop reference renderer for the first real-material image hash.


## Phase 136: BMW M3 paint material contract

`SHIFT.BMWM3PaintMaterialContract/1` converts the evidence-backed M3 paint chain into a machine-readable contract: `bodywork.fx`, material sampler registers s1/s2/s4, renderer-global s3/s0, exact texture names, sampler state and the documented specialization flags `USE_FRESNEL`, `ALLOW_VINYLS`, `DIRT_SCRATCH`.

Next: compare this contract directly against the material binding emitted by the real BMT/FX/FXO pipeline, then carry the exact sampler state into `RenderCommand/1` and the first golden render.


## Phase 137: BMW paint binding adapter

`bmw_m3_paint_contract.py` now normalizes the actual `draw_packets.compile_material()` shape before validating the M3 paint contract. Nested shader refs, texture `ref` paths, emitted sampler registers, selected-FXO specialization flags and external samplers are preserved without synthetic remapping.

Next: run the real `bmw_m3_e36_paint.bmt` through the full linker and require the normalized binding to pass the documented contract before generating the first real material command.


## Phase 138: enforce BMW M3 paint contract

The exact `BMW_M3_E36_PAINT.mtx` now carries `SHIFT.BMWM3PaintMaterialContract/1` validation inside `compile_material()`. The check covers `bodywork.fx`, M3 specialization flags, s1/s2/s4 material samplers, s3/s0 external samplers, texture identities, and filter/address/sRGB state. Paint-contract blockers propagate into `StaticDraw/1`.

Next: run the actual M3 BMT/FXO/texture records through this path and verify the emitted material contract without synthetic substitution. The remaining blocker is actual runtime capture for same-instance proof.


## Phase 139: BMW golden gate paint integration

`bmw_golden_gate.py` now consumes `compile_material().paint_contract` and propagates every unready paint-contract blocker into `SHIFT.BMWGoldenRenderGate/1`. The static evidence chain is therefore fail-closed from the BMW golden MEB through material binding and StaticDraw to the golden gate.

Next: run the gate on a real extracted BMW M3 resource analysis/material-binding report; no synthetic BFF content will be treated as proof.


## Phase 139: BMW paint shader gate

`SHIFT.BMWM3PaintShaderGate/1` is now part of the exact M3 paint render path. It requires unique exact FXO selection, unique VS/PS pairing, a linked shader pair, a valid permutation identity, documented sampler registers and no unresolved material textures. Heuristic or ambiguous shader selection is fail-closed and propagates into `StaticDraw/1`.

Next: run the actual BMW M3 BMT/FXO analysis output through the complete material contract without synthetic substitution; then the only remaining external proof gap is same-instance runtime capture.


## Phase 140: BMW golden shader gate

`SHIFT.BMWGoldenRenderGate/1` now consumes `paint_shader_gate` for the exact BMW M3 paint material. The gate will not accept a paint primitive unless both the evidence-backed sampler contract and unique exact FXO/VS/PS permutation identity are ready. Non-paint materials remain on the generic path.

Next: generate and validate a real M3 `MaterialBinding/1` from the extracted BFF analysis. The runtime capture remains the last external proof needed for same-instance parity.


## Phase 141: exact BMW M3 asset→paint contract

`SHIFT.BMWM3PaintAssetContract/1` now locks the exact M3 golden MEB SHA, both paint primitive ranges, the `.mtx ↔ .bmt` material alias and manifest provenance. `BMWGoldenRenderGate/1` consumes this contract only for the exact M3 golden resource, so the selected asset cannot drift while material/shader work proceeds.

Next: feed an actual M3 `MaterialBinding/1` generated from the archive analysis into the paint contract/shader gate. Current sandbox access to the 18.9 MB BFF is blocked by the Dropbox binary/text limits, so no synthetic material is being promoted as real evidence.


## Phase 142: specialization evidence bridge

The BMW M3 paint path now consumes the existing `MaterialBinding/1.specialization.requested` evidence emitted by `material_linker`, avoiding a lossy dict→keys conversion. This keeps BMT feature evidence, paint contract and shader gate on the same provenance chain.

Next: produce an actual M3 material-binding artifact from the archived BFF analysis when binary extraction is available; no synthetic permutation will be promoted.
