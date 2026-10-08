# Process 1B — constant-assisted indexed +0x4330 synthesis closure

The previous simple-affine scan is extended to expressions with one unknown pointer origin plus proven constant registers. It propagates representable `mov`, register/immediate `add/sub`, and indexed `lea [base+index*scale+disp]` expressions inside straight-line regions and resets at call/jump/ret or unrecognized writes.

Across 181,901 symbolic transitions, including 152 register/index-assisted transitions, `base+0x4330` is produced only at the four already-proven runtime materializers and the known compiler unwind cleanup. No hidden constant-assisted indexed materializer exists in this bounded class.

Two independent unknown origins, cross-control-flow phi-style equivalence, and opaque/external pointers remain open. Manager `+0x374` identity and literal `0x004b86cf` remain fail-closed; provider count remains 7.
