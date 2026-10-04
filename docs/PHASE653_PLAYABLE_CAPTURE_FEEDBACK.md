# Phase 653 — playable capture-result feedback

## Playable-slice blocker reduced

Phase 652 closes the exact Phase 650 capture-result feedback path for the lower-level native vertical-slice bootstrap. The actual Silverstone + BMW milestone entry point, `tools/bootstrap_playable_linux_slice.py`, still required the caller to unpack that verified bundle into manual `--renderer-capture-jsonl` and `--renderer-capture-root` arguments.

Phase 653 removes that final manual renderer-capture path hop from the playable command.

## Interface

`bootstrap_playable_linux_slice.py` now accepts:

```text
--renderer-capture-result <capture-root>/external_sampler_capture_result.json
```

It reuses `resolve_capture_feedback_input()` from Phase 652. A ready Phase 650 result therefore has to revalidate against the canonical sibling layout:

```text
<capture-root>/external_sampler_capture_result.json
<capture-root>/shift_d3d9_capture.jsonl
<capture-root>/textures/*.ppm
```

The playable layer then injects the verified JSONL/root into the existing `bootstrap_native_vertical_slice.py` path.

## Fail-closed policy

When `--renderer-capture-result` is present, callers may not also provide:

```text
--renderer-capture-jsonl
--renderer-capture-root
```

The Phase 650 result is rejected before lower-level bootstrap if Phase 652 detects a missing canonical sibling capture, changed raw observation, missing snapshot file, invalid cube face set, stale or semantically promoted result, or any other failed feedback-integrity gate.

The stored absolute capture root inside an older result is not selection authority. There is no basename search or similar-path fallback.

## Renderer proof boundary

Phase 653 does not promote the Phase 650 snapshot preflight into renderer admission. It records that the verified capture feedback was consumed, then runs the existing full shader/draw/resource/scene re-attribution path.

It does not claim:

- binding identity from texture stage;
- draw identity across capture sessions;
- retail resource identity from a texture pointer;
- `scene_set_ready` from the Phase 650 result;
- a new camera/view convention;
- physics scheduling or BODY semantics;
- a new `VehicleWorldMatrix` transport.

## Example

```bash
python tools/bootstrap_playable_linux_slice.py \
  Vehicles.zip Silverstone_Era3_.zip SHIFT_tail.zip \
  -o out/playable-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root . \
  --renderer-capture-result out/phase642-capture/external_sampler_capture_result.json \
  --renderer-pe-evidence out/shift_pe_evidence.json \
  --keyboard
```

The historical direct `--renderer-capture-jsonl` path remains available for existing captures that do not come from a Phase 650 verified bundle.

## Regression coverage

`tests/test_phase653_playable_capture_feedback.py` verifies:

- exact Phase 652 capture JSONL/root forwarding into the existing lower-level bootstrap;
- removal of the Phase 650-only option before delegation;
- rejection of manual JSONL or root overrides;
- rejection of an unready/tampered capture result before renderer bootstrap starts.

## Result

The resource/render feedback path for the selected playable command is now:

```text
Phase 641 exact missing sampler frontier
-> Phase 642 selective Wine capture
-> Phase 650 capture-result preflight
-> Phase 652 exact bundle integrity
-> Phase 653 playable command handoff
-> existing full renderer re-attribution
-> Silverstone + BMW scene composition
```

No renderer evidence gate is skipped or weakened.
