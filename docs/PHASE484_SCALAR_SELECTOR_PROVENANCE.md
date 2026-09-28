# Phase 484 — scalar selector provenance

## Goal

Phase 484 reconstructs the exact provenance of the scalar selector passed to `FUN_007b2210` from the three active constraint groups in `FUN_007b3f40`.

## Primary JOINT/HINGE group

Source callsite: line 814124.

Record base: `physics_system+0x1c`, stride `0xA0`.

When `record+0x70` bit 0 is set, the selector is loaded from `(record+0x7c)->+0x30` and three reset calls are issued:

`selector`, `selector+1`, `selector+2`.

## Secondary group

Source callsite: line 814138.

Record base: `physics_system+0x24`, stride `0xA0`.

The selector is loaded from `(record+0x7c)->+0x94` and two calls are issued:

`selector`, `selector+1`.

## BAR group

Source callsite: line 814150.

Record base: `physics_system+0x2c`, stride `0xB8`.

The selector is loaded from `(record+0x7c)->+0x30` and one reset call is issued.

## Consequence

This closes the chain:

`constraint record → selector source field → FUN_007b2210(param_1) → provider vtable +0x1c(param_1)`

`FUN_007b2210` itself performs no selector bounds check, so domain validity is a caller-side property. The recovered scalar count (40/34) remains the expected selector domain for the corresponding provider.

## Scope boundary

The `+0x7c`, `+0x30` and `+0x94` offsets are recorded as source-derived selector paths only. No new semantic field names, matrix coordinates or physical meanings are inferred.
