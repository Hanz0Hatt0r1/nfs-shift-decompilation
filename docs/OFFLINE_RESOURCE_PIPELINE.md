# Offline resource pipeline

The Process 3 tooling provides a fail-closed path from retail SHIFT resources
toward the native runtime without launching `SHIFT.exe`:

```text
BFF / ZIP / BFF directory
  -> canonical shift_importer.BFF archive parsing
  -> SHIFT.OfflineResourceCatalog/1
  -> known parser validation + neutral IR summaries
  -> SHIFT.OfflineResourceDependencyGraph/1
  -> SHIFT.SceneVehicleBootstrap/1
  -> SHIFT.TypedResourceClosure/1
  -> existing vehicle physics asset graph
  -> SHIFT.VehiclePhysicsResourceManifest/1
  -> static scene IR / exact scene-resource closure
  -> SHIFT.OfflineNativeSceneBuild/1
  -> SHIFT.OfflineNativeVehicleBuild/1
  -> SHIFT.OfflineRuntimeBootstrap/1
  -> SHIFT.OfflineNativeRuntimeRequirements/1
  -> SHIFT.OfflineNativeVerticalSliceProfilePrepare/1
  -> optional SHIFT.NativeVerticalSliceLaunchPlan/1 validation
```

`tools/shift_resource_pipeline.py` owns the catalog/dependency/bootstrap layer.
`tools/bootstrap_runtime.py` continues through the strongest currently proven
offline native scene/vehicle bootstrap. `tools/bootstrap_native_vertical_slice.py`
adds runtime-requirement accounting, profile preparation, and optional validation
through the existing native vertical-slice launcher.

None of these commands executes the original game or starts the native runtime.

## Evidence boundaries

The pipeline is deliberately fail-closed.

- Archive structure and payload decoding use `shift_importer.BFF`.
- Unknown resource extensions are indexed but are not assigned invented layouts.
- Admission dependency edges come only from semantic parsers/contracts already
  present in the repository.
- For SGB, `NODE`/`SUMM`/`OCCL` resource fields decoded by the source-backed
  `sgb_runtime` contract may become admissible exact dependency edges only when
  that decode is fully ready. Remaining string-scan SGB candidates stay
  diagnostic-only and cannot satisfy an admission gate.
- Resource lookup is exact normalized path. There is no basename fallback in the
  admission graph or the external SGB exact-closure preflight.
- `.mtx <-> .bmt` is the only accepted alias and is recorded explicitly as the
  existing known legacy material alias.
- Missing shaders/resources remain unresolved. Nothing is synthesized.
- A resource-ready bootstrap does not bypass the existing native render,
  physics, runtime-evidence, or provenance gates.
- Static SGB render bindings are not promoted to runtime draw proof. A
  runtime-proven native scene set remains a separate gate.
- Structural participant ABI evidence is not promoted to a concrete participant
  identity. An optional existing `SHIFT.NativePhysicsParticipantObservation/1`
  is joined only through the exact participant-runtime-evidence contract.
- The current native physics compatibility manifest is emitted only for exact
  `BMW_M3_E36.bff` identity. Other vehicle manifests remain neutral rather than
  being relabeled as BMW.
- Profile preparation never creates camera, BODY-feedback, input, scene, or
  participant evidence. Missing runtime requirements must be supplied explicitly.
- Optional launch-plan validation delegates to `tools/run_native_vertical_slice.py`;
  Process 3 does not duplicate or weaken its format, packet-magic, path, or
  input/frame consistency checks.

## Resource-pipeline commands

Inventory only:

```bash
python tools/shift_resource_pipeline.py catalog \
  Vehicles.zip Silverstone_Era3_.zip \
  -o out/offline-resource-catalog
```

Corpus validation with every currently supported generic parser:

```bash
python tools/shift_resource_pipeline.py catalog \
  Vehicles.zip Silverstone_Era3_.zip \
  -o out/offline-resource-validation \
  --decode-known
```

`--decode-limit-per-archive N` provides a reproducible bounded smoke run. `0`
(the default) means the complete known-format corpus.

Build a bootstrap from previously generated catalog/graph files:

```bash
python tools/shift_resource_pipeline.py bootstrap \
  out/offline-resource-validation/resource_catalog.json \
  out/offline-resource-validation/dependency_graph.json \
  --track Silverstone_Era3_GrandPrix \
  --vehicle Ford_Mustang_2010 \
  -o out/offline-resource-validation/bootstrap_manifest.json \
  --admission out/offline-resource-validation/native_admission.json
```

Run catalog + validation + selected track/vehicle bootstrap + native resource
handoff in one command:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle Ford_Mustang_2010
```

The `all` command also writes corpus-wide target-readiness diagnostics. Blockers
for unrelated track/vehicle targets remain diagnostic and do not override the
readiness of the explicitly selected pair.

Without a runtime-proven scene set the scene side of the native-resource handoff
intentionally remains blocked, while the neutral vehicle physics resource
manifest can still be generated. For the current BMW vertical slice, an existing
scene set can be joined explicitly:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --scene-set out/native-scene-vulkan \
  --require-native-resource-handoff
```

`--require-native-resource-handoff` changes only the command exit gate. It does
not claim camera, participant, BODY-feedback, provider-scheduling, input, or full
runtime readiness.

The standalone `native-handoff` subcommand remains available for rebuilding the
join without re-decoding the BFF corpus.

When `RENDER.bff` is not supplied, exact `.fx` dependencies referenced by
materials remain visible as unresolved blockers. The pipeline must return
blocked rather than silently substituting an FXO or synthesized shader.

## Native bootstrap commands

Build the strongest offline native bootstrap directly from retail inputs:

```bash
python tools/bootstrap_runtime.py \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/runtime-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36
```

This command automatically builds the resource pipeline, track/vehicle loads,
scene IR, static native scene resource binding, native vehicle resource build,
and `runtime_requirements.json`. It may report
`offline-native-build-ready-runtime-gated`; that is not a runtime-ready claim.

An existing participant observation can be joined without changing the resource
readiness boundary:

```bash
python tools/bootstrap_runtime.py \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/runtime-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --participant-observation evidence/native_physics_participant_observation.json
```

`runtime_requirements.json` records which vertical-slice inputs are already
satisfied by exact bootstrap artifacts and which still require external proven
evidence. It never synthesizes a missing requirement.

Prepare a vertical-slice profile from an existing requirements report:

```bash
python tools/prepare_native_vertical_slice_profile.py \
  out/runtime-bootstrap/runtime_requirements.json \
  --workspace-root . \
  -o out/runtime-bootstrap/vertical_slice_profile.json \
  --scene-set out/native-scene-vulkan \
  --camera-state out/native-camera-state.json \
  --solver-frame out/solver.sbfr \
  --generated-body-constraint-frame out/generated.gbcf \
  --constraint-sample-relation-frame out/relations.csrf \
  --constraint-relation-reset-frame out/reset.crrf \
  --post-solve-projection out/post.sbps \
  --keyboard --frames 120 \
  --validate-launch-plan
```

Exact physics/participant artifacts already proven by the requirements report
are auto-filled. An explicit conflicting replacement is rejected, all profile
paths are confined to the chosen workspace, and a stale profile/launch plan is
removed when the current preparation is blocked.

The same chain is available from retail inputs in one command:

```bash
python tools/bootstrap_native_vertical_slice.py \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/native-vertical-slice \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root . \
  --participant-observation evidence/native_physics_participant_observation.json \
  --scene-set out/native-scene-vulkan \
  --camera-state out/native-camera-state.json \
  --solver-frame out/solver.sbfr \
  --generated-body-constraint-frame out/generated.gbcf \
  --constraint-sample-relation-frame out/relations.csrf \
  --constraint-relation-reset-frame out/reset.crrf \
  --post-solve-projection out/post.sbps \
  --keyboard --frames 120 \
  --validate-launch-plan
```

The one-command path refuses to prepare a profile when the selected offline
track/vehicle bootstrap itself is blocked, even if all later runtime paths are
supplied explicitly. `--validate-launch-plan` performs validation only; it does
not execute `native_runtime/build/shift_runtime`.

## Outputs

`shift_resource_pipeline.py all` writes, among other artifacts:

- `resource_catalog.json` — archive and entry identity, category, compression,
  decoded status and hashes;
- `dependency_graph.json` — semantic dependency edges plus diagnostic-only
  non-admissible edges;
- `coverage_report.json` — parsed/blocked/unsupported counts, unknown
  extensions/layouts and parser failures;
- `bootstrap_corpus_validation.json` — exact track/vehicle target candidates,
  loader readiness, and target-level blockers across the available corpus;
- `scene_vehicle_bootstrap.json` — exact selected track/vehicle archives and
  required root resource identities;
- `typed_resources/` + `typed_resource_closure.json` — decoded bytes for the
  resolved semantic closure; unresolved dependencies are not materialized;
- `vehicle_physics/vehicle_physics_asset_graph.json` — produced by the existing
  vehicle physics asset-graph path for the selected vehicle;
- `native-handoff/vehicle_physics_resource_manifest.json` — exact neutral
  vehicle BFF/physics identity join;
- `native-handoff/native_physics_manifest.json` — current native-runtime BMW
  compatibility manifest when the exact BMW gate is satisfied;
- `native-handoff/scene_catalog_join.json` — existing runtime-proven scene IMB
  identities joined back to the exact offline catalog when `--scene-set` is
  supplied;
- `native-handoff/native_resource_handoff.json` — combined native resource-input
  admission state;
- `native_runtime_admission.json` — explicit resource/runtime gate state;
- `pipeline_run.json` — top-level reproducibility record including native-resource
  handoff and corpus target-readiness diagnostics.

`bootstrap_runtime.py` additionally writes nested scene/vehicle build artifacts,
`runtime_bootstrap.json`, and `runtime_requirements.json`.

`bootstrap_native_vertical_slice.py` writes:

- `runtime-bootstrap/` — the complete `bootstrap_runtime` artifact tree;
- `runtime_requirements.json` — exact satisfied/missing runtime gates;
- `vertical_slice_profile.prepare.json` — profile admission result;
- `vertical_slice_profile.json` — only when the profile is complete;
- `launch_plan.json` — only when optional launcher validation succeeds;
- `vertical_slice_bootstrap.json` — top-level status separating offline bootstrap,
  profile, and launch-plan readiness.

See `docs/OFFLINE_NATIVE_RESOURCE_HANDOFF.md` and
`docs/PHASE649_NATIVE_VERTICAL_SLICE_LAUNCH.md` for the exact downstream join and
launcher contracts.

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
