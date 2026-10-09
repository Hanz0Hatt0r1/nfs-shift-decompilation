# Process 1D — slot3 wheel-runtime alias/callee/bulk-copy inventory

## Target and displacement correction

P1.3D still needs exact writer/value provenance for selected:

```text
HDVehicle+0x28b8
```

The retail machine proof fixes the consumer lifecycle:

```text
FUN_00758b50
  wheel runtime receiver = HDVehicle+0x400+slot*0xa80
  -> 0x00758d6b call FUN_00755950

FUN_00755950
  reads f64 [receiver +0x538]
```

Therefore slot 3 normalizes exactly as:

```text
0x400 + 3*0xa80 + 0x538 = 0x28b8
```

The first version of this exporter incorrectly scanned `+0x138`. That value came from an older contract-local decomposition and is **not** the retail instruction displacement on the `FUN_00755950` receiver. Whole-program machine scanning must use `+0x538`. This document and the tooling now enforce that correction.

The full direct-literal store surface for absolute `HDVehicle+0x28b8` is already exhausted. The remaining writer class is alias/callee/bulk-copy provenance.

## Corrected exporter

`tools/ghidra/ShiftWheelRuntimeAliasExporter.java` scans every non-external function and emits a row only when the function contains an instruction or raw p-code operation using exact machine displacement `+0x538`.

For each such function it records independent topology/context hints:

- exact `+0x400` wheel-runtime receiver-base scalar;
- exact `+0xa80` wheel stride scalar;
- exact `+0x28b8` scalar, retained only as a navigation hint;
- raw p-code classes including `STORE`, `LOAD`, `CALL`, `CALLIND`, `COPY`, `PIECE`, `SUBPIECE`, `PTRADD`, `PTRSUB`, `INT_ADD`, and `INT_MULT`;
- exact instructions where `+0x538` occurs.

Output format:

```text
SHIFT.GhidraWheelRuntimeAliasUses/1
```

The script deliberately does not equate an arbitrary object `+0x538` with the selected wheel runtime.

## Analyzer

`tools/ghidra/analyze_p1d_slot3_wheel_runtime_aliases.py` ranks the finite result set. Strong topology candidates require both:

```text
same-function +0x400 hint
same-function +0xa80 hint
```

plus at least one exact `+0x538` use in a store/address-materializer/call class.

Even a strong candidate remains candidate-only. Promotion requires all of:

1. exact base provenance to selected `HDVehicle+0x400+slot*0xa80`;
2. exact slot 3 plus `+0x538` mapping to selected `HDVehicle+0x28b8`;
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

This correction fixes the machine search displacement. It does not pretend the exporter has already been executed in this environment.

```text
correct machine displacement              = +0x538
superseded scan displacement               = +0x138
exporter ready                             = true
analyzer ready                             = true
machine inventory executed                 = false
selected HDVehicle slot3 writer proven     = false
retail input/control provenance proven     = false
P1.3 complete                              = false
provider count                             = 7
```

## Next step

Run the corrected exporter against PC retail Ghidra. If a strong candidate writes or materializes `+0x538`, recover its base back to the selected HDVehicle wheel-runtime receiver and trace the value backward. If no strong candidate writes the field, follow callees receiving a materialized alias and bulk-copy ranges covering `+0x538`.
