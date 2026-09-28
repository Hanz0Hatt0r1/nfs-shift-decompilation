# Phase 420 — JOINT `d15` source correction

A direct audit of the full retail `SHIFT.exe.c` snapshot found that the JOINT tensor intermediate `d15` was mapped incorrectly in the Phase 410/400 implementation.

The retail expression is:

`d15 = m00*y - m01*x`

with `m00` at `+0xb0` and the symmetric `m01` slot at `+0xbc`. The previous implementation used `m02` (`+0xb8`), which only escaped detection because earlier regression fixtures used diagonal/identity tensors.

A non-degenerate tensor `[[2,3,4],[3,5,6],[4,6,7]]` with point `(1,2,3)` produces `d15 = 1`, while the incorrect `m02` mapping would produce `4`. The new regression locks this distinction.

No other JOINT tensor intermediates are changed by this phase.
