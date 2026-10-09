# Process 1D — slot3 wheel-runtime alias/callee/bulk-copy inventory

## Target

P1.3D still needs exact writer/value provenance for selected:

```text
HDVehicle+0x28b8
```

The retail machine proof already fixes the consumer lifecycle:

```text
FUN_00758b50
  wheel runtime = HDVehicle+0x400+slot*0xa80
  -> 0x00758d6b call FUN_00755950

FUN_00755950
  reads f64 [wheel runtime +0x138]
```

For slot 3, `0x400 + 3*0xa80 + 0x138 = 0x28b8`.

The full direct-literal store surface for `HDVehicle+0x28b8` is already exhausted. The remaining writer class is alias/callee/bulk-copy provenance.

## New exporter

`tools/ghidra/ShiftWheelRuntimeAliasExporter.java` scans every non-external function and emits a row only when the function contains an instruction or raw p-code operation using exact per-wheel offset `+0x138`.

For each such function it also records independent topology/context hints:

- exact `+0x400` wheel-runtime base scalar;
- exact `+0xa80` wheel stride scalar;
- exact `+0x28b8` scalar, retained only as a navigation hint;
- raw p-code classes including `STORE`, `LOAD`, `CALL`, `CALLIND`, `COPY`, `PIECE`, `SUBPIECE`, `PTRADD`, `PTRSUB`, `INT_ADD`, and `INT_MULT`;
- the exact instructions where `+0x138` occurs.

Output format:

```text
SHIFT.GhidraWheelRuntimeAliasUses/1
```

The script deliberately does not equate an arbitrary object `+0x138` with the selected wheel runtime.

## Analyzer

`tools/ghidra/analyze_p1d_slot3_wheel_runtime_aliases.py` ranks the finite result set. Strong topology candidates require both:

```text
same-function +0x400 hint
same-function +0xa80 hint
```

plus at least one exact `+0x138` use in a store/address-materializer/call class.

Even a strong candidate remains candidate-only. Promotion requires all of:

1. exact base provenance to selected `HDVehicle+0x400+slot*0xa80`;
2. exact slot 3 mapping to selected `HDVehicle+0x28b8`;
3. qword/f64 store width, or a proven bulk-copy range covering the target eight bytes;
4. backward value provenance to an exact PC-retail producer.

`+0x28b8` scalar equality on an unrelated object is never sufficient.

## Headless flow

Run on the authoritative PC retail 1.02 Ghidra project:

```text
ShiftWheelRuntimeAliasExporter.java out/p1d_slot3_wheel_runtime_aliases.jsonl
python3 tools/ghidra/analyze_p1d_slot3_wheel_runtime_aliases.py \
  out/p1d_slot3_wheel_runtime_aliases.jsonl \
  --output out/p1d_slot3_wheel_runtime_alias_inventory.json
```

Then adjudicate `strong_topology_candidates` against exact receiver/data flow before changing any gate.

## Current gate

This change builds the missing machine inventory path; it does not pretend the exporter has already been executed in this environment.

```text
exporter ready                         = true
analyzer ready                         = true
machine inventory executed             = false
selected HDVehicle slot3 writer proven = false
retail input/control provenance proven = false
P1.3 complete                          = false
provider count                         = 7
```

## Next step

Run the exporter against PC retail Ghidra. If a strong candidate writes or materializes `+0x138`, recover its base back to the selected HDVehicle wheel-runtime expression and trace the value backward. If no strong candidate writes the field, follow callees receiving a materialized alias and bulk-copy ranges covering `+0x138`.
