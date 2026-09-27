# Phase 353 — one-command BMW apitrace byte-proof pipeline

Phase 353 combines the existing Linux apitrace extraction stages into one
reproducible command:

1. Phase 348 geometry-filtered BMW resource discovery;
2. Phase 350 direct TYPE_BLOB extraction from the original trace;
3. deterministic MEB-derived VB/IB artifact reconstruction;
4. Phase 351 exact seven-object byte parity;
5. Phase 352 `SHIFT.BMWM3RuntimeGeometryProof/1` generation.

## Command

    python tools/run_apitrace_bmw_buffer_proof.py \
      /path/to/shift.trace \
      /path/to/unique_bmw_geometry.json \
      /path/to/BMW_M3_E36.bff \
      ./bmw-buffer-proof

The workflow reads the original trace only through the bounded `apitrace dump
`--blobs` call range derived from the six known BMW index-buffer lifecycles and
the BMW vertex-buffer lifecycle. It does not require a multi-gigabyte text dump
and does not depend on the trimmed trace preserving fake memcpy calls.

## Outputs

- `extracted/buffer_blob_evidence.json` — raw apitrace BLOB provenance;
- `expected/manifest.json` — deterministic MEB-derived expected bytes;
- `direct_parity_report.json` — exact seven-object comparison;
- `runtime_geometry_proof.json` — strict renderer-facing geometry proof;
- `pipeline_result.json` — one machine-readable pipeline summary.

Runtime shader/material same-instance proof remains a separate gate.
