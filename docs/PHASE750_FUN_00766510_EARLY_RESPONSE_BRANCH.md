# Phase 750 — FUN_00766510 early response state

Phase 750 consumes the positive Process 1 ownership contract for the early FUN_00766510 response branch rooted at `HDVehicle+0x3b08/+0x3b20`.

The native slice models only source-backed state:

- setup clamp storage at `+0x3b00`;
- application vector at `+0x3b08/+0x3b10/+0x3b18`;
- six-entry `0x18`-stride table rooted at `+0x3b20`;
- persistent `+0x3ae8 = +0x37b8 * s + +0x37b0`, refreshed by `FUN_00756b60` with selector `+0x3c90`;
- runtime overwrite of the sixth-entry third lane `+0x3ba8` immediately before the table evaluator.

The runtime formula is preserved exactly as established by the ownership evidence:

`+0x3ba8 = +0x3af0 * 0.5 * clamped_pair_sum + +0x3ae8 + abs(pair_delta) * +0x3af8`.

The exact clamp algorithm is not inferred. The native API therefore accepts the already-clamped pair sum and the pair delta explicitly. Coefficients `+0x3af0` and `+0x3af8` also remain explicit inputs instead of being promoted to setup constants without ownership evidence.

The setup table is copied before runtime materialization. Only entry six lane Z (`+0x3ba8`) is overwritten, preserving the proof that the complete table is not a setup constant.

Phase 750 does not internalize `FUN_007551e0`, the BODY application, the direct caller accumulator write, or any later/optional branch. `contact_response` remains external and the provider count remains seven.
