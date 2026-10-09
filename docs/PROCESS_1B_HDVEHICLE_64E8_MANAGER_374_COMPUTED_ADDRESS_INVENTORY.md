# Process 1B: computed `manager+0x374` address inventory

## Scope

After the literal `[base+0x374]` destination surface was closed, the remaining static class is address computation before a later access. This slice inventories explicit `.text` `LEA`/register-`ADD` materializers of `base+0x374` without inferring that the base is Participants Manager.

## Inventory

The retail PC 1.02 `.text` scan yields 22 exact `+0x374` address materializers after excluding already-inventoried literal memory destinations, `+0x3740` coincidences, `-0x374` stack/address forms, and inverse subtraction.

Twenty sites belong to ordinary code functions. Two sites (`0x00a6cfe7`, `0x00a6d067`) map to SQLite `Unwind@...` records and are separated as metadata candidates rather than promoted to executable writers.

This is a worklist, not a receiver-identity claim. A site only matters to `manager+0x374` if its base is independently proven to be Participants Manager root and the computed pointer is subsequently written through.

## Result

The explicit computed-address worklist is finite. Receiver provenance and use classification remain open for the 20 code candidates. The final `0x004b86cf` HDVehicle+0x64e8 candidate therefore remains fail-closed, as do P1.3 completion and provider removal. Provider count remains 7.
