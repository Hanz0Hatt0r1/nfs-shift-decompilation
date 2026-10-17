# Process 1B / P1.3B — address-taken orphan function recovery

This batch continues the bounded recovery of the 60 exact Ghidra callsites that
had no caller-function owner. The earlier wrapper batch restored 15 callers.
The new pass checks code-pointer references, instruction ownership, contiguous
bodies, P-code, branch destinations and the final instruction before creating
functions in the separate Ghidra project copy
`shift-recovered-mass-20261017`.

Three bodies met that evidence bar:

- `FUN_00910aa5` follows a terminal `RET`, has two exact code-address
  references, and ends at `0x00911394 RET`. Its 703 instructions contain
  26 call instructions; every jump destination stays inside the body. Two
  orphan direct calls at `0x00910d62` and `0x009112e7` now have this caller.
- `FUN_00a9a86e` is a two-instruction address-taken body ending at
  `JMP 0x0092e065`. The jump destination remains an unowned code address, so no
  destination name or behavior is inferred.
- `FUN_00a9a878` is the adjacent address-taken body after that tail transfer.
  Its six instructions end at `0x00a9a88d RET`; the orphan direct call at
  `0x00a9a87d` now has this caller.

All eight instructions in the two adjacent table entries and all 703
instructions in `FUN_00910aa5` were unowned in the original project. Ghidra
exports from the copy confirm the exact function sizes, instruction bytes,
P-code rows, and recovered callsite owners. The new batch adds three functions,
711 instructions and 711 P-code rows. Combined with the earlier target and
wrapper batches, the corpus now contains 762 unique function bodies, 111,472
instructions and 111,288 P-code rows. Of the 60 exact orphan callsites, 18 now
have recovered caller owners; 42 remain unresolved.

The compact, hash-pinned report is
[`evidence/p1b_address_taken_orphan_function_recovery.json`](../evidence/p1b_address_taken_orphan_function_recovery.json).
Raw instruction, metadata and reference exports remain outside Git. The
original Ghidra project was opened read-only; the recovered functions exist in
the isolated project copy. Names remain Ghidra-style `FUN_<address>` labels,
and the P1.3 control-producer gate remains false.

To reproduce the Ghidra mutation, run the recovery script only against an
isolated project copy of the pinned retail program:

```bash
GHIDRA_HOME=/opt/ghidra tools/ghidra/run_p1b_address_taken_recovery.sh \
  /path/to/isolated/project shift SHIFT.exe /tmp/address-taken-functions.tsv
```

The script fails closed if the executable, data references, instruction bytes,
function boundaries, existing ownership, P-code or callsite targets drift.
