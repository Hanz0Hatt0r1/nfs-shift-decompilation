# Phase 632 — static PE renderer production

Phase 632 removes the manually prepared `SHIFT.PEImageEvidence/1` JSON from the
Silverstone renderer production handoff.

The original executable is **not executed**. It is opened only as a byte file by
the existing `d3d9_pe_evidence.py` static PE adapter.

## Pipeline

```text
SHIFT.exe bytes
→ PE headers/section mapping
→ fixed source-backed declaration table virtual addresses
→ file-backed table bytes
→ SHIFT.PEImageEvidence/1

out.zip / renderer report bundles
+ historical shift_d3d9_capture.jsonl
+ generated PE evidence
+ original resource corpus
→ Phase 631 hybrid production
→ Phase 630 raw capture bootstrap
→ Phase 627 / Phase 619-626 renderer frontier
```

The new tool is:

`tools/run_silverstone_renderer_static_pe_production.py`.

## Static-only boundary

The PE adapter already distinguishes virtual memory from bytes actually present
in the executable file.

Phase 632 records explicitly that:

- `SHIFT.exe` is never launched;
- the operating-system PE loader is not invoked;
- no entry point, import, TLS callback or game code is executed;
- recovered virtual addresses are mapped to section file offsets only;
- bytes not backed by the file are not treated as observed values;
- Usage values are never filled by semantic or runtime inference.

This is static binary evidence, equivalent to reading any other original game
resource file.

## Reused source-backed PE adapter

`src/graphics/d3d9/d3d9_pe_evidence.py` maps the Ghidra-recovered static table
addresses including:

- `0x00b90088` — declaration type-code table;
- `0x00b8eef0` — type-size table;
- `0x00b8ef38` — type-component table;
- `0x00b9011c` — nine-entry D3D9 Usage table;
- `0x00b90140` — usage-index table;
- `0x00b90178` — channel table;
- `0x00b901d0` — type-name pointer table.

The derived report is `SHIFT.PEImageEvidence/1`. Phase 630 then feeds only its
`decoded_tables.usage` values into the strict `SHIFT.D3D9UsageMap/1` builder.

## Partial PE evidence

Phase 632 does not require the Usage table to be fully decoded before handing the
report downstream.

If `usage_table_status=partial`, the exact partial PE report is still saved and
Phase 631/630 continues. Phase 630 can therefore still preserve independent
capture-local draw evidence while its Usage-dependent runtime attribution
remains blocked.

This avoids turning a missing file-backed table value into a false contradiction
or throwing away unrelated evidence.

## Usage

```bash
python tools/run_silverstone_renderer_static_pe_production.py \
  out.zip \
  --capture-jsonl shift_d3d9_capture.jsonl \
  --pe-image /path/to/SHIFT.exe \
  --output-dir out/silverstone_renderer_static_pe \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

An exact target-set override remains available:

```bash
--runtime-shader-targets evidence/silverstone_era3_runtime_shader_targets.json
```

Phase 631 still verifies that a chosen target set agrees with any target-set
identities present in the bundle.

## Output

```text
pe/
  shift_pe_image_evidence.json
hybrid/
  silverstone_renderer_hybrid_production_run.json
  bundle/
  raw/
  production/
silverstone_renderer_static_pe_production_run.json
```

The top-level format is:

`SHIFT.SilverstoneRendererStaticPEProductionRun/1`.

It records:

- exact PE input path, byte size and SHA-256;
- generated PE-evidence canonical SHA-256 and serialized-file SHA-256;
- PE machine/base/header metadata;
- Usage-table file-backed and decode status;
- the downstream hybrid production summary/frontier;
- every blocker without reinterpreting it as a capture requirement.

## What this closes

Before Phase 632, the end-to-end renderer production command still needed a
manually materialized PE-evidence JSON solely to recover the numeric D3D9 Usage
mapping.

After Phase 632, the renderer path can begin from original/static evidence:

```text
original PE bytes
+ historical raw D3D9 capture
+ renderer handoff/static ambiguity bundle
+ original BFF/ZIP resource corpus
→ renderer frontier
```

The remaining bundle dependency is now the higher-level static/base ambiguity
handoff, not the Usage table or capture-local reports.

## Capture policy

Phase 632 changes no historical capture fact. In particular, the old capture
still lacks direct observations for `SetSamplerState`, VB/IB payload bytes,
portable runtime resource path+SHA and texture payload snapshots.

None becomes a new-capture requirement merely because it is absent.

## Regression coverage

`tests/test_run_silverstone_renderer_static_pe_production.py` verifies:

- static PE evidence is persisted and passed to Phase 631;
- input/corpus/target options are preserved;
- a partial Usage table still reaches the downstream fail-closed pipeline;
- a PE parser failure stops before hybrid production;
- a missing PE image stops before parsing;
- an unexpected derived report format is rejected;
- executable bytes are never executed or treated as loader-populated memory.
