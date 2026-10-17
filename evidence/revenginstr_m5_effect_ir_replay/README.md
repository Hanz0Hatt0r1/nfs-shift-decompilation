# revenginstr M5 effect evidence

This frozen consumer bundle exercises `FunctionEffectIR/2` and
`FunctionSummary/2` on the NFS Shift scan22 function `00a277d0` (`SHIFT.exe`).
It is generated from the existing parameter load/store and High-P-code flow
evidence; the manifest pins each input, output, and the `revenginstr` source
commit.

The replay records 60 effects and 18 summary claims. Run
`python tools/replay_revenginstr_m5_effect_ir.py` with `REVENGINSTR_REPO` set
to the pinned checkout to verify the frozen bytes and schemas. Use
`--freeze` only when intentionally refreshing the evidence.

These rows describe static P-code and structural parameter-rooted fields.
Generic `LOAD`/`STORE` operand tokens do not establish runtime execution,
global identity, pointer aliasing, or write-to-read flow; field projections do
not assign semantic roles. See `scan22/manifest.json` for input and output
hashes and the full limitations list.
