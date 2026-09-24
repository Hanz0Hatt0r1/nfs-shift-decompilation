---
name: ghidra
description: >-
  Evidence-driven Ghidra workflow for Need for Speed: SHIFT: headless analysis,
  decompiler/source correlation, function anchors, call-chain extraction, and
  machine-readable artifacts. Use for SHIFT.exe, Ghidra C exports, function
  address analysis, runtime ABI hypotheses, or batch binary analysis.
---
# Ghidra workflow for SHIFT

Use the upstream headless workflow as an implementation reference, but keep the
project's evidence policy stricter: a decompiler observation is source evidence,
not a runtime proof.

## Workflow

1. Start from the exact binary/decompiler export and record SHA-256, architecture,
   and source line anchors.
2. Extract functions/call relationships before proposing semantics.
3. Correlate a function with its caller, callee, vtable slot, and data object.
4. Preserve ambiguous table contents as opaque; do not infer missing initializer bytes.
5. Emit JSON evidence with provenance so later captures can be joined mechanically.
6. When a runtime capture exists, keep static-source and runtime-instance evidence
   as separate layers and correlate them only through explicit identity fields.

## SHIFT-specific anchors

Important recovered paths include `FUN_00854e70` (declaration conversion),
`FUN_00859800` (binary MEB descriptor loader), `FUN_00830f80`
(canonicalization/CreateVertexDeclaration) and `FUN_0082e510` (SetVertexDeclaration
wrapper). These are source anchors already represented by project evidence modules.

## References

Upstream Ghidra headless skill: https://github.com/mitsuhiko/agent-stuff/blob/main/skills/ghidra/SKILL.md
