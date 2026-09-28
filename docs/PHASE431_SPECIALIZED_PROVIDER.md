# Phase 431 — specialized provider identities and sparsity signatures

Phase 431 extracts the two provider vtables from the retail PE and makes their
strict-upper-triangle acceptance signatures executable.

## Provider 0

PE vtable address: 0x00B0FC5C. Observed accessor returns: +0x04 -> 0x00c23c68, +0x08 -> 0x00c21738, +0x0c -> 0x00c21698, +0x2c -> [0x00b8d8ec]. The +0x10 helper accepts only dimension 0x28 (40), while +0x24 returns 0x4A6.

- vtable: 0x00B0FC5C
- scalar domain: 40
- init: FUN_007d2f70
- shutdown: FUN_007c6e10
- acceptance: FUN_007c6e50
- solve: FUN_007c7200
- scalar-count check: FUN_007c6e30
- +0x04: FUN_007d2eb0
- +0x08: FUN_007d2ec0
- +0x0c: FUN_007d2ed0
- +0x14 acceptance entry: FUN_007c6e50
- +0x2c: FUN_007d2f00
- +0x24 constant: 0x4A6
- +0x28 constant: 0x28

The acceptance helper contains 83 run lengths. Starting in the zero state, each
run is followed by one transition cell except the final run. This decodes to
780 strict-upper-triangle cells for a 40x40 matrix: 450 non-zero and 330 zero.

## Provider 1

PE vtable address: 0x00B0FC8C. Observed accessor returns: +0x04 -> 0x00c21588, +0x08 -> 0x00c1fe38, +0x0c -> 0x00c1fdb0, +0x2c -> [0x00b8d8f0]. The +0x10 helper accepts only dimension 0x22 (34), while +0x24 returns 0x2EA.

- vtable: 0x00B0FC8C
- scalar domain: 34
- init: FUN_007cd980
- shutdown: FUN_007cdb00
- acceptance: FUN_007cdb40
- solve: FUN_007cdfc0
- scalar-count check: FUN_007cdb20
- +0x04: FUN_007d2f10
- +0x08: FUN_007d2f20
- +0x0c: FUN_007d2f30
- +0x14 acceptance entry: FUN_007cdb40
- +0x2c: FUN_007d2f60
- +0x24 constant: 0x2EA
- +0x28 constant: 0x22

The acceptance helper contains 107 run lengths. It decodes to 561 strict-upper
cells for 34x34: 315 non-zero and 246 zero.

## Why this matters

The retail provider is not an arbitrary backend once these acceptance helpers are
considered: it advertises a fixed scalar dimension and a fixed strict-upper
sparsity pattern. The matcher therefore provides a hard structural test for a
candidate runtime matrix without inventing provider class names.

This phase deliberately does not claim that provider 0 is BMW M3 E36. That
claim requires comparing the decoded pattern against the reconstructed BMW
40-scalar matrix and, ideally, a real runtime capture.
