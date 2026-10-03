# Phase 639 — unified resource + renderer vertical-slice handoff

Phase 638 removed the manually supplied `SHIFT.SGBRuntimeObjectCandidateJoin/1`
from the source-backed renderer path. A higher-level split still remained:

```text
resource vertical-slice bootstrap
  -> runtime_bootstrap.json

manual path handoff
  -> renderer source bootstrap
```

Phase 639 removes that split from the top-level Process 3 command.

## Vertical-slice blocker

The intended Process 3 interface is a single fail-closed path from selected game
data, track and vehicle to every offline resource/renderer artifact that can be
proven from the available corpus and historical capture. Requiring a user to
copy the resource bootstrap path into a second renderer command defeats that
handoff and makes it easy to combine stale or unrelated evidence.

When renderer evidence is requested, `tools/bootstrap_native_vertical_slice.py`
now passes the exact `runtime_bootstrap.json` produced earlier in the same
invocation to the Phase 637/638 source renderer pipeline.

## Unified dependency chain

```text
retail BFF / ZIP / directory inputs
+ exact track
+ exact vehicle
        |
        v
OfflineNativeVerticalSliceBootstrap
        |
        +-> OfflineRuntimeBootstrap
        |     +-> exact resource catalog / IR
        |     +-> native scene
        |     +-> native vehicle
        |     `-> runtime_bootstrap.json
        |
        +-> runtime requirements / profile preparation
        |
        `-> optional unified renderer evidence
              + historical raw D3D9 JSONL
              + static PE image/evidence
              + same retail corpus
              + exact runtime_bootstrap.json above
                    |
                    v
              Phase 636 full shader targets
              -> Phase 630 raw capture bootstrap
              -> Phase 638 OBJECT candidate regeneration
              -> Phase 634 ambiguity regeneration
              -> Phase 633 base audit regeneration
              -> Phase 619-626 renderer production/frontier
```

No original game execution occurs.

## CLI

Renderer evidence is opt-in so the existing resource/profile-only command keeps
its prior semantics. The unified path is enabled with
`--renderer-capture-jsonl` plus exactly one static PE source:

```bash
python tools/bootstrap_native_vertical_slice.py \
  Vehicles.zip Silverstone_Era3_.zip SHIFT_tail.zip \
  -o out/vertical-slice \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root /path/to/nfs-shift-decompilation \
  --keyboard \
  --renderer-capture-jsonl shift_d3d9_capture.jsonl \
  --renderer-pe-image SHIFT.exe
```

A prebuilt static PE evidence report may be supplied instead:

```text
--renderer-pe-evidence <path>
```

Historical renderer report bundles remain optional cross-checks only:

```text
--renderer-bundle <path>
```

They never become selection authority.

## Unified output

`vertical_slice_bootstrap.json` now records:

- whether renderer evidence was requested;
- whether source renderer regeneration completed;
- the current regenerated renderer frontier;
- the Phase 637 manifest path;
- the full Phase 637 report under `stages.renderer_source_bootstrap`;
- combined blocking reasons.

The Phase 637 manifest is written under:

```text
renderer-evidence/silverstone_renderer_source_bootstrap_production_run.json
```

This makes the renderer ambiguity frontier part of the same handoff consumed by
the Process 3 vertical-slice workflow instead of an unrelated side artifact.

## Fail-closed gates

The selected offline resource bootstrap is authoritative. Renderer evidence is
not started when that bootstrap is blocked, so an external renderer artifact
cannot bypass ambiguous or missing resource identity.

When renderer evidence is explicitly requested:

- a blocked Phase 637/638 path makes the unified bootstrap not ready;
- launch-plan validation cannot bypass that renderer failure;
- the precise renderer blocking reasons are copied into the top-level report;
- no renderer artifact is synthesized;
- no report bundle can replace a blocked regenerated source;
- no candidate ranking is introduced.

When renderer evidence is not requested, the previous resource/profile-only
readiness semantics remain unchanged.

## Existing-capture exhaustion

The historical raw capture already contains shader creation bytecode, draw-local
vertex constants and texture bindings. The absence of a direct D3D9
`SetTransform` event therefore does not by itself justify a recapture: Phase 625
must continue to use exact float32 draw-local constant windows for transform
witnesses before any missing observation can be promoted to a capture blocker.

The unified top-level report exposes the regenerated Phase 626 frontier so this
rule is enforceable at the primary Process 3 diagnostic interface.

## Proof boundary

Phase 639 is orchestration only. It does not claim that:

- a renderer candidate is portable resource identity;
- a unique static candidate is runtime admission;
- descriptor compatibility is texture identity;
- an absent intermediate report means the raw capture lacks the observation;
- a source-valid optional Phase 595 ambiguity may be resolved by a bundle;
- a complete offline renderer frontier is itself a playable runtime scene.

The next development step must be selected from the concrete
`renderer_frontier.existing_data_requiring_tooling` and top-level runtime
requirements emitted by this unified command.