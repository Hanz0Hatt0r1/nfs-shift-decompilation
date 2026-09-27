# Phase 383 — Turbo BBF/TBF runtime

The BMW M3 physics corpus includes two real Turbo resources:

- `vehicles/physics/turbo/gen_lowrpm_33.tbf`
- `vehicles/physics/turbo/nitrous.bbf`

This phase moves their loader boundary into neutral IR.

## BBF

`FUN_007c6030` reads:

| Field | Runtime offset | Loader helper |
|---|---|---|
| Boost | +0x34 | FUN_007a75a0 |
| Max Boost | +0x20 | FUN_007a75a0 |
| Boost Time | +0x08 | FUN_007a75a0 |
| Fill Time | +0x04 | FUN_007a67b0 |
| Max Boost Time | +0x1c | FUN_007a67b0 |
| Ramp Down Time | +0x48 | FUN_007a67b0 |
| Min Level To Fire | +0x4c | FUN_007a67b0 |

The loader applies `FUN_007a6be0` to Boost and Boost Time, then checks both
against the 1e-5 activation threshold. When active, four timing/fire fields are
clamped to `[0, _DAT_00b8d8e8]` through `FUN_007c5fd0`.

## TBF

`FUN_007c6680` loads Twin/Sequential flags, wastegate fields and two turbo
descriptors.

Source-visible conversions:

- Size × 0.01
- Engine RPM × 0.10471976
- Turbine Optimum RPM × 0.10471976
- Fuel Percentage × 0.01
- Inertia/Friction unchanged

After loading, the function applies `FUN_007a6be0` to the converted Turbo1 and
Turbo2 Size values stored at +0x08 and +0x1c. It stores the post-modifier values
at +0x0c and +0x20 and returns their sum plus 1.0. The implementation exposes
this value as a raw source-derived scalar and does not assign it a gameplay name.

## Implementation

`turbo_runtime.py` contains `parse_turbo_bbf()` and `parse_turbo_tbf()`.
The vehicle physics bundle extracts both resources automatically.

## Explicit unknowns

PhysX ownership, exact Turbo object classes, GlobalUpgrades node provenance from
the running object graph, and the higher-level semantics of the converted fields
remain separate evidence targets.
