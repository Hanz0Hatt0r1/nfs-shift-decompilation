# Process 1A / P1.3A — slot0/slot1 topology alias frontier

## Blocker

After the exact absolute-displacement subset and the literal wheel-local `+0x538` materializer subset were closed, selected-root provenance for `HDVehicle+0x938` and `HDVehicle+0x13b8` still has two open mechanism classes:

- aliases that reach the same bytes without embedding literal `+0x538`;
- overlapping bulk-copy / memory-initialization destinations.

Searching only for `0x538`, `0x938`, or `0x13b8` cannot exhaust that surface.

## New inventory layer

`ShiftP13ASlot01TopologyAliasExporter.java` broadens the search around the proven wheel topology instead of the target displacement. It emits functions only when the same function contains both:

- wheel-runtime base hint `+0x400`;
- wheel stride hint `+0xa80`.

For each such function it records STORE/LOAD/CALL/CALLIND/COPY/PIECE/SUBPIECE and address-arithmetic p-code plus instruction text. Literal `+0x538`, `0x938`, and `0x13b8` are retained only as ranking/context flags.

`analyze_p1a_slot01_topology_aliases.py` prioritizes rows that do **not** contain literal `+0x538`, because the exact literal subset is already bounded by `SHIFT.P1A.P13ASlot01Wheel538ForwardingFrontier/1`.

## Evidence boundary

This is a candidate-inventory layer, not a semantic closure. Same-function `+0x400/+0xa80` constants can occur in unrelated layouts, so every positive candidate still requires:

1. exact selected-HDVehicle root provenance;
2. normalization to slot0 `HDVehicle+0x938` or slot1 `HDVehicle+0x13b8`;
3. an f64/qword write or bulk-copy/memory-init range that covers the target bytes;
4. callee and backward value provenance before producer semantics are assigned.

The authoritative PC retail machine image remains the semantic authority. The Drive Ghidra SQLite/index artifacts are acceleration/navigation inputs.

## Gate

```text
exporter/analyzer ready                  = true
authoritative machine inventory captured = false
slot0 complete                           = false
slot1 complete                           = false
P1.3 complete                            = false
provider count                           = 7
```

## Next step

Run the exporter against authoritative PC retail 1.02 Ghidra, analyze the nonliteral `+0x538` candidates first, and adjudicate exact selected-root and target-range write coverage. If the topology inventory still leaves no writer, widen only then to interprocedural aliases whose caller owns the wheel base/stride derivation.