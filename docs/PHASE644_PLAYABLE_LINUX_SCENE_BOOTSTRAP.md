# Phase 644 — one-command playable Linux scene bootstrap

## Playable-slice blocker reduced

Phase 643 proved that an already-prepared Silverstone `SHIFT.NativeSceneVulkanSet/1`
and the canonical BMW M3 body can coexist in one neutral scene-set without
changing the native runtime ABI. Phase 644 removed the remaining manual vehicle
render handoff: the caller no longer has to prepare a BMW material-slice set or
pass individual BMW/renderer BFF paths.

The current path is:

```text
retail corpus inputs
  -> offline resource/bootstrap
  -> prepared Silverstone scene-set
  -> exact retail BMW/renderer archive admission
  -> Phase 533 complete BMW body material admission
  -> Phase 645 VHF body world transform
  -> Phase 643 Silverstone + BMW neutral composition
  -> runtime requirements/profile
```

No original game execution and no new runtime capture are introduced.

## Exact retail archive identity

`src/scene/native_playable_scene_bootstrap.py` emits:

```text
SHIFT.NativePlayableSceneBootstrap/1
```

It reuses `offline_resource_pipeline.materialize_bff_inputs()` and therefore
accepts `.bff`, `.zip`, and directory corpus inputs. Basenames are now discovery
hints only; they are not resource identity proof.

The current BMW/render inputs are admitted only when both the canonical archive
name and full source-backed retail SHA-256 match:

| Archive | SHA-256 |
| --- | --- |
| `BMW_M3_E36.bff` | `c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70` |
| `BMW_M3_E36_Cockpit.bff` | `a9bc1b3c0dfb21408913089d565fa2ffc80f2fb2c4a408ab9aef101d012f15be` |
| `RENDER.bff` | `b0b03960ba7e620b7ad5e2b027ed13de67afffe168eb8b30da73c2a632a7c0af` |

The identities live in `src/resources/retail_archive_identity.py` and cite the
existing repository retail evidence. Admission additionally requires exactly one
matching materialized corpus occurrence.

This is intentionally stricter than byte equality:

- archive order is never selection authority;
- first-match fallback is forbidden;
- basename-only admission is forbidden;
- a same-name wrong-hash archive is rejected;
- two occurrences with the same canonical name and the same bytes remain
  ambiguous rather than being collapsed into one semantic identity.

The emitted `archive_sources` records include the admitted SHA-256 plus original
ZIP/directory provenance. Temporary extraction paths are not exposed as identity.

## Earlier native-bootstrap gate

The resource-driven native bootstrap now also emits:

```text
SHIFT.RetailArchiveIdentityAdmission/1
```

before native scene or native vehicle admission. For the first playable target it
requires one exact catalog occurrence for:

```text
Silverstone_Era3_GrandPrix.bff
Silverstone_Era3_GrandPrix_Physics.bff
BMW_M3_E36.bff
BMW_M3_E36_Cockpit.bff
```

with the retail hashes recorded in `retail_archive_identity.py`. The corresponding
Silverstone hashes are:

```text
Silverstone_Era3_GrandPrix.bff
  aac2e1fe721aec25494d0bfc84eac2bd49d1628fe55b165097ae694ef7a7d56c
Silverstone_Era3_GrandPrix_Physics.bff
  b90b70a1965260599570efef5bce4a76e5f96732c9831e6614e8541b886edbd7
```

A legacy `SHIFT.SceneVehicleBootstrap/1` name match can still exist as a catalog
candidate, but it cannot make `SHIFT.OfflineRuntimeBootstrap/1` ready unless this
retail identity gate succeeds. Unknown track/vehicle targets have no implicit
name-only fallback into the playable native path.

## Vehicle render materialization

The admitted archives feed the existing Phase 533 material path:

```text
BMW_M3_E36.bff
+ BMW_M3_E36_Cockpit.bff
+ RENDER.bff
+ canonical BMW body golden manifest
-> SHIFT.BMWBodyMaterialAdmission/1
-> complete SHIFT.BMWMaterialSliceSet/1
```

All selected canonical body primitives must be ready. Partial material admission
is diagnostic only and cannot seed the playable scene. The material slice then
receives the Phase 645 source-backed VHF transform before Phase 643 rebuilds the
neutral vehicle draw bundles.

## Playable entry point

The high-level command remains:

```text
tools/bootstrap_playable_linux_slice.py
```

Example shape:

```bash
python tools/bootstrap_playable_linux_slice.py \
  Vehicles.zip Silverstone_Era3_.zip SHIFT_tail.zip \
  -o out/playable-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root . \
  --renderer-capture-jsonl shift_d3d9_capture.jsonl \
  --renderer-pe-evidence out/shift_pe_evidence.json \
  --keyboard
```

The command owns the generated composite scene and must not silently replace it
with an unrelated prepared scene. If composition fails, the track-only
intermediate cannot be promoted to the playable result.

## Current Process 3 boundary

The later Phase 647/648/649 chain already closes the mechanical transport:

```text
current persistent VehicleWorldMatrix
-> freshness gate
-> Vulkan vertex upload
```

That transport is infrastructure-complete for Process 3 and is not reopened by
this phase. Phase 644/645 resource transforms are bootstrap state; Phase 649
consumes current runtime state supplied by Process 2. Process 3 does not infer
BODY identity, physics scheduling, input-to-drivetrain semantics, or camera-state
production from these resource archives.

The next Process 3 work therefore expands exact resource/scene/render coverage,
not another transform uploader or runtime scheduling abstraction.

## Regression coverage

`tests/test_native_playable_scene_bootstrap.py` verifies:

- full SHA-256 admission for BMW primary/cockpit and `RENDER.bff`;
- Phase 533 -> Phase 645 -> Phase 643 handoff;
- missing archive rejection;
- same-name wrong-hash rejection;
- byte-identical duplicate occurrence rejection;
- no archive-order fallback;
- unsupported vehicle rejection before corpus parsing.

`tests/test_retail_archive_admission.py` verifies the earlier native-bootstrap
Silverstone + BMW identity gate, including unknown-target fail-closed behavior and
byte-identical duplicate ambiguity.

`tests/test_offline_runtime_bootstrap.py` verifies that an identity failure blocks
both native scene and native vehicle admission before either consumer runs.

## Result

For the selected first playable target, the resource/render chain can no longer
become ready because a file merely has the expected basename. The required
retail archive bytes and a unique corpus occurrence are now explicit admission
proof before the scene/vehicle reaches native consumers.
