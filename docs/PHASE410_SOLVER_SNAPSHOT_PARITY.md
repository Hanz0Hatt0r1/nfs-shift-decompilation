# Phase 410 — solver snapshot parity adapter

The project now has a neutral comparison layer for an external SDF solver snapshot. A snapshot contains `scalar_count`, the retail `row_indices` vector, the flat `matrix_pool` and the RHS vector.

The comparator first checks structural identity: scalar count, row-index layout and buffer sizes. It then compares every matrix cell and RHS entry with a caller-selected absolute tolerance and reports bounded `(row,column)` differences. NaN/Inf mismatches are treated explicitly rather than silently coerced.

This layer does not fabricate captured values. It is ready to consume a genuine physics runtime dump once one is available, and it can already validate the reconstructed retail storage against generated/reference snapshots.

A standalone `tools/compare_sdf_solver_snapshots.py` CLI emits a compact result and can write the full JSON diff report.
