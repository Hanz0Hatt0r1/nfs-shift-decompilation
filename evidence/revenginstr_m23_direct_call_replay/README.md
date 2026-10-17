# M2.3 direct-call audit replay (SHIFT)

This consumer replay freezes twelve SHIFT functions with 31 exact parameter and field-offset store/load pairs. It uses the retail input SHA-256 recorded in `coordination/research_inputs.lock.json`, read-only Ghidra exports, and `revenginstr` commit `88a30066b79af827de7c7a9cb91c24a9947edee4`.

Each candidate includes bounded P-code, parameter store/load rows, CFG/3, memory-store facts, paired-field graphs, direct-call effect rows, and the `/1`, `/2`, and `/3` audit outputs. `manifest.json` pins every artifact by byte count, row count, and SHA-256. The replay rebuilds the derived pairs, call effects, and audits byte-for-byte.

## Replay

Install the pinned `revenginstr` revision in a virtual environment and run from the repository root:

```sh
python tools/replay_revenginstr_m23_direct_call_audit.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The replay verifies the frozen artifacts, rebuilds field-access pairs and direct-call effects from the committed TSVs, runs all three audit versions, and compares generated JSONL byte-for-byte. The bounded TSV is split by exact `function_entry`; only direct callees present in the export are supplied to the effect builder.

## Results

All 31 paired-field rows replay exactly. `/1` reports 26 `possible_intervening_memory_effect`, four `store_not_dominating_load`, and one `unique_cfg_store_candidate`. `/2` and `/3` each report 25, four, and two rows in those categories.

Across 67 direct-call effect rows, three have `no_explicit_memory_write` status. One eligible call occurs on the exact store-to-load witness in `00619b7d`: direct call `0060a369` at P-code time 27 lies between the paired store at time 22 and load at time 102, on witness blocks `[0, 1, 4]`. `/3` leaves the row `possible_intervening_memory_effect` because the same witness contains an `unknown_effect` direct call at time 31 (`0060a7e1`). The write-free call is eligible for filtering; the unknown call remains a barrier. No status is promoted to a unique candidate.

The control case `00503790` has a complete write-free direct call at time 91, after its paired loads at times 38 and 68; it does not lie in either store-to-load interval. The expanded scan9 screen covered 32 bounded roots and 90 ordered pairs. It found three complete write-free call rows, with exactly one on an audited witness; `/1`, `/2`, and `/3` status counts remained identical across the screen.

These are conservative structural audits only. They make no branch-feasibility, runtime value-flow, or semantic-label claim.
