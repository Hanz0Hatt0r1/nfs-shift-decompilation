# Process 1B — exact carrier source-symbol address-taking surface

This contract bounds how the canonical 15 P1B exact `HDVehicle+0x4330` carrier symbols appear in the hash-pinned PC retail 1.02 Ghidra C export.

Across all 15 symbols there are exactly **40** textual symbol occurrences. Every occurrence is immediately followed by `(` after optional whitespace. In the decompiler export this is the grammar used by function definitions and direct invocations. There are no source-visible occurrences where an exact carrier symbol is used as a value, assigned/stored, passed as a bare callback value, or explicitly address-taken.

```text
exact carrier symbols = 15
total symbol occurrences = 40
call/definition-form occurrences = 40
non-call symbol-as-value occurrences = 0
source-visible address-taken carrier symbols = 0
```

## Reproduce

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_source_symbol_address_taking.py \
  /path/to/SHIFT.exe.c \
  --output evidence/p1b_hdvehicle_4330_source_symbol_address_taking.json
```

The analyzer pins the source SHA-256, per-symbol occurrence counts and total count. It fails closed if any exact carrier gains a reference whose next non-whitespace character is not `(`.

## What this proves

Within the source-visible symbol-reference surface, no exact carrier is directly materialized as a function-pointer value. This complements the already merged whole-image VA/RVA literal and static-table negative evidence.

## What it does not prove

This does **not** close the global generic function-pointer gate. It cannot rule out:

- computed or reconstructed code pointers;
- copied or encoded function pointers;
- raw address literals hidden by decompiler recovery;
- table-derived pointers not emitted using the exact function symbol;
- runtime-patched storage;
- opaque indirect dispatch.

Therefore `generic_function_pointer_stores_copies_ruled_out`, `computed_or_encoded_code_pointers_ruled_out`, `runtime_callback_registration_ruled_out`, and `indirect_entry_into_carriers_ruled_out` all remain false. Manager identity, final `0x004b86cf`, aggregate P1.3 and provider count are unchanged; provider count remains 7.
