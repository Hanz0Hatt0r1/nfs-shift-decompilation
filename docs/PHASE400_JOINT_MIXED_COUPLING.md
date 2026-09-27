# Phase 400 — JOINT mixed matrix coupling

`FUN_007bbb80` is the remaining JOINT-centric matrix kernel. It consumes the body tensor at `+0xb0`, body inverse scalar at `+0x90`, and JOINT records at `+0x160` with stride `0x40`.

## JOINT self block

For each JOINT, nine tensor/position intermediates are formed. They produce the six lower-triangle entries of the 3×3 self block; the diagonal entries include the body inverse scalar. The block is added to the row-pointer matrix at the JOINT scalar base `+0x30`.

## JOINT/JOINT

Later JOINTs produce a full 3×3 pair block. The source computes `d7/d9/d8`, `d13/d11/d20`, `d17/d16/d14` and stores the block against the lower triangle selected by scalar-base ordering. Equal side flags add; differing flags subtract.

## JOINT/HINGE

A HINGE contributes a 3×2 block from its angular rows `+0x48/+0x50/+0x58` and linear rows +0x60/+0x68/+0x70`, using scalar base `+0x94`. The source has two orientations depending on base ordering.

## JOINT/BAR

A BAR contributes a 3×1 block from point `+0x18/+0x20/+0x28` and direction `+0x40/+0x48/+0x50`, using scalar base `+0x30`. The same equal/different side rule and lower-triangle ordering apply.

All four paths write into the per-body row-pointer table at `+0x158`; this phase deliberately keeps the body tensor and accumulator fields as storage-level constructs.
