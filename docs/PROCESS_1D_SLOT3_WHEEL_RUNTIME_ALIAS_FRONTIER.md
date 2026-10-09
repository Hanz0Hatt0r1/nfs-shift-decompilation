# Process 1D — slot3 wheel-runtime alias/callee/bulk-copy frontier

## Scope

P1.3D still needs exact writer/value provenance for selected `HDVehicle+0x28b8` consumed by `FUN_00755950`.

Existing retail machine proof fixes the consumer topology:

```text
FUN_00758b50 -> FUN_00755950
this = HDVehicle + 0x400 + slot*0xa80
consumer field = wheel-runtime +0x138
slot 3 absolute field = HDVehicle+0x28b8
```

The direct-literal writer surface for `+0x28b8` is exhausted, so the remaining writer classes are alias/callee/bulk-copy.

## New tooling

`tools/ghidra/ShiftWheelRuntimeAliasExporter.java` exports every function with an exact `+0x138` instruction or p-code constant use and records same-function topology/context hints:

- `+0x400` wheel-runtime base;
- `0xa80` wheel stride;
- `+0x28b8` absolute scalar occurrence;
- STORE / LOAD;
- CALL / CALLIND;
- COPY / PIECE / SUBPIECE;
- PTRADD / PTRSUB / INT_ADD / INT_MULT.

`tools/ghidra/analyze_p1d_slot3_wheel_runtime_aliases.py` ranks those rows so the exact consumer lifecycle and likely writer/forwarding sites are reviewed first.

## Authority boundary

This inventory is navigation evidence only.

A function that uses `+0x138` is not thereby proven to operate on selected `HDVehicle`. Likewise, seeing `+0x400`, `0xa80`, or `+0x28b8` in the same function does not establish object identity. Promotion requires all of:

1. exact base provenance to selected `HDVehicle+0x400+slot*0xa80`;
2. exact slot-3 normalization to `HDVehicle+0x28b8`;
3. exact f64/qword write, or a bulk-copy interval that covers the target field;
4. backward value provenance to the retail producer before assigning semantics.

## Workflow

```text
ShiftWheelRuntimeAliasExporter.java out/p1d_slot3_wheel_runtime_aliases.jsonl
python3 tools/ghidra/analyze_p1d_slot3_wheel_runtime_aliases.py \
  out/p1d_slot3_wheel_runtime_aliases.jsonl \
  --output out/p1d_slot3_wheel_runtime_alias_inventory.json
```

Inspect `strong_topology_candidates` first, then the remaining ranked writer/copy/address-materializer rows.

## Gate

```text
alias/callee/bulk-copy exporter ready      = true
retail candidate inventory captured        = false until exporter is run on PC retail 1.02
selected HDVehicle root provenance complete= false
exact f64 slot3 writer proven              = false
P1.3D complete                             = false
provider count                             = 7
```

No semantic name is assigned to `HDVehicle+0x28b8` from numeric proximity alone.
