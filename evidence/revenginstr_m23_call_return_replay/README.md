# M2.3 call-result-to-return replay

This consumer-owned evidence bundle replays `revenginstr-receiver-call-return-flow`
over 64 frozen caller/callee P-code exports from the M2.3 scan16–18 screens.
The input files contain 7,218 P-code rows. The pinned generic tool emits 37
structural call-result-to-return paths across 11 functions: 28 begin at direct
`CALL` results and 9 at `CALLIND` results. Each non-empty result is retained
under `call-return-paths/`; `manifest.json` records byte counts, row counts,
SHA-256 hashes, the exact source commit, and per-screen aggregates.

These paths identify P-code data dependencies from a call result to a return
operation in the same function. They do not establish factory semantics,
execution feasibility, returned object identity, or runtime type. `CALLIND`
paths also have no statically resolved target. No labels or class identities
were added.

## Replay

The source revision matches the `revenginstr` checkout pinned by the NFS CI
workflow (`08a31b94c304f8b7a57996974dafe352413f7924`). With that revision
installed, run from the repository root:

```sh
REVENGINSTR_REPO=/path/to/revenginstr \
  python tools/replay_revenginstr_m23_call_return.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The test suite validates the frozen input/output hashes and replays all 64
exports byte-for-byte through the pinned generic CLI.
