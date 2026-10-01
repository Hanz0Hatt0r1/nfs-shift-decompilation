# Phase 644 — standalone SDF probe import bootstrap

A direct launcher invocation could fail before argument parsing with:

```text
ModuleNotFoundError: No module named 'd3d9_pe_evidence'
```

The launcher already bootstraps the repository root and `src/physics`, but the
PE validator depends on `src/graphics/d3d9/d3d9_pe_evidence.py`. Normal test
runs often hid this because root `sitecustomize.py` recursively adds every
`src` directory to `sys.path`.

Phase 644 makes the dependency explicit inside
`sdf_runtime_probe_pe_validation.py`: it derives `src/graphics/d3d9` from
its own file location and adds that directory before importing
`d3d9_pe_evidence`.

Regression coverage executes both the PE validator and the real
`tools/run_sdf_solver_probe.py --print-contract` path under `python -S`,
which disables `sitecustomize.py`. This freezes the standalone CLI import
contract independently of shell `PYTHONPATH` state.

No capture, solver, relation-mutation or scheduler semantics change in this
phase.
