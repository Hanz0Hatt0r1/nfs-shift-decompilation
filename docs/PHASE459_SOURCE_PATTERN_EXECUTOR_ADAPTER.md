# Phase 459 — source-pattern numeric executor adapter

## Goal

Phase 459 connects the retail-source factor extractor to the experimental numerical executor without coupling either layer to proprietary source text.

## Pipeline

`SHIFT.exe.c`
→ source factor extractor
→ `(pivot,column)` factor edge contract
→ dense-factor support admissibility gate (Phase 458)
→ sparse-guided numeric executor (Phase 457)

The adapter also enforces sequential factor rows and deduplicates edge records.

## Safety boundary

The numerical solve is **not** allowed to start merely because the retail factor pattern was extracted. The supplied logical matrix must first produce exactly the same dense `LDLᵀ` factor support.

This makes the adapter fail closed when the logical matrix, factor pattern, or reconstruction assumptions disagree.

## Interpretation boundary

The adapter does not translate packed workspace addresses into a logical matrix automatically. That work remains represented by the source-context and alias layers. It also does not claim that the experimental executor is binary-identical to the retail solver.

Provider 0/1 masks remain source-derived candidates until a real runtime matrix passes the admissibility gate.

Run locally with:

    python specialized_provider_source_pattern_executor_adapter_runtime.py SHIFT.exe.c
