# Offline resource pipeline

Process 3 is the fail-closed path from retail SHIFT resources to the strongest
currently provable native scene/vehicle bootstrap. It does not launch
`SHIFT.exe` and does not require a new runtime capture.

```text
BFF / ZIP / BFF directory
  -> canonical shift_importer.BFF extraction
  -> SHIFT.OfflineResourceCatalog/1
  -> known parser validation + neutral summaries
  -> SHIFT.OfflineResourceDependencyGraph/1
  -> exact load_track / load_vehicle selection
  -> SHIFT.SceneVehicleBootstrap/1
  -> SHIFT.TypedResourceClosure/1
  -> scene IR materialization
  -> exact SGB scene resource closure
  -> SHIFT.OfflineNativeSceneBuild/1
  -> vehicle physics resource manifest
  -> SHIFT.NativePhysicsParticipantBoundary/1
  -> SHIFT.OfflineNativeVehicleBuild/1
  -> SHIFT.OfflineRuntimeBootstrap/1
```

The native-runtime boundary remains explicit. A static/resource-complete build
is not automatically a runtime-ready scene or vehicle.

## Evidence and fail-closed rules

- Archive layout, compression/encryption metadata, entry offsets and extraction
  use `shift_importer.BFF`.
- Resource identity is archive provenance + logical path + entry identity +
  decoded/stored hashes. Duplicate normalized paths and duplicate payload
  identities remain explicit; they are not silently collapsed.
- Unknown resource extensions are indexed but are not assigned invented layouts.
- Parser failures remain blocked. Unknown layouts are not heuristically decoded.
- Admission dependency edges come only from concrete semantic parsers.
- Source-backed SGB runtime decoding exposes exact `NODE`, `SUMM` and `OCCL`
  `resource` fields. They are admissible only when the SGB runtime decoder is
  ready. Legacy SGB arbitrary string-scan references remain diagnostic-only.
- MEB/IMB/IMX material references and BMT shader/texture references come from
  their existing parsers/neutral adapters.
- Resource lookup in admission paths uses exact normalized logical paths. There
  is no basename fallback.
- `.mtx <-> .bmt` is the known material alias; alias use remains explicit.
- Missing shaders/resources remain unresolved. No similar file is substituted.
- Tied FXO candidates are not selected without exact runtime admission evidence.
- Static RenderBinding is not promoted to runtime draw proof.
- Generic vehicle resources are not promoted to a concrete runtime participant.
- `SHIFT.NativePhysicsParticipantBoundary/1` proves the current participant
  registry/selector/process structural ABI only. It does not invent registry
  index, selector ordinal, participant instance, provider identity, input
  binding or fixed-step scheduling.

## Main commands

### Catalog and raw corpus validation

Inventory only:

```bash
python tools/shift_resource_pipeline.py catalog \
  Vehicles.zip Silverstone_Era3_.zip \
  -o out/offline-resource-catalog
```

Run every currently supported generic parser:

```bash
python tools/shift_resource_pipeline.py catalog \
  Vehicles.zip Silverstone_Era3_.zip \
  -o out/offline-resource-validation \
  --decode-known
```

`--decode-limit-per-archive N` provides a reproducible bounded smoke run. `0`
(the default) means the complete known-format corpus.

The coverage report records total/supported/verified/blocked/unsupported/deferred
resources, unresolved dependency edges and the currently explicit malformed /
unknown-layout classifications. It does not infer failure classes from exception
text.

### Exact high-level loaders

Build exact track/vehicle load contracts from an existing catalog and graph:

```bash
python tools/shift_resource_pipeline.py load-track \
  out/offline-resource-validation/resource_catalog.json \
  out/offline-resource-validation/dependency_graph.json \
  --track Silverstone_Era3_GrandPrix \
  -o out/track_load.json

python tools/shift_resource_pipeline.py load-vehicle \
  out/offline-resource-validation/resource_catalog.json \
  out/offline-resource-validation/dependency_graph.json \
  --vehicle BMW_M3_E36 \
  -o out/vehicle_load.json
```

These loaders require exact archive/root identities and fail on blocked required
roots or unresolved admissible dependencies.

### Selected resource bootstrap

```bash
python tools/shift_resource_pipeline.py bootstrap \
  out/offline-resource-validation/resource_catalog.json \
  out/offline-resource-validation/dependency_graph.json \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  -o out/bootstrap_manifest.json \
  --admission out/native_admission.json
```

### Complete legacy resource orchestration

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36
```

`all` runs catalog/validation/graph/bootstrap, materializes the selected typed
closure, extracts the vehicle physics graph, builds the existing native resource
handoff, and now writes `bootstrap_corpus_validation.json`.

The corpus target report is diagnostic-only for this command. A different
blocked track or vehicle in the same corpus cannot make the explicitly selected
track/vehicle pair fail.

An existing runtime-proven native scene set may be joined explicitly:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --scene-set out/native-scene-vulkan \
  --require-native-resource-handoff
```

`--require-native-resource-handoff` changes the command exit gate only. It does
not claim participant identity, input/fixed-step orchestration or full runtime
readiness.

### Corpus-wide target readiness

Validate exact high-level targets after catalog generation:

```bash
python tools/validate_bootstrap_corpus.py \
  out/offline-pipeline/resource_catalog.json \
  out/offline-pipeline/dependency_graph.json \
  -o out/offline-pipeline/bootstrap_corpus_validation.json
```

Track candidates are discovered only from exact `<stem>.bff +
<stem>_Physics.bff` pairs. Vehicle candidates use the existing CDF+EDF physics
corpus admission convention. Candidate discovery never implies readiness; each
candidate is passed through `load_track` or `load_vehicle`.

### Scene IR and native scene resources

Materialize renderer-facing IR from BFF/ZIP/directory inputs:

```bash
python tools/build_scene_ir.py \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/scene-ir
```

The wrapper uses existing `shift_importer build-ir` decoding/materialization,
including IMB/IMX inputs. Legacy dependency hints inside that IR are diagnostic;
they are not resource-identity admission proof.

Build one source-backed static SGB scene resource artifact:

```bash
python tools/build_native_scene.py \
  path/to/selected_scene.sgb \
  out/scene-ir \
  -o out/native-scene
```

The builder automatically runs the already-proven chain:

```text
raw SGB
-> SGB runtime decode
-> FLAT/SUMM + PART/NODE placement joins
-> scene placement
-> OBJECT render handoffs/transforms
-> render binding admission
-> exact IR resource closure
-> static RenderBinding bridge
```

Optional existing MultiMatrix root consensus and exact runtime shader admission
may be supplied. The builder stops before runtime draw admission;
`native_scene_runtime_ready` therefore remains false unless a future proven
runtime-scene stage explicitly closes that gate.

### Native vehicle resources

```bash
python tools/build_native_vehicle.py \
  out/offline-pipeline/resource_catalog.json \
  out/offline-pipeline/scene_vehicle_bootstrap.json \
  out/offline-pipeline/vehicle_physics_bundle_report.json \
  -o out/native-vehicle
```

This emits:

- generic `SHIFT.VehiclePhysicsResourceManifest/1`;
- `SHIFT.NativePhysicsParticipantBoundary/1` structural participant contract;
- the current BMW-specific native physics compatibility manifest only when the
  exact BMW gate is satisfied;
- `SHIFT.OfflineNativeVehicleBuild/1`.

`participant_structural_ready` is part of offline vehicle readiness. Concrete
participant instance/registry identity is still a runtime gate.

### One-command Process 3 bootstrap

The highest-level Process 3 entry point is:

```bash
python tools/bootstrap_runtime.py \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/runtime-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36
```

It composes:

```text
resource pipeline
+ exact load_track/load_vehicle
+ scene IR materialization
+ exact selected SGB typed root
+ native static scene build
+ native vehicle resource build
+ structural participant boundary
-> SHIFT.OfflineRuntimeBootstrap/1
```

The top-level report separates:

- `offline_build_ready`: every currently provable offline/native resource stage
  required by this path is ready;
- `runtime_ready`: runtime scene draw admission and vehicle runtime identity /
  orchestration are both proven ready.

`--require-runtime-ready` returns non-zero until those runtime-only gates are
actually proven. It never converts static readiness into runtime proof.

Optional existing evidence:

```text
--root-consensus <SHIFT.SGBMultiMatrixRootConsensus/1>
--runtime-shader-admission <exact runtime shader admission JSON>
```

## Main outputs

The standard resource pipeline writes:

- `resource_catalog.json` — archive/resource identity, offsets, compression,
  encryption, hashes, decoded status and duplicate identities;
- `dependency_graph.json` — admissible semantic edges plus retained
  diagnostic-only observations;
- `coverage_report.json` — raw parser/corpus support and blocker statistics;
- `bootstrap_corpus_validation.json` — high-level track/vehicle target readiness
  and blocker frequencies;
- `scene_vehicle_bootstrap.json` — exact selected archive/root identities;
- `typed_resources/` + `typed_resource_closure.json` — decoded selected semantic
  closure with source provenance;
- `vehicle_physics/vehicle_physics_asset_graph.json` and
  `vehicle_physics_bundle_report.json`;
- `native_runtime_admission.json` — explicit resource/runtime admission state;
- `native-handoff/*` — existing native resource handoff artifacts;
- `pipeline_run.json` — top-level reproducibility record.

`bootstrap_runtime.py` additionally creates:

- `track_load.json` and `vehicle_load.json`;
- `scene-ir/scene_ir_materialization.json` + materialized renderer IR;
- `native-scene/native_scene_build.json` and intermediate scene contracts;
- `native-vehicle/vehicle_physics_resource_manifest.json`;
- `native-vehicle/native_physics_participant_boundary.json`;
- optional `native-vehicle/native_physics_manifest.json` when the current exact
  runtime compatibility gate is satisfied;
- `native-vehicle/native_vehicle_build.json`;
- `runtime_bootstrap.json`.

## Current runtime gates

A resource-complete Process 3 build still does not imply the game can execute the
selected scene/vehicle. Important remaining gates are intentionally external to
this process:

- runtime-proven scene draw admission / final native scene-set production;
- exact participant registry/selector instance identity;
- participant/provider admission where required by the native runtime;
- input binding and fixed-step scheduling;
- broader runtime lifecycle integration.

Renderer evidence tooling may consume already-existing capture/report bundles,
but an audit/frontier report is not treated as a native scene admission artifact.

## Current attached corpus intake

The attached corpus used while introducing this pipeline contains:

| Source | BFFs | Entries | Type 2 | Type 0 |
| --- | ---: | ---: | ---: | ---: |
| `Vehicles.zip` | 12 | 12,447 | 12,429 | 18 |
| `Silverstone_Era3_.zip` | 8 | 14,387 | 14,361 | 26 |

Notable exact entry counts:

- vehicle corpus: 9,934 `.fxo`, 1,086 `.meb`, 833 `.dds`, 411 `.bmt`,
  six each of `.cdf/.cgp/.csd/.cdp/.cdv/.edf/.gdf/.sdf/.tbf`, and four `.bbf`;
- Silverstone corpus: 6,071 `.meb`, 3,748 `.fxo`, 2,015 `.dds`, 1,303 `.bmt`,
  585 `.vhf`, 427 `.imb`, four each of `.sgb/.trd/.lsd/.aiw/.csm`.

The four Silverstone physics archives each expose one exact AIW and one exact
CSM root. The four visual archives each expose one SGB/TRD/LSD root. This makes
archive/root selection deterministic without guessing resource layout.

`shift.zip` is a Ghidra project export rather than a retail BFF corpus.
`SHIFT_tail.zip` contains split raw tail parts (`.aa` ... `.af`) rather than
standalone BFF members, so neither input is counted as a BFF source.

## Real-corpus regression hook

Copyrighted retail archives are not committed. A real-corpus regression is
available when the caller supplies paths:

```bash
SHIFT_REAL_VEHICLES_ZIP=/path/to/Vehicles.zip \
SHIFT_REAL_SILVERSTONE_ZIP=/path/to/Silverstone_Era3_.zip \
pytest -q tests/test_offline_resource_pipeline_real_corpus.py
```

Ordinary CI skips this test when those environment variables are absent.