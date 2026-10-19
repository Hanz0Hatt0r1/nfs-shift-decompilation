# SHIFT M2.3 structural graph gold

This consumer-owned gold subgraph covers the captured
`FUN_00a45520` / `FUN_00a40550` field-memory slice. It labels all seven direct
calls in those exports, both parameter-0 reads at offset `0x0`, and the one
parameter-0 write at offset `0x0`. The graph scope declares `calls`, `reads`,
and `writes` complete for those captured operations.

The edges were manually adjudicated from the frozen Ghidra P-code and
parameter store/load records, separately from the Semantic Program Graph.
`NFS.M23ConsumerReplayNote/1` record indexes are Markdown line numbers;
P-code and parameter TSV record indexes are one-based data rows excluding the
header. The note records that the consumer replay rebuilds its audits from the
committed TSVs.

This is a structural graph check only. It does not name or interpret the
parameter-0 field, prove that the store reaches either load, establish branch
feasibility or aliasing, or claim runtime execution. The frozen M2.3 audit
explicitly retains possible intervening memory effects and makes no
runtime-value-flow or semantic-label claim.

| Source | SHA-256 |
| --- | --- |
| [Bounded P-code](../../revenginstr_m23_direct_call_replay/00a45520/bounded-pcode.tsv) | `934c673014b84b962e7b5574a9a41cd8752fef2b080f7d1f57ba36c7ecccbc61` |
| [Parameter stores](../../revenginstr_m23_direct_call_replay/00a45520/parameter-stores.tsv) | `5afcb2d296078813129b1b235b4cacab258cc7c8f4892be9a0d0f46e92d0e6ba` |
| [Parameter loads](../../revenginstr_m23_direct_call_replay/00a45520/parameter-loads.tsv) | `facc794c48e31ea72ee031a25dc1f6bb80a68392efa91c9c4ecf740a1afb2972` |
| [Consumer M2.3 replay note](../../revenginstr_m23_direct_call_replay/README.md) | `a4d03d0352bf142987ac4481118edcc1d707c9f15bf2b468c86451e674c8256d` |

The gold artifact SHA-256 is
`df606c38bf980329081929d63f2f1835f8e293eb78f6bdadd344ef140888496f`.
It pins graph `program:1141bf92df0142e061e8ac27deba839412f2e16a65ffda08e3ef07dbce335377`
for `nfs-shift:SHIFT.exe`. The replay uses the exploratory view because the
field edges are structural projections, not calibrated exact-static facts.
It matched all 7 calls, 2 reads, and 1 write; each relation had 1.0 precision
and recall, with 100% provenance completeness. Accepted-edge precision is
`null` because graph confidence is uncalibrated.
