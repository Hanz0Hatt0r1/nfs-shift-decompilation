# Phase 468 — reset/cleanup storage partition (corrected)

Phase 468 originally conflated the reset function's zero writes with its unit-diagonal seed writes. Phase 479/481 corrected that interpretation.

## Correct relation

`cleanup-covered storage = reset-zero slots ∪ unit-diagonal seed slots`

The two reset sets are disjoint for the shipped providers.

Provider 0: **370** reset-zero slots + **40** unit-diagonal seed slots = **410** cleanup-covered slots.

Provider 1: **280** reset-zero slots + **34** unit-diagonal seed slots = **314** cleanup-covered slots.

The output vector is fully covered by cleanup/reset-zero state; the diagonal seed slots are workspace locations and are not themselves reset-zero writes.

## Interpretation

Cleanup establishes the broader baseline. The selector-driven reset writes zero to a subset of that baseline and writes one exact `1.0` seed for every selector case.

The corrected equality is a partition of storage domains, not a claim that reset zero writes alone reproduce cleanup.

## Scope boundary

This is storage-level evidence. It does not assign matrix semantics and does not imply that reset is a per-frame initializer.
