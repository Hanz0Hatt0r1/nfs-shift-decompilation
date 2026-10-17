# Process 1B / P1.3B — bounded orphan wrapper function recovery

The earlier target-body batch left 94 linear-sweep callsites without an exact
Ghidra callgraph edge. A read-only Ghidra address/instruction pass found 60
exact `CALL` instructions with matching unconditional call references. Their
caller addresses had no owning function in the original Ghidra project. The
other 34 addresses were not Ghidra instruction starts; one lies inside an
existing thunk body, and 32 point to addresses outside the program's memory
map.

Fifteen of the 60 orphan callers meet a bounded wrapper rule: the entry is the
instruction immediately after a terminal `RET`, the body is contiguous and
straight-line, it contains exactly one direct `CALL`, and it ends at the next
`RET`. Each entry also has an exact Ghidra data reference from an instruction
that stores that code address. The original project had no function at or
containing any of the 15 entries.

Those 15 functions were added as `FUN_<address>` in the separate Ghidra project
copy `shift-recovered-mass-20261017`. A fresh reference export from that copy
now assigns every recovered callsite to its exact caller function. The bodies
contain 137 instructions and 137 P-code rows. This raises the direct-callee
recovery batch from 744 to 759 unique function bodies, with 110,761 unique
instructions and 110,577 P-code rows.

The compact hash-pinned result is
[`evidence/p1b_orphan_wrapper_function_recovery.json`](../evidence/p1b_orphan_wrapper_function_recovery.json).
The raw instruction, reference, and slice exports remain outside Git.

No semantic names or behavior claims are assigned. The other 45 exact orphan
callsites remain candidates until their function boundaries meet the same
evidence bar. The P1.3 control-producer gate remains false.
