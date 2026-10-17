# M2.3 direct-call audit replay (SHIFT)

This consumer replay freezes thirteen SHIFT functions with 33 exact parameter and field-offset store/load pairs. It uses the retail input SHA-256 recorded in `coordination/research_inputs.lock.json`, read-only Ghidra exports, and `revenginstr` commit `88a30066b79af827de7c7a9cb91c24a9947edee4`.

Each candidate includes bounded P-code, parameter store/load rows, CFG/3, memory-store facts, paired-field graphs, direct-call effect rows, and the `/1`, `/2`, and `/3` audit outputs. `manifest.json` pins every artifact by byte count, row count, and SHA-256. The replay rebuilds the derived pairs, call effects, and audits byte-for-byte.

## Replay

Install the pinned `revenginstr` revision in a virtual environment and run from the repository root:

```sh
python tools/replay_revenginstr_m23_direct_call_audit.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The replay verifies the frozen artifacts, rebuilds field-access pairs and direct-call effects from the committed TSVs, runs all three audit versions, and compares generated JSONL byte-for-byte. The bounded TSV is split by exact `function_entry`; only direct callees present in the export are supplied to the effect builder.

## Results

All 33 paired-field rows replay exactly. `/1` reports 28 `possible_intervening_memory_effect`, four `store_not_dominating_load`, and one `unique_cfg_store_candidate`. `/2` and `/3` each report 27, four, and two rows in those categories.

Across 71 direct-call effect rows, five have `no_explicit_memory_write` status. In `00619b7d`, direct call `0060a369` at P-code time 27 lies between the paired store at time 22 and load at time 102, on witness blocks `[0, 1, 4]`. `/3` leaves the row `possible_intervening_memory_effect` because the same witness contains an `unknown_effect` direct call at time 31 (`0060a7e1`). The write-free call is eligible for filtering; the unknown call remains a barrier.

Scan12 adds a second path-filter case in `0060de20`: write-free calls at times 18 and 32 occur on both exact store-to-load witnesses. Each witness also contains two `CALLIND` barriers at times 42 and 52, so both pairs remain `possible_intervening_memory_effect` in `/1`, `/2`, and `/3`. This exercises the filter with multiple eligible calls and barriers without promoting either candidate.

The control case `00503790` has a complete write-free direct call at time 91, after its paired loads at times 38 and 68; it does not lie in either store-to-load interval. The scan9 screen covered 32 bounded roots and 90 ordered pairs. Scans 10–13 screened 630 additional function exports: 45 field-pair rows and 23 ordered pairs across nine roots. Two write-free direct calls were on exact witnesses in scan12, both alongside indirect-call barriers; the `/2` to `/3` status-change count remained zero. Scan14 added 22 previously unscanned functions from the `00a5` sample. The `ParameterStoreField/1` exporter returned zero rows, while the general memory-store exporter emitted 156 STORE facts, 53 with a parameter root; no field pairs were produced, so no dominance audit was run. Scan15 screened 62 functions with zero indirect calls: it retained 238 parameter-load rows and 302 general memory-store facts, but produced no parameter-to-field store rows or field pairs. Scan16 screened 70 functions with exactly one indirect call. It retained 18 parameter-to-field stores, 399 parameter loads, and 351 general STORE facts, producing five exact field pairs across three functions. CFG/2 and CFG/3 audited all five with identical statuses: three remained `possible_intervening_memory_effect` and two were `store_not_dominating_load`; neither version reported a unique candidate. The direct-call sidecar has eight explicit-write sites, three indirect-call barriers, and one unknown-effect site, with no write-free direct calls. The screen makes no runtime value-flow claim. See [`screening-scan10-13.json`](screening-scan10-13.json), [`screening-scan14.json`](screening-scan14.json), [`screening-scan15.json`](screening-scan15.json), and [`screening-scan16.json`](screening-scan16.json) for frozen selections and exports.

These are conservative structural audits only. They make no branch-feasibility, runtime value-flow, or semantic-label claim.
