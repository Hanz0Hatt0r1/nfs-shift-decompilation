# Offline resource pipeline

`tools/shift_resource_pipeline.py` is the high-level offline path from retail BFF
inputs toward the native runtime:

```text
BFF / ZIP
  -> canonical shift_importer.BFF archive parsing
  -> SHIFT.OfflineResourceCatalog/1
  -> known parser validation + neutral IR summaries
  -> SHIFT.OfflineResourceDependencyGraph/1
  -> SHIFT.SceneVehicleBootstrap/1
  -> SHIFT.TypedResourceClosure/1
  -> existing vehicle physics asset graph
  -> SHIFT.OfflineResourceRuntimeAdmission/1
```

The tool never launches `SHIFT.exe`.

## Evidence boundaries

The pipeline is deliberately fail-closed.

- Archive structure and payload decoding use `shift_importer.BFF`.
- Unknown resource extensions are indexed but are not assigned invented layouts.
- Admission dependency edges come only from semantic parsers already present in
  the repository (`BMT`, `MEB`, `IMB`, `VHF`).
- `SGB` currently exposes string-scan resource references. Those references are
  retained as diagnostic-only edges and cannot satisfy an admission gate.
- Resource lookup is exact normalized path. There is no basename fallback in the
  admission graph.
- `.mtx <-> .bmt` is the only accepted alias and is recorded explicitly as the
  existing known legacy material alias.
- Missing shaders/resources remain unresolved. Nothing is synthesized.
- A resource-ready bootstrap does not bypass the existing native render,
  physics, runtime-evidence, or provenance gates.

## Commands

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

Run the complete orchestration in one command:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle Ford_Mustang_2010
```

When `RENDER.bff` is not supplied, exact `.fx` dependencies referenced by
Silverstone BMT materials remain visible as unresolved blockers. The command
must return blocked rather than silently substituting an FXO or synthesized
shader.

## Outputs

`all` writes:

- `resource_catalog.json` — archive and entry identity, category, compression,
  decoded status and hashes;
- `dependency_graph.json` — semantic dependency edges plus diagnostic-only
  non-admissible edges;
- `coverage_report.json` — parsed/blocked/unsupported counts, unknown
  extensions/layouts and parser failures;
- `scene_vehicle_bootstrap.json` — exact track/vehicle archive selection and required
  root resource identities;
- `typed_resources/` + `typed_resource_closure.json` — decoded bytes for the
  resolved semantic closure; unresolved dependencies are not materialized;
- `vehicle_physics/vehicle_physics_asset_graph.json` — produced by the existing
  `vehicle_physics_bundle.py` path for the selected vehicle;
- `native_runtime_admission.json` — explicit resource/runtime gate state;
- `pipeline_run.json` — compact top-level reproducibility record.

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
