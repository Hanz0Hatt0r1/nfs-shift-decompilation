# M2.3 direct-call audit replay (SHIFT)

This consumer replay freezes ten SHIFT functions with 28 exact parameter and field-offset store/load pairs. The evidence uses the retail input SHA-256 already recorded in `coordination/research_inputs.lock.json`, read-only Ghidra exports, and `revenginstr` commit `88a30066b79af827de7c7a9cb91c24a9947edee4`.

Each candidate includes the bounded P-code TSV, parameter store/load rows, CFG/3, memory-store facts, paired-field graphs, direct-call effect rows, and the `/1`, `/2`, and `/3` audit results. `manifest.json` pins every evidence artifact by byte count, row count, and SHA-256.

## Replay

Use the pinned `revenginstr` revision with its command line tools installed in a virtual environment, then run from the repository root:

```sh
python tools/replay_revenginstr_m23_direct_call_audit.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The replay verifies the frozen artifact manifest, rebuilds field-access pairs and direct-call effects from the committed TSVs, runs all three audit versions, and compares the generated JSONL byte-for-byte with the frozen results. The bounded TSV is split by exact `function_entry`; only direct callees referenced by the caller P-code and present in the export are passed to the effect builder.

## Result

All 28 paired-field rows replay exactly. The `/1` replay has 25 `possible_intervening_memory_effect`, two `store_not_dominating_load`, and one `unique_cfg_store_candidate` rows. `/2` and `/3` each have 24, two, and two rows in those categories. The `/1` candidate at `00a45520` is the store at time 30 paired with the load at time 39; `/2` adds the `00a45b50` store-at-33/load-at-44 candidate after excluding a proven disjoint store. The call-aware audit preserves the `/2` status counts.

Across 56 direct-call effect rows, none has status `no_explicit_memory_write`: all resolved callees in this sample contain explicit writes, while the remaining rows are indirect, nested/unknown, or unresolved. In `00a45520`, a resolved call with an explicit `STORE` at P-code time 102 lies between the paired store at time 30 and load at time 107; `/3` keeps that pair unresolved. The unique candidates at `00a45520` and `00a45b50` are structural only and do not result from filtering calls. This second-consumer replay therefore validates the barrier behavior but does not validate a positive write-free-call filtering case.

No branch-feasibility, runtime value-flow, or semantic-label claim is made. A separate consumer example with an exact direct call and a complete write-free callee on the candidate path is still needed to exercise the allowed filter in consumer evidence.
