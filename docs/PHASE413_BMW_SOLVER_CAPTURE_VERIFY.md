# Phase 413 — BMW M3 solver capture verification

The capture pipeline now has a BMW-specific structural gate for the real `aarm_multilink.sdf` domain.

## Fixed domain

The verifier expects the source-backed BMW shape: 11 bodies, 24 source constraint records, 28 runtime constraint records, 40 scalar solver nodes, a 40×40 matrix (1600 double cells / 12,800 bytes) and a 40-entry row-pointer table (160 bytes).

## Two validation modes

Structural verification checks scalar count, matrix dimensions, retail row-index layout and optional runtime identity-node evidence. It reports matrix non-zero support diagnostically because later coefficient arithmetic and identity resets can change individual cells.

Pair verification delegates actual values to the Phase 411 cell-level comparator. It is the numerical gate only when a real expected solver frame is supplied.

No expected numeric BMW solver frame is fabricated by this phase.