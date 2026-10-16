# Targeted Ghidra address-reference export

The Shift global-reference runner uses the shared revenginstr address-reference
exporter when present and adapts its JSONL rows to the existing
SHIFT.GhidraGlobalReferences/1 contract. The local
ShiftGlobalReferenceExporter.java remains available as a fallback.

The adapter preserves the Shift row fields and reference ordering consumed by
the current validator and analyses. Generic reference-source and memory-block
metadata stay in the revenginstr schema and do not change the Shift contract.
