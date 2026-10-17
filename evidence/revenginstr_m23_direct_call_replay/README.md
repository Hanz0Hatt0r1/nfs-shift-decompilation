# M2.3 direct-call audit replay (SHIFT)

This consumer replay freezes five SHIFT functions with exact parameter and field-offset store/load pairs. The evidence uses the retail input SHA-256 already recorded in `coordination/research_inputs.lock.json`, read-only Ghidra exports, and `revenginstr` commit `88a30066b79af827de7c7a9cb91c24a9947edee4`.

Each candidate includes the bounded P-code TSV, parameter store/load rows, CFG/3, memory-store facts, paired-field graphs, direct-call effect rows, and the `/1`, `/2`, and `/3` audit results. `manifest.json` pins every evidence artifact by byte count, row count, and SHA-256.

## Replay

Use the pinned `revenginstr` revision with its command line tools installed in a virtual environment, then run from the repository root:

```sh
python tools/replay_revenginstr_m23_direct_call_audit.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The replay verifies the frozen artifact manifest, rebuilds field-access pairs and direct-call effects from the committed TSVs, runs all three audit versions, and compares the generated JSONL byte-for-byte with the frozen results. The bounded TSV is split by exact `function_entry`; only direct callees referenced by the caller P-code and present in the export are passed to the effect builder.

## Result

All 16 paired-field rows replay exactly. The `/1`, `/2`, and `/3` status counts are identical: 15 rows remain `possible_intervening_memory_effect`, one row is `store_not_dominating_load`, and none is `unique_cfg_store_candidate`. No direct-call effect row has status `no_explicit_memory_write`: complete callees are writeful, while the remaining rows are indirect, nested/unknown, or unresolved. Thus this consumer exercises `/3` in a second real program but does not contain a call eligible for filtering.

The result is negative structural evidence. It makes no branch-feasibility, runtime value-flow, or semantic-label claim. In particular, it does not validate a positive write-free-call filtering case; that still needs a separate consumer example before such behavior is claimed from consumer evidence.
