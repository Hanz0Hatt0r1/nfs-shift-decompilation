# Phase 445 — specialized-provider execution schedule

## Goal

Phase 445 records the source-order execution schedule around every reciprocal pivot in the two specialized provider solvers.

Each pivot block begins at the unique reciprocal recovered in Phases 436–437. Subsequent assignment sites are classified structurally as factor normalization, forward RHS handling, generic workspace/global update, or terminal back-substitution.

## Important correction

The retail code does **not** guarantee one simple `factor → RHS → diagonal` sequence for every pivot. Some blocks contain several interleaved subloops. Phase 445 therefore preserves the observed event order instead of collapsing it into an invented phase sequence.

## Evidence boundary

Output-vector destinations are separated from workspace/global destinations. The final pivot block is treated as the terminal back-substitution region. Workspace updates are deliberately kept neutral because retail provider storage reuses packed addresses across logical stages and the row/cell mapping is not yet proven.

Workspace packing is deliberately not reinterpreted. In particular, the Phase 435 row-pointer spans are storage topology, while the logical meaning of individual packed cells remains unresolved.

## Retail audit

The local supplied `SHIFT.exe.c` contains exactly 40 pivot blocks for `FUN_007c7200` and 34 pivot blocks for `FUN_007cdfc0`. The terminal blocks are the only blocks classified as back-substitution regions.

## Role in reconstruction

The execution schedule is the temporal layer joining Phases 440–444:

`pivot -> source-order event -> destination address -> dependency/operator metadata`

This will be used to reconstruct the fixed-layout provider execution without copying proprietary retail expressions.

Run locally with:

    python specialized_provider_execution_schedule_runtime.py SHIFT.exe.c
