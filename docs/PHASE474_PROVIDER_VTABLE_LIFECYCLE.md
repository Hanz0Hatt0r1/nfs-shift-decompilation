# Phase 474 — specialized-provider vtable lifecycle

## Goal

Phase 474 decodes the two specialized provider vtables directly from PE `.rdata` and assigns only roles already supported by the earlier source/runtime evidence.

## Provider 0

Vtable: `0x00B0FC5C`

| Slot | Function | Role |
|---:|---:|---|
| `+0x00` | `FUN_007d3120` | destructor wrapper |
| `+0x04` | `FUN_007d2eb0` | output-vector accessor |
| `+0x08` | `FUN_007d2ec0` | factor-workspace accessor |
| `+0x0c` | `FUN_007d2ed0` | row-pointer accessor |
| `+0x10` | `FUN_007c6e30` | scalar-count check |
| `+0x14` | `FUN_007c6e50` | acceptance check |
| `+0x18` | `FUN_007c7200` | solve |
| `+0x1c` | `FUN_007d3150` | reset |
| `+0x20` | `FUN_007d43c0` | cleanup |
| `+0x24` | `FUN_007d2ee0` | workspace-size accessor |
| `+0x28` | `FUN_007d2ef0` | scalar-count accessor |
| `+0x2c` | `FUN_007d2f00` | workspace-size/finalize accessor |

`FUN_007d3120` calls the previously identified shutdown routine `FUN_007c6e10` before its optional object deletion path.

## Provider 1

Vtable: `0x00B0FC8C`

The same slot layout is used, with provider-1 implementations:

`+0x00 FUN_007d4870`, `+0x04 FUN_007d2f10`, `+0x08 FUN_007d2f20`, `+0x0c FUN_007d2f30`, `+0x10 FUN_007cdb20`, `+0x14 FUN_007cdb40`, `+0x18 FUN_007cdfc0`, `+0x1c FUN_007d48a0`, `+0x20 FUN_007d5600`, `+0x24 FUN_007d2f40`, `+0x28 FUN_007d2f50`, `+0x2c FUN_007d2f60`.

`FUN_007d4870` calls provider shutdown `FUN_007cdb00` before optional deletion.

## Lifecycle model

The recovered vtables support this source/PE-backed lifecycle surface:

`accessors → scalar/acceptance checks → solve/reset/cleanup → destructor/shutdown`

This is a dispatch topology, not a claim about the underlying C++ class hierarchy.

## Capture implication

Phase 463's provider breakpoints at `+0x18` are now backed directly by the actual vtable word. The reset/cleanup profiles from Phases 466–468 are likewise tied to explicit `+0x1c/+0x20` slots.

## Scope boundary

Only PE function-pointer addresses and roles already supported by source-derived evidence are named. Undecoded accessor internals remain opaque.
