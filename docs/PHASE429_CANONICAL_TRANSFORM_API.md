# Phase 429 — canonical transform-helper API

Phase 429 consolidates the transform helper pair so that the repository has one executable source of truth.

## Canonical functions

- FUN_007af0a0 -> transform_fun_007af0a0
- FUN_007aefb0 -> transform_fun_007aefb0

Both functions consume the same nine float coefficients. Their coefficient orderings are preserved exactly from the retail instruction stream.

The older transform_vector function remains an alias of FUN_007af0a0 for compatibility with earlier phases.

## SDF integration

sdf_transform_runtime.py is now an adapter over the canonical implementation instead of a second copy of the arithmetic.

sdf_body_frame_runtime.py likewise uses the canonical pair. Its established semantic chain remains:

    FUN_007af0a0 -> component-wise scale -> FUN_007aefb0

The project therefore no longer has independent formulas that could drift apart.

## Why the names stay explicit

One earlier layer described the coefficient orderings as forward/transposed, while another used forward/transpose in the opposite semantic sense. The raw retail function names are now the canonical identifiers; semantic coordinate conventions remain deliberately unnamed until caller/context evidence proves them.
