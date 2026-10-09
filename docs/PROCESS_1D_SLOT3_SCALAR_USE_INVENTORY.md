# Process 1D — P1.3D slot3 `HDVehicle+0x28b8` scalar-use inventory

## Blocker

P1.3D still needs the exact writer/value provenance for slot3 consumed by `FUN_00755950`:

```text
HDVehicle+0x28b8
```

The existing full-PC-retail direct-store scan is already exhausted: there are **zero** direct literal stores to `+0x28b8`. Repeating direct `[root+0x28b8]` store search therefore cannot advance this blocker.

## New bounded search surface

This change adds two tools:

- `ShiftScalarUseExporter.java` — scans the Ghidra program for instructions containing an exact scalar value and emits the containing function/instruction/operand plus a coarse usage class;
- `analyze_p1d_slot3_scalar_uses.py` — consumes the exact `0x28b8` rows and groups the candidate functions, with address-materializers separated for priority adjudication.

The intended headless flow is:

```text
ShiftScalarUseExporter.java out/p1d_slot3_28b8.jsonl 0x28b8
python3 tools/ghidra/analyze_p1d_slot3_scalar_uses.py \
  out/p1d_slot3_28b8.jsonl \
  --output out/p1d_slot3_28b8_inventory.json
```

## Evidence boundary

This is **candidate inventory only**.

An instruction containing scalar `0x28b8` is not automatically:

- selected `HDVehicle+0x28b8`;
- a writer;
- the qword/f64 producer consumed by `FUN_00755950`;
- even a memory displacement rather than an unrelated arithmetic constant.

Promotion requires exact receiver/root provenance plus write/forwarding-width proof. Numeric offset equality remains explicitly non-semantic.

## Next step

Run the exporter against authoritative PC retail 1.02, then adjudicate the finite address-materializer/forwarding candidate set one-by-one. Any candidate that cannot prove selected-HDVehicle receiver identity is rejected; only a candidate that also proves the qword/f64 value path may close P1.3 slot3.
