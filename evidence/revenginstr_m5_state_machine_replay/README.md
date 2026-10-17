# revenginstr M5 state-machine evidence

This frozen structural audit applies `revenginstr-state-machine-candidates` to
one existing NFS Shift scan22 function. Its manifest pins the CFG/3, P-code
flow, parameter-load, memory-store inputs and the `revenginstr` source commit.

The audit joined 169 P-code operations, 12 parameter field loads and 3 memory
stores. It found zero instances of the bounded compare/branch/same-field-write
pattern. That result is limited to this function and pattern; it does not show
that the function has no state behavior. The audit makes no branch-polarity,
path-feasibility, runtime-value-flow or state-semantics claim.

Replay with `python tools/replay_revenginstr_state_machine_scan22.py` and
`REVENGINSTR_REPO` set to the pinned checkout. Use `--freeze` only when
intentionally refreshing the report.
