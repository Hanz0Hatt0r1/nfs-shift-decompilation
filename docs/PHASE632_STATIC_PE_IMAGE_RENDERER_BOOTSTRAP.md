# Phase 632 — static PE-image renderer bootstrap

Phase 632 removes another manually prepared renderer handoff from the offline
Silverstone path: `SHIFT.PEImageEvidence/1` no longer has to be created by hand
before running the historical D3D9 capture pipeline.

No original executable is launched. The PE file is read strictly as bytes by the
existing static adapter in `src/graphics/d3d9/d3d9_pe_evidence.py`.

## Existing proof chain

Before this phase the source-backed chain was already:

```text
SHIFT.PEImageEvidence/1
→ decoded_tables.usage
→ SHIFT.D3D9UsageMap/1
→ historical raw D3D9 JSONL
→ SHIFT.D3D9TargetDrawLocalEvidence/1
→ SHIFT.IMBRuntimeCapturePipeline/1
```

`d3d9_pe_evidence.py` already knows the exact recovered retail addresses for the
D3D9 declaration tables, including:

```text
usage_table = 0x00B9011C, 9 * 4 bytes
```

and maps those virtual addresses to file-backed PE bytes without executing the
image.

Phase 632 only connects that existing static builder to the production entry
points.

## Raw-capture bootstrap

`tools/run_silverstone_renderer_raw_capture_bootstrap.py` now accepts either:

- an existing `SHIFT.PEImageEvidence/1` JSON report; or
- `--pe-image <path>`.

Exactly one source is allowed.

Example with the static PE image directly:

```bash
python tools/run_silverstone_renderer_raw_capture_bootstrap.py \
  shift_d3d9_capture.jsonl \
  --pe-image SHIFT.exe \
  --output-dir out/silverstone_raw_renderer
```

The PE path is only opened for reading. `SHIFT.exe` is never started, loaded as a
process, injected, or used for runtime capture.

When `--pe-image` is used the output directory additionally contains:

```text
d3d9_pe_evidence.json
```

with format:

```text
SHIFT.PEImageEvidence/1
```

The raw-bootstrap manifest preserves:

- PE image path, byte size and SHA-256;
- generated PE-evidence path and SHA-256;
- the fact that the evidence came from static PE-image analysis;
- the unchanged numeric Usage source:
  `SHIFT.PEImageEvidence/1:decoded_tables.usage`.

## Failure boundary

PE parsing and draw-local capture reconstruction are independent.

Therefore a PE decode failure behaves as follows:

```text
PE decode failed
→ Usage map unavailable
→ declaration-dependent Phase 573 blocked
```

but, when the historical capture and shader target set are valid:

```text
raw capture
→ draw-local shader/VB/IB/texture/constant evidence
```

still runs and is retained.

A missing or malformed PE table is not a declaration contradiction and does not
justify a new capture.

## Direct hybrid production

`tools/run_silverstone_renderer_pe_image_hybrid_production.py` removes the PE
JSON handoff from the Phase 631 production path.

It performs:

```text
static PE image bytes
→ d3d9_pe_evidence.py
→ generated SHIFT.PEImageEvidence/1
→ unchanged Phase 631 hybrid production
→ Phase 627
→ Phase 619/620/622/623/624/625/626
```

Example:

```bash
python tools/run_silverstone_renderer_pe_image_hybrid_production.py \
  out.zip \
  --capture-jsonl shift_d3d9_capture.jsonl \
  --pe-image SHIFT.exe \
  --output-dir out/silverstone_renderer_hybrid \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

The wrapper persists the generated PE evidence before invoking Phase 631, so the
static input remains inspectable and reproducible rather than being an implicit
in-memory transformation.

The top-level wrapper format is:

```text
SHIFT.SilverstoneRendererPEImageHybridProductionRun/1
```

It records PE image SHA-256, generated evidence SHA-256, downstream hybrid
status, renderer frontier, and all blockers.

## Proof policy

Phase 632 does not add a new source of semantic inference.

The following rules remain unchanged:

- PE bytes are static evidence only;
- the executable is never run;
- Usage ordinal values come only from the decoded retail table;
- missing table entries remain missing;
- ranking, frequency and filename are not proof;
- bundle copies of capture-derived reports remain Phase 631 canonical
  cross-checks only;
- missing historical capture events do not imply recapture;
- `buffer_payload` remains a last conditional fallback for unresolved geometry;
- no new capture is required by this phase.

## Regression coverage

`tests/test_run_silverstone_renderer_pe_image_bootstrap.py` verifies:

- direct static PE-image → PE evidence → ready Usage map;
- exact Usage values reach Phase 573;
- PE decode failure preserves independent draw-local evidence;
- exactly one PE source is required by the raw bootstrap API;
- the direct hybrid wrapper persists generated PE evidence and delegates to the
  unchanged Phase 631 runner;
- PE decode failure blocks before hybrid production.
