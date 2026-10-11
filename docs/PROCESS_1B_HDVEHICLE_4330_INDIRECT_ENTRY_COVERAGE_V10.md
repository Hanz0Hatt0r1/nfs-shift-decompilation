# Process 1B: HDVehicle+0x4330 indirect-entry coverage v10

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/10` supersedes `/9` by composing the target-agnostic base/index-addressed writable `.data` same-register near-transfer subset.

## Added coverage

The upstream retail machine scan contains:

- **2,847,850** decoded instructions;
- **63** exact base/index-addressed writable `.data` loads;
- **51** unique effective addresses;
- a **16-instruction** straight-line forward window;
- **0** same-register indirect `CALL/JMP` transfers;
- therefore **0** exact targets among the 15 canonical P1B carrier addresses in this subset.

## Aggregate effect

Bounded coverage classes increase from **13 to 14**. Bounded exact carrier hits remain **0**.

The navigation SQLite still reports **19,500 unresolved indirect edges**. This remains a capability/frontier metric and is not decremented by independently recovered machine subsets.

## Still fail-closed

- register copy/transform after base/indexed writable loads;
- stack spill/reload and inter-block carry;
- aliases and runtime mutation;
- external/runtime NVAPI values;
- runtime-written vtables;
- runtime-created/copied/opaque function pointers;
- generic stores/copies and runtime patching;
- global `indirect_entry_into_carriers`;
- `manager+0x374 -> HDVehicle+0x4330`;
- `0x004b86cf`/slot2;
- aggregate P1.3.

Provider count remains **7**.
