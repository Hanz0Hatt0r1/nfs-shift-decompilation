# Phase 519 — FLAT runtime index table links

Phase 519 records the runtime table geometry driven by the FLAT direct-record index field.

## Source evidence

`FUN_006af330` allocates:

- a primary table with `0x28`-byte entries;
- a secondary table with `0x40`-byte entries.

`FUN_006af780` reads direct-record `+0x3c` and uses it as an index:

- primary table value slot: `0x20 + index * 0x28`;
- secondary table slot: `index * 0x40`;
- secondary slot `+0x30` receives the FLAT tree/node pointer;
- secondary slot `+0x34` receives the direct-record pointer;
- secondary slot `+0x38` receives the primary-table entry pointer.

`FUN_006af830` consumes direct-record `+0x38` as an object/resource handle during teardown, and `FUN_006af640` passes that handle into `FUN_006b0440` for recursive object lookup.

## IR

`src/scene/flat_runtime.py` now exposes `runtime_link_metadata` for every direct record, including the exact index word offset, table strides and per-index slot offsets.

The original raw 16 dwords remain preserved.

## Boundary

The metadata proves runtime link-table layout and handle/index usage. It does not assign a concrete gameplay/scene class to the object referenced by `+0x38`.