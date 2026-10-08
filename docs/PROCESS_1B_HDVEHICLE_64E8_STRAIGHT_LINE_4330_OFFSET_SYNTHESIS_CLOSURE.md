# Process 1B — straight-line +0x4330 offset synthesis closure

A whole-retail `.text` symbolic scan tracks simple per-register affine expressions across `mov reg,reg`, `lea reg,[reg+/-imm]`, immediate `add/sub`, and `inc/dec`. State is reset on call/jump/ret and on unrecognized register overwrites, so this is a bounded straight-line proof rather than a whole-program equivalence claim.

Across 181,525 tracked affine transitions, `base+0x4330` is produced only five times: the four already-proven runtime materializers and `Unwind@00a7063f`. Every production is a single-step `+0x4330`; there are zero hidden multi-step simple-affine productions.

Indexed two-origin LEA, cross-control-flow synthesis, opaque helper returns, and externally supplied pointers remain open. Manager `+0x374` identity and literal `0x004b86cf` remain fail-closed; provider count remains 7.
