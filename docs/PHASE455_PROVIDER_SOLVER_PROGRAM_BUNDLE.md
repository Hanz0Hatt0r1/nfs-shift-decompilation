# Phase 455 — specialized-provider solver program bundle

## Goal

Phase 455 assembles the specialized-provider reconstruction into one consumer-facing evidence bundle.

Each provider program contains the previously reconstructed solver IR, source-order execution schedule, update relations, output-vector schedule, acceptance/factor separation, packed-workspace alias map, and source-context resolver.

## Readiness gates

The program is not `ready` unless all of these agree on the same scalar domain:

1. pivot geometry is complete;
2. execution schedule has one block per scalar;
3. update relations are valid;
4. output-vector schedule is valid;
5. acceptance/factor separation is internally valid;
6. workspace alias map is valid;
7. every pivot diagonal remains uniquely resolvable through source context.

## Role

This bundle is now the stable input boundary for the next executor phase. Consumers no longer need to compose seven independent reports manually.

## Interpretation boundary

The bundle remains structural. It contains no proprietary retail RHS expression text, physical units, semantic solver variable names, or final BMW provider identity. Numeric provider execution remains a separate capture-gated step.

Run locally with:

    python specialized_provider_solver_program_runtime.py SHIFT.exe.c
