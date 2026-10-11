# Process 1B: HDVehicle+0x4330 source-slot exact address surface

## Result

Whole-image little-endian dword scanning on PC retail 1.02 closes the exact/literal address surface for the two source slots feeding the positive memory-derived calls.

### `0x00b83dc0`

Exactly **4** raw dword occurrences exist, all in `.text` immediates:

- `0x00552f59`: exports the slot address through an output pointer;
- `0x00553229`: loads the address as the base of the four-object indirect-call loop;
- `0x00553a62`: loads the address as the base of the four-object direct-method loop;
- `0x00a79b0d`: exact initializer write destination.

The exact alias getter `0x00552f50` has exactly two direct callsites, `0x008df2cf` and `0x008dfc06`, and its function address has **0** raw dword occurrences in the retail image.

### `0x00b83ec0`

Exactly **2** raw dword occurrences exist:

- `0x00553649`: exports the slot address through an output pointer;
- `0x00553b62`: loads the address as the base of the 41-object direct-method loop.

The exact alias getter `0x00553640` has exactly one direct callsite, `0x008df037`, and its function address also has **0** raw dword occurrences.

## Aggregate effect

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/16` increases bounded coverage classes from **19 to 20**. This removes unknown exact/literal address seeds from the selected source-slot alias frontier.

## Boundary

This is not a computed-alias or runtime-writer closure. Copied pointers, arithmetic reconstruction, runtime-created aliases, and caller-side write/escape semantics remain open. Exact runtime call-target identity, global incoming indirect entry, the manager+0x374 identity join, slot2 `0x004b86cf`, and aggregate P1.3 remain fail-closed. Provider count remains **7**.

## Next

Classify the three direct alias-getter caller paths for read/write/escape behavior, then continue computed alias and runtime writer provenance.
