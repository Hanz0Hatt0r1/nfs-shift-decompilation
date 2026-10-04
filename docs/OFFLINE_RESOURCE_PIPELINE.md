# Offline resource pipeline

`tools/shift_resource_pipeline.py` is the high-level offline path from retail BFF
inputs toward the native runtime:

```text
BFF / ZIP / directory
  -> canonical shift_importer.BFF archive parsing
  -> SHIFT.OfflineResourceCatalog/1
  -> known parser validation + neutral IR summaries
  -> SHIFT.OfflineResourceDependencyGraph/1
  -> SHIFT.SceneVehicleBootstrap/1
  -> SHIFT.TypedResourceClosure/1
  -> existing vehicle physics asset graph
  -> SHIFT.VehiclePhysicsResourceManifest/1
  -> optional runtime-proven scene-set/catalog join
  -> SHIFT.OfflineNativeResourceHandoff/1
  -> SHIFT.OfflineResourceRuntimeAdmission/1
```

The tool never launches `SHIFT.exe`.

## Evidence boundaries

The pipeline is deliberately fail-closed.

- Archive structure and payload decoding use `shift_importer.BFF`.
- Unknown resource extensions are indexed but are not assigned invented layouts.
- Admission dependency edges come only from source-backed semantic parsers.
- Source-backed ready SGB record fields may close exact dependency edges; legacy
  SGB string-scan observations remain diagnostic-only.
- Resource lookup is exact normalized path. There is no basename fallback in the
  dependency graph.
- `.mtx <-> .bmt` is the only accepted alias and is recorded explicitly as the
  existing known legacy material alias.
- Missing shaders/resources remain unresolved. Nothing is synthesized.
- A resource-ready bootstrap does not bypass native render, physics,
  runtime-evidence, or provenance gates.
- Byte/hash duplicate reports prove only path/byte equivalence. They do not prove
  semantic resource identity.

`SHIFT.SceneVehicleBootstrap/1` still uses the requested archive filename to form
its corpus candidate set. That candidate name is not sufficient proof for the
first playable native target. `SHIFT.OfflineRuntimeBootstrap/1` now inserts the
separate `SHIFT.RetailArchiveIdentityAdmission/1` gate before native scene or
vehicle consumers.

For the selected Silverstone + BMW vertical slice that gate requires full retail
SHA-256 identity and exactly one catalog occurrence for:

```text
Silverstone_Era3_GrandPrix.bff
Silverstone_Era3_GrandPrix_Physics.bff
BMW_M3_E36.bff
BMW_M3_E36_Cockpit.bff
```

The identities are centralized in `src/resources/retail_archive_identity.py`.
Unknown target names do not fall back to name-only native admission. Two exact
byte-identical occurrences remain ambiguous; archive order and first-match
selection are never proof.

The later Phase 644 playable scene bootstrap applies the same policy to the BMW
primary/cockpit archives plus `RENDER.bff` before material/Vulkan scene
composition.

### Persistent typed physics resource paths

The unified `SHIFT.OfflineRuntimeBootstrap/1` passes its existing
`SHIFT.TypedResourceClosure/1` into the native-vehicle resource stage. The
existing `SHIFT.VehiclePhysicsResourceManifest/1` is enriched in place; no new
coordination report or resource identity is introduced.

For each selected CDF/EDF/GDF/SDF/TBF/BBF entry, a persistent decoded path is
admitted only after all of the following match exactly:

```text
resource_id
+ normalized retail path
+ manifest decoded SHA-256
+ typed-closure decoded SHA-256
+ typed-closure identity_match = true
+ current materialized file SHA-256
```

The admitted entry then exposes:

```text
materialized_path
materialized_sha256
materialization_source = SHIFT.TypedResourceClosure/1
```

A missing file, hash drift, duplicate resource ID, path mismatch, or typed
closure ambiguity blocks native vehicle resource readiness. Basename fallback,
archive order, first duplicate, and resource similarity are not used.

For the selected BMW target the unified runtime bootstrap additionally surfaces
the already-admitted SDF file as:

```text
artifacts.vehicle_sdf
```

This is a resource handoff only. It makes the exact decoded retail SDF available
to Process 1/2 without another extraction command, but it does **not** claim
BODY0 identity, BODY bind semantics, SDF-model -> VHF frame relation, provider
identity, scheduling, or vehicle-world-transform readiness.

### Persistent selected vehicle archive

`SHIFT.OfflineNativeVehicleBuild/1` now also preserves the exact selected primary
vehicle BFF when the catalog carries real source provenance. This removes the
manual `Vehicles.zip -> BMW_M3_E36.bff` extraction step for downstream proof or
runtime consumers that still require an archive path.

The materializer follows only the catalog-selected archive occurrence:

- ZIP input: the exact recorded `source_member` is reopened; same-basename ZIP
  members are never searched or substituted;
- direct BFF input: the exact recorded source file is copied;
- directory input: candidate files must match both the selected archive name and
  SHA-256, and exactly one hit is required.

In every case the bytes and size are reverified before the persistent artifact is
admitted. Hash drift, missing source provenance, or a byte-identical duplicate
occurrence blocks the archive handoff. Archive order and first-match selection
are never used.

The existing native-vehicle build report exposes the result as:

```text
vehicle_archive_materialization
artifacts.vehicle_archive.path
artifacts.vehicle_archive.sha256
```

For the unified playable path, canonical retail identity is still proved by the
separate `SHIFT.RetailArchiveIdentityAdmission/1` gate. Archive materialization
does not rederive or replace that proof, and it does not claim BODY semantics,
participant identity, provider identity, scheduling, or vehicle transforms.

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

Build a catalog-level bootstrap from previously generated catalog/graph files:

```bash
python tools/shift_resource_pipeline.py bootstrap \
  out/offline-resource-validation/resource_catalog.json \
  out/offline-resource-validation/dependency_graph.json \
  --track Silverstone_Era3_GrandPrix \
  --vehicle Ford_Mustang_2010 \
  -o out/offline-resource-validation/bootstrap_manifest.json \
  --admission out/offline-resource-validation/native_admission.json
```

This subcommand is useful for corpus diagnostics, but a filename-selected
candidate is not by itself playable-native admission proof.

Run the complete offline resource orchestration in one command:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36
```

The `all` command also runs the native-resource handoff stage. Without a
runtime-proven scene set the scene side intentionally remains blocked, but the
neutral vehicle physics resource manifest is still generated. An existing scene
set can be joined in the same command:

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
not claim camera, participant, BODY-feedback, provider scheduling, or full
runtime readiness.

When `RENDER.bff` is not supplied, exact `.fx` dependencies referenced by
Silverstone/BMW material evidence remain visible as blockers where the consuming
stage requires them. The pipeline must not silently substitute an FXO or invented
shader.

## Outputs

The resource pipeline writes:

- `resource_catalog.json` — archive/entry provenance, compression, parse status,
  and content hashes;
- `dependency_graph.json` — admissible semantic dependency edges plus explicit
  diagnostic-only observations;
- `coverage_report.json` — parsed/blocked/unsupported/deferred counts and parser
  failures;
- `scene_vehicle_bootstrap.json` — selected archive candidates and required root
  resource IDs;
- `typed_resources/` + `typed_resource_closure.json` — decoded bytes for the
  resolved semantic closure;
- `vehicle_physics/vehicle_physics_asset_graph.json` — existing source-backed
  vehicle physics asset graph;
- `native-handoff/vehicle_physics_resource_manifest.json` — exact neutral
  vehicle BFF/physics identity join;
- `native-handoff/native_resource_handoff.json` — combined native resource-input
  admission state;
- `native_runtime_admission.json` — explicit resource/runtime gate state;
- `pipeline_run.json` — compact top-level reproducibility record.

The one-command `offline_runtime_bootstrap` additionally writes
`retail_archive_identity_admission.json`; its readiness is now a required input
to both static native scene and native vehicle admission. In that unified path,
`native-vehicle/vehicle_physics_resource_manifest.json` also carries the exact
persistent decoded paths described above, `runtime_bootstrap.json` exposes
`artifacts.vehicle_sdf`, and `native-vehicle/native_vehicle_build.json` exposes
the persistent exact selected vehicle BFF through `artifacts.vehicle_archive`.

See `docs/OFFLINE_NATIVE_RESOURCE_HANDOFF.md` for downstream join contracts and
non-claims.

## Current corpus intake

The established corpus inventory contains:

| Source | BFFs | Entries | Type 2 | Type 0 |
| --- | ---: | ---: | ---: | ---: |
| `Vehicles.zip` | 12 | 12,447 | 12,429 | 18 |
| `Silverstone_Era3_.zip` | 8 | 14,387 | 14,361 | 26 |

Notable entry counts include 1,086 vehicle `.meb` resources and 427 Silverstone
`.imb` resources. The four Silverstone physics archives each expose one AIW and
one CSM root; the four visual archives each expose one SGB/TRD/LSD root. Those
counts are corpus diagnostics, not identity-selection heuristics.

`shift.zip` is a Ghidra project export rather than a retail BFF corpus.
`SHIFT_tail.zip` contains split raw tail parts rather than standalone BFF members,
so neither input is counted as a BFF source by this pipeline.

## Real-corpus regression hook

Copyrighted retail archives are not committed. A real-corpus regression is
available when the caller supplies paths:

```bash
SHIFT_REAL_VEHICLES_ZIP=/path/to/Vehicles.zip \
SHIFT_REAL_SILVERSTONE_ZIP=/path/to/Silverstone_Era3_.zip \
pytest -q tests/test_offline_resource_pipeline_real_corpus.py
```

Ordinary CI skips this test when those environment variables are absent.
