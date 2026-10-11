# Process 1B — one-command Ghidra helper-setter acquisition

## Blocker removed

Merged #2012 provides the compact whole-program Ghidra exporter and the Python bridge that feeds the three bounded helper-setter probes from one pinned instruction stream. The remaining acquisition friction was operational: export and analysis still required two manual commands, exposed the repository-wide Java script path to Ghidra compilation, and could leave a partially populated destination if either step failed.

This runner closes that orchestration gap without adding a semantic transport class.

## Runner

```text
tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh
```

Usage:

```bash
GHIDRA_HOME=/path/to/ghidra \
  bash tools/ghidra/run_p1b_manager374_helper_setter_ghidra_headless.sh \
  /path/to/project-dir \
  PROJECT_NAME \
  SHIFT.exe \
  /path/to/output/p1b-helper-setter-ghidra
```

Optional bound:

```bash
SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS=1800
```

The project must already contain the analyzed PC retail `SHIFT.exe` used by the P1B Ghidra evidence path.

## Acquisition pipeline

The wrapper performs these steps in one fail-closed transaction:

1. validates `GHIDRA_HOME`, project directory, timeout and an empty/nonexistent destination;
2. rejects an already-running headless session for the same project/program instead of contending for the project lock;
3. copies only `ShiftCompactInstructionStreamExporter.java` into a temporary Ghidra script directory;
4. opens the existing project with `-readOnly -noanalysis`;
5. exports `compact_instruction_stream.jsonl.gz`;
6. runs `run_p1b_manager374_helper_setter_ghidra_frontier.py` over that exact stream;
7. validates the acquisition/frontier formats and the fail-closed P1.3 semantic gates;
8. preserves the compact stream and `ghidra_headless.log` beside the generated JSON contracts;
9. publishes the destination only after every previous step succeeds.

The staging directory is created beneath the destination parent, so final publication is a same-filesystem rename rather than incremental writes into the requested evidence directory.

## Output

A successful directory contains:

```text
compact_instruction_stream.jsonl.gz
ghidra_headless.log
ghidra_acquisition.json
frontier.json
direct_call_argument.json
helper_return_immediate.json
helper_return_stack.json
```

`ghidra_acquisition.json` remains the `SHIFT.P1B.Manager374GhidraHelperSetterAcquisition/1` contract from #2012. This wrapper introduces no replacement semantic contract.

## Safety and authority

The wrapper explicitly requires the #2012 acquisition contract to retain:

```text
raw_executable_sha256_verified_in_this_run = false
ghidra_helper_setter_probe_bundle_execution_complete = true
ghidra_helper_setter_candidate_frontier_composed = true
retail_helper_setter_probe_bundle_execution_complete = false
retail_helper_setter_candidate_frontier_composed = false
```

It also refuses publication if any of these final gates become true unexpectedly:

```text
global_helper_non_vtable_indirect_setter_surface_complete
external_or_unknown_origin_outer_alias_surface_complete
independent_unnamed_opaque_or_external_runtime_root_synthesis_complete
unrecognized_runtime_transform_root_origin_surface_complete
global_manager_root_origin_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

External provider count must remain `7`.

The Ghidra stream is corroborating acquisition evidence. The raw PC retail image remains the semantic authority for any later global/final closure.

## Failure behavior

- A non-empty destination is never overwritten.
- A Ghidra timeout or non-zero exit publishes no destination.
- An empty/missing instruction stream publishes no destination.
- A bridge/contract validation failure publishes no destination.
- Temporary exporter/compiler directories are removed on exit.
- Existing Ghidra processes are reported, never killed automatically.

## Tests

```bash
python3 -m pytest -q \
  tests/test_process1b_manager374_ghidra_helper_setter_headless.py
```

The integration regression uses a fake `analyzeHeadless` executable and verifies isolated exporter compilation, read-only/no-analysis flags, gzip export, #2012 analysis, output preservation and atomic publication. Additional tests cover non-empty destination refusal, headless failure and invalid timeout handling.

## Next step

Run this one-command acquisition against the pinned analyzed retail Ghidra project. If the resulting frontier has positive write candidates or open boundaries, classify those exact rows first. If its bounded frontier is empty, compare the canonical instruction stream/candidate set against a raw-retail #2011 run before promoting any scoped helper-setter closure. Do not add another synthetic helper transport before that real acquisition is consumed.
