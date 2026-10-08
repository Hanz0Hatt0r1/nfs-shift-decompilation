# Process 2 P2.4 — `FUN_00765c40` bounded state tail

## BLOCKER

P2.4 continues internalizing the residual `FUN_00765c40` pass after the merged contact-array sweep. The remaining direct machine-write inventory includes a bounded four-store state block at `+0x3660..+0x3678`.

## INPUT

`SHIFT.Fun00765c40DirectMachineWriteSurface/1` proves:

```text
0x007661ac -> byte  HDVehicle+0x3660 = 1
0x00766381 -> qword HDVehicle+0x3668
0x0076638a -> qword HDVehicle+0x3670
0x0076639b -> dword HDVehicle+0x3678
```

The destination geometry, widths and the `+0x3660` literal are positive. The exact branch predicate and computed values for `+0x3668/+0x3670/+0x3678` are not promoted by the current handoff.

## OUTPUT

Adds `SHIFT.Fun00765c40BoundedStateTail/1`.

The native API accepts an explicit `write_block_executed` input. A false value produces no commit. A true value produces the proven `+0x3660 = 1` byte and preserves the source-computed qword/qword/dword payloads bit-for-bit.

This models the source-visible mutation surface without inventing a branch condition, floating-point interpretation, units, or semantic field names.

## GATES_CHANGED

- four direct state-tail destinations are native-owned;
- skipped execution remains observable as no commit;
- the literal byte write is internalized exactly;
- the three computed payloads remain explicit opaque inputs;
- branch predicate remains external;
- complete `FUN_00765c40` internalization remains false;
- top-level provider remains present;
- external provider count remains 7.

## LIMITS

This slice does not claim why the write block executes, does not reinterpret the qword/dword payloads, and does not join the following BODY accumulator work prematurely.

## TESTS

`shift_runtime_fun_00765c40_bounded_state_tail_check` verifies skipped/executed behavior, the literal byte and bit-preserving payloads. Python regression cross-checks the exact sites, widths, evidence scope and provider-removal gate.

## NEXT_STEP

Consume the optional BODY accumulator sweep and remaining runtime computations in retail order. Remove the top-level `FUN_00765c40` callback only after end-to-end native execution preserves every proven side effect.
