# Phase 652 — exact external-sampler capture feedback

## Playable-slice blocker reduced

Phase 650 makes the selective Phase 642 capture self-validating, but the
resulting bundle still required a manual path handoff back into
`bootstrap_native_vertical_slice.py`:

```text
external_sampler_capture_result.json
+ manually copied --renderer-capture-jsonl
+ manually copied --renderer-capture-root
-> full renderer re-attribution
```

That manual hop is now removed without weakening renderer admission.

Phase 652 adds:

```text
tools/bootstrap_native_vertical_slice_from_capture_result.py
```

The entry point accepts the ready Phase 650 result bundle, revalidates its
capture integrity, then delegates to the existing unified bootstrap with the
exact capture JSONL/root injected automatically.

## Exact bundle layout

The Phase 650 Wine wrapper already owns one output layout:

```text
<capture-root>/
  shift_d3d9_capture.jsonl
  external_sampler_capture_result.json
  textures/*.ppm
```

Phase 652 treats the **parent directory of the supplied Phase 650 result** as
the bundle root and accepts only the exact sibling:

```text
<capture-root>/shift_d3d9_capture.jsonl
```

It does not:

- search recursively for a matching basename;
- trust an old absolute `source.capture_root` stored in a copied result;
- accept a caller override for `--renderer-capture-jsonl`;
- accept a caller override for `--renderer-capture-root`.

This lets a capture bundle be moved as a unit without turning basename search
or a stale machine-local absolute path into identity proof.

## Result-to-raw integrity revalidation

A ready `SHIFT.Phase642ExternalSamplerCaptureResult/1` is not trusted only
because its JSON says `ready=true`.

For every ready Phase 650 expectation, Phase 652 requires at least one ready
observation to still match the canonical sibling raw JSONL on:

- exact `event_index` within that capture;
- `event == set_texture`;
- requested D3D9 stage;
- expected resource type;
- observed texture pointer as capture-local integrity data;
- `snapshot_status == captured`;
- exact ordered `snapshot_paths` list;
- exact required snapshot count;
- existing snapshot files under the canonical bundle root;
- complete canonical cube face set for `samplerCube`.

Duplicate matching event indices are rejected as ambiguous. Malformed raw JSON
is rejected.

The texture pointer and event index are used only to prove that the Phase 650
result still describes the same raw capture file. They are **not** promoted into
retail resource, draw, binding, or scene identity.

## Full re-attribution remains mandatory

Once the bundle is verified, Phase 652 calls the existing
`bootstrap_native_vertical_slice.py` and injects:

```text
--renderer-capture-jsonl <capture-root>/shift_d3d9_capture.jsonl
--renderer-capture-root  <capture-root>
```

All other normal bootstrap inputs remain unchanged, including exact retail
corpus inputs and PE evidence.

The existing renderer path still reruns the complete evidence/admission chain.
Phase 652 explicitly does not claim:

- binding identity;
- draw identity;
- scene identity;
- resource identity;
- `scene_set_ready`;
- that Phase 650 can replace Phase 569/572/574/590/592/580/585.

## Usage

After the exact Phase 642/650 Wine capture succeeds:

```bash
python tools/bootstrap_native_vertical_slice_from_capture_result.py \
  out/phase642-capture/external_sampler_capture_result.json -- \
  Vehicles.zip Silverstone_Era3_.zip SHIFT_tail.zip \
  -o out/vertical-slice \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root . \
  --renderer-pe-evidence out/shift_pe_evidence.json \
  --keyboard
```

The caller no longer supplies the capture JSONL or capture root manually.

## Ownership boundary

Phase 652 is Process 3 resource/render coordination only. It does not modify:

- Process 1 BODY/resource semantics;
- Process 2 physics scheduling;
- input processing;
- persistent BODY commit;
- camera-state production;
- `VehicleWorldMatrix` transport;
- Vulkan transform conventions.

## Regression coverage

`tests/test_phase652_capture_result_feedback.py` verifies:

- canonical sibling capture/root resolution;
- stale stored capture-root rejection as selection authority;
- raw-capture tamper rejection after a previously ready Phase 650 result;
- no recursive/similar-basename fallback;
- Phase 650 proof-boundary preservation;
- exact delegation to the existing unified bootstrap;
- refusal of manual capture JSONL/root overrides.

## Result

The renderer feedback loop is now:

```text
Phase 641 exact missing sampler frontier
-> Phase 642 selective Wine capture
-> Phase 650 capture-result preflight
-> Phase 652 exact bundle feedback
-> existing full renderer re-attribution/admission
-> scene_set_ready or the next exact blocker
```

No renderer resource is synthesized and no historical frame/draw number is
used as cross-session semantic identity.
