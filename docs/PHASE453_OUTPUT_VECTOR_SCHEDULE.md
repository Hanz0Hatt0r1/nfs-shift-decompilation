# Phase 453 — specialized-provider output-vector schedule

## Goal

Phase 453 isolates all assignments whose destination lies in the provider output vector and records their source-order dependencies.

Each expanded assignment carries the pivot index, source line, optional loop index, output destination index, and output/workspace/global RHS reference counts. Output-to-output reads are additionally collapsed into a deduplicated dependency edge set.

## Retail audit

The local retail source contains 84 output-vector destination stores in `FUN_007c7200` and 73 in `FUN_007cdfc0`. All output indices remain inside their 40- and 34-scalar domains.

The final pivot block is represented separately as `terminal-output`; non-terminal output stores are `forward-output`. These labels describe source position only.

## Reconstruction value

This layer separates right-hand-side propagation from packed workspace mutation. The provider solver IR can therefore model:

`pivot -> workspace update relations`
`pivot -> output-vector update relations`

without assigning physical meaning to the vector components.

## Scope boundary

No physical quantity, unit, semantic solver variable name, or provider class identity is inferred. Numeric coefficients remain outside the repository.

Run locally with:

    python specialized_provider_output_schedule_runtime.py SHIFT.exe.c
