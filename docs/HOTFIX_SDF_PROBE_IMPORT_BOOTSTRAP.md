# Standalone SDF probe import bootstrap hotfix

A direct launcher invocation could fail before argument parsing with:

```text
ModuleNotFoundError: No module named 'd3d9_pe_evidence'
```

The launcher bootstraps the repository root and `src/physics`, while the PE
validator depends on `src/graphics/d3d9/d3d9_pe_evidence.py`. Normal test runs
can hide this because root `sitecustomize.py` recursively adds source
directories to `sys.path`.

The PE validator now derives `src/graphics/d3d9` from its own file location
and adds that directory before importing `d3d9_pe_evidence`.

Regression coverage executes both the PE validator and the real
`tools/run_sdf_solver_probe.py --print-contract` path under `python -S`,
which disables `sitecustomize.py`.

This is an import/bootstrap hotfix only. Capture, solver, relation-mutation and
scheduler semantics are unchanged.
