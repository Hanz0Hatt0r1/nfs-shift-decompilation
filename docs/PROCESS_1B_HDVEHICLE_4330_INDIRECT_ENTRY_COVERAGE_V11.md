# Process 1B: HDVehicle+0x4330 indirect-entry coverage v11

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/11` supersedes `/10` by composing the shared P1.3A exact mov-based stack spill/reload propagation result into the P1B aggregate indirect-entry frontier.

## Added coverage

The authoritative PC retail 1.02 machine scan covers the same 63 base/index-addressed writable `.data` loads used by the previous near-transfer subset. Within the bounded 16-instruction propagation window it finds:

- **2** exact EBP/ESP-relative stack spills;
- **0** exact stack reloads;
- **0** reload-derived indirect `CALL/JMP` transfers;
- **0** surviving-taint indirect transfers;
- therefore **0** exact targets among the 15 canonical P1B carrier addresses in this added subset.

The two spills are:

- `0x004da33e` / effective address `0x00b82304` -> `0x004da344 [ebp-0x28]`, ECX, untransformed;
- `0x009f71a8` / effective address `0x00bac6e0` -> `0x009f71c3 [esp+0x8]`, EAX, transformed.

## Aggregate effect

Bounded coverage classes increase from **14 to 15**. Bounded exact carrier hits remain **0**.

The navigation SQLite still reports **19,500 unresolved indirect edges**. This remains a capability/frontier metric and is not decremented by independently recovered machine subsets.

## Still fail-closed

- implicit `push`/`pop` carriers;
- normalized ESP-delta stack carriers;
- inter-block/phi carry;
- memory aliases and runtime mutation;
- runtime-created/copied/opaque function pointers;
- generic stores/copies and runtime patching;
- global `indirect_entry_into_carriers`;
- `manager+0x374 -> HDVehicle+0x4330`;
- `0x004b86cf` / P1.3.slot2;
- aggregate P1.3.

Provider count remains **7**.

## Next step

Bound implicit/normalized stack carriers and then inter-block carry for base/index-derived writable values. Do not promote the global indirect-entry, manager identity join, slot2, or aggregate P1.3 gates from this negative bounded subset.
