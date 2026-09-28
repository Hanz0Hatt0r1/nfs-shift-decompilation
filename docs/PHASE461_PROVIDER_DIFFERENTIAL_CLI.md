# Phase 461 — specialized-provider differential CLI

## Goal

Phase 461 adds a command-line entry point around the Phase 460 capture differential harness.

## Usage

Dense experimental reference:

    python tools/run_specialized_provider_differential.py --pre pre_solve_XXXXXX.json

With a captured post-solve vector:

    python tools/run_specialized_provider_differential.py \
      --pre pre_solve_XXXXXX.json \
      --post post_solve_XXXXXX.json \
      --abs-tol 1e-10 --rel-tol 1e-8

With retail source-derived factor topology:

    python tools/run_specialized_provider_differential.py \
      --pre pre_solve_XXXXXX.json \
      --post post_solve_XXXXXX.json \
      --source SHIFT.exe.c \
      --provider 0

## Status semantics

The CLI preserves the Phase 460 statuses: `predicted-only`, `matched`, `numeric-divergence`, and `blocked`.

A source-pattern run is blocked if factor extraction fails or if the logical capture matrix fails Phase 458 dense-support admissibility. It never silently forces the source pattern onto the matrix.

## Scope boundary

The CLI is an experimental reconstruction tool. It does not prove retail binary identity and does not replace the existing SDF probe/session capture pipeline.
