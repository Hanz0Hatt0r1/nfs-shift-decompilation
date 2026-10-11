# Process 1B: HDVehicle+0x4330 indirect-entry coverage v9

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/9` supersedes `/8` by composing the bounded direct-absolute writable `.data` indirect-target recovery.

## Added coverage

The new class covers the complete retail machine inventory of direct transfers through absolute writable `.data` slots:

- **334** transfers;
- **259** unique slots;
- **9** bounded internal/static candidate function values;
- exact intersection with the 15 canonical P1B carriers: **0**.

The underlying writable-data contract separates:

- 2 fixed bridge slots / 2 transfers;
- 2 callback-pair slots / 77 transfers;
- 255 NVAPI slots / 255 transfers.

The nonzero NVAPI runtime values are external `nvapi_QueryInterface` results, so they remain outside the bounded internal/static negative claim.

## Aggregate effect

Bounded coverage classes increase from **12 to 13**. Bounded exact carrier hits remain **0**.

The navigation SQLite still reports **19,500 unresolved indirect edges**. That number is retained as a capability/frontier metric rather than decremented, because the navigation index does not map its unresolved edges to the independently recovered writable-slot targets.

## Still fail-closed

- external/runtime NVAPI target identity;
- alias or indirect writers into the callback pair;
- register-loaded/base-indexed writable target provenance;
- runtime-written vtables;
- runtime-created/copied/opaque function pointers;
- generic stores/copies and runtime patching;
- global `indirect_entry_into_carriers`;
- `manager+0x374 -> HDVehicle+0x4330`;
- `0x004b86cf`/slot2;
- aggregate P1.3.

Provider count remains **7**.
