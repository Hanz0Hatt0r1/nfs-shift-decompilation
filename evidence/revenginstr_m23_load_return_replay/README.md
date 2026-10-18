# M2.3 parameter-load-to-return replay

This consumer-owned artifact replays the pinned
`revenginstr-receiver-load-return-flow` command on one exact function snapshot
from NFS Shift scan18. The frozen scan has 115 parameter-load rows; seven
belong to the selected function. The generic tool finds three paths from those
parameter-rooted loads to `RETURN` operations. The manifest pins both source
exports and the generated graph file by byte count, row count, and SHA-256.

These paths are structural evidence only. They do not assign getter or
accessor semantics, prove branch feasibility, identify a returned object, or
establish runtime behavior.

## Replay

The source revision matches the `revenginstr` checkout pinned by NFS CI
(`08a31b94c304f8b7a57996974dafe352413f7924`). With that revision installed,
run from the repository root:

```sh
REVENGINSTR_REPO=/path/to/revenginstr \
  python tools/replay_revenginstr_m23_load_return.py \
  --bin-dir /path/to/revenginstr/.venv/bin
```

The test suite verifies source/output hashes and replays the three graphs
byte-for-byte through the pinned generic CLI.
