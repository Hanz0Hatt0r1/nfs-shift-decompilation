# Phase 133 — MEB Usage ordinal → D3D9 Usage byte bridge

`SHIFT.MEBRuntimeUsageOrdinalBridge/1` derives a Usage map only from runtime
declaration records that are correlated to the exact BMW resource identity.

## Rule

For each preserved MEB descriptor `[Type, UsageOrdinal, Channel]`, the bridge looks
for declaration records in frames whose declaration resource matches the golden M3
MEB by SHA-256 (or normalized path when SHA is unavailable). Candidates must match
`Type` and `UsageIndex == Channel`; the observed D3D9 `Usage` byte becomes a candidate
mapping for that MEB Usage ordinal.

A single ordinal observed with multiple runtime Usage bytes is `ambiguous`. An ordinal
with no exact same-resource observation remains `unmapped`. No heuristic or archive
order is used.

## Output

The report contains `usage_map`, per-frame evidence rows, conflicts, unmapped ordinals,
and an explicit boundary that runtime capture authenticity is still `not-verified`.

`bmw_runtime_parity.py` and `bmw-runtime-golden-gate` accept either the legacy raw
mapping JSON or this nested bridge report.

## CLI

```bash
python shift_importer.py meb-runtime-usage-bridge bmw-paint-slice.json runtime-evidence.json usage-bridge.json
python shift_importer.py bmw-runtime-golden-gate bmw-paint-slice.json runtime-evidence.json gate.json --usage-map usage-bridge.json
```

## Next

Provide a concrete BMW runtime capture and run the bridge first. The expected first
high-value correlation is the real M3 `COLOR0` descriptor `[4,6,0]` against its
runtime declaration record; only a unique same-resource match can promote ordinal 6
to a verified D3D9 Usage byte.