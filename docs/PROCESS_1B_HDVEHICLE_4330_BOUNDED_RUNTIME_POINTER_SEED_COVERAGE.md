# Process 1B: bounded runtime pointer-seed coverage

This aggregate composes the current seven non-resolver exact-carrier seed/materialization classes with the fully bounded statically reachable imported-`GetProcAddress` result-storage surface.

## Inputs

- `SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4`
- `SHIFT.P1B.HDVehicle4330GetProcAddressStorageCoverage/1`

## Result

- canonical P1B carriers: **15**;
- non-resolver bounded seed classes: **7**;
- exact carrier hits across those seven classes: **0**;
- statically reachable imported-`GetProcAddress` callsites: **101**;
- exact internal carrier identities in their bounded result storage: **0**;
- composed bounded seed domains: **8**;
- composed exact carrier hits: **0**.

This means the bounded seed domains currently enumerated cannot produce an exact internal P1B carrier pointer for later copying or indirect entry.

## Gate discipline

Promoted only:

- `bounded_runtime_pointer_seed_domains_composed=true`;
- `bounded_runtime_pointer_seed_can_produce_exact_internal_carrier=false`.

This is not a global function-pointer copy theorem. Runtime-created resolver aliases, unrelated runtime-populated pointer tables, cross-block/table-derived arithmetic, runtime patching, opaque external pointer sources, global indirect entry, manager+0x374 identity, `0x004b86cf`, and P1.3 remain fail-closed. Provider count remains 7.
