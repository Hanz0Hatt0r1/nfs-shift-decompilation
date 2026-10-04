# Process 1 — one-shot BMW BODY0 bind static-proof runner

## Playable-slice blocker reduced

The static BODY0-bind chain is now split into several fail-closed analyzers, but
running them manually makes it easy to use stale reports or skip a gate.  The
playable Linux slice needs one reproducible offline path from the existing Ghidra
export to the current first unresolved bind join.

This stage adds:

```text
tools/ghidra/run_bmw_body0_bind_static_proof.py
```

Bundle format:

```text
SHIFT.BMWBody0BindStaticProofBundle/1
```

The runner creates no new semantic evidence.  It only composes merged static
proof stages and retains their individual reports.

## Inputs

```text
<ghidra-export-root>
<caller-instruction-export.jsonl>
<pose-writer-instruction-export.jsonl>
<output-dir>
```

The export root supplies the exact `SHIFT.exe` binary/functions/callgraph data
used by the initialization frontier and physical ABI join.  Caller instructions
cover the direct `FUN_007b7840` callsites.  The pose-writer export is one exact
`SHIFT.GhidraFunctionInstructions/2` row for `FUN_007b7840` itself.

No original game execution or runtime capture is involved.

## Stage order

The runner executes the current chain in one direction only:

```text
01 SHIFT.BMWBody0BindInitializationFrontier/1
   ->
02 SHIFT.BMWBody0BindCallsiteRegisterProvenance/1
   ->
03 SHIFT.BMWBody0BindPoseWriterABI/1
   ->
04 SHIFT.BMWBody0BindStackValueProvenance/1
   ->
05 SHIFT.BMWBody0BindPoseWriterTargetRole/1
   ->
06 SHIFT.BMWBody0BindPoseWriterValueProvenance/1
```

Stage 04 is skipped only when the physical ABI contains no stack-value worklist.
Stage 06 is not executed unless Stage 05 has positively proven the BODY pose
record target parameter.

## Output bundle

Successful stages are written as numbered JSON files in the output directory.
The final coordination artifact is:

```text
bmw_body0_bind_static_proof_bundle.json
```

It records:

- every stage state/path/format;
- mechanical readiness through the chain;
- whether the target parameter is positive;
- whether the value-dependency frontier is positive;
- the first remaining semantic join and blocker IDs;
- explicit negative retail transform/render readiness.

The bundle always preserves:

```text
BODY0_pointer_at_bind_callsite_ready = false
BODY0_bind_origin_basis_values_ready = false
BODY0_bind_frame_proof_ready = false
phase704_706_retail_bind_admissible = false
phase649_retail_vulkan_upload_ready = false
```

because no merged stage yet closes both the BODY0 pointer and concrete bind-value
joins.

## Upstream-gate behavior

If the target-role report is negative, value provenance is marked:

```text
blocked_by_upstream_gate
```

and is not executed.  This prevents a dependency frontier from being generated
against an unproven BODY target.

If the ABI has no stack arguments requiring value provenance, the stack stage is
recorded as:

```text
not_required
```

rather than fabricating an empty positive evidence report.

## Mechanical failure behavior

Malformed or ambiguous inputs still raise an error from the owning analyzer.
Before re-raising, the runner writes a failure bundle containing:

```text
completed = false
failed_stage = <stage>
error = <exception>
```

Any successful earlier JSON reports remain in the output directory for audit.
A failed stage is never promoted to semantic readiness.

## Current expected retail stopping point

With the current repository state, the strongest possible successful bundle can
reach a positive target-role/value-dependency frontier and then report the real
remaining join:

```text
target parameter callsite value -> BMW chassis BODY0
AND
pose STORE terminal roots -> concrete bind-time origin/basis values
```

Once both sides are source-backed, a later stage may construct and validate
`M_BODY0_bind` and emit a positive `SHIFT.BMWBody0BindFrameProof/1`.

## Example

```bash
python tools/ghidra/run_bmw_body0_bind_static_proof.py \
  out/shift_ghidra_database \
  out/body0_bind_callers.instructions.jsonl \
  out/fun_007b7840.instructions.jsonl \
  out/body0_bind_static_proof
```

The command intentionally does not launch Ghidra or the original game.  It
consumes already-exported static data only.
