# Process 1 — BMW `offset33b` first-bootstrap mass ratio

## Playable-slice blocker reduced

The retail `FUN_0076b280` algebra reduces the symbolic BODY0 bind translation to:

```text
offset33b =
    (auxiliary_weighted_COM - target_CG)
  * (auxiliary_mass / BODY0_mass)
```

This phase closes the scalar factor for the exact BMW M3 E36 first-bootstrap
path. It does not preclaim either remaining vector.

Contract:

```text
SHIFT.BMWOffset33bBootstrapMassRatio/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_bootstrap_mass_ratio.py
```

## Retail construction and lookup chain

The analyzer freezes exact retail fingerprints and direct edges for:

```text
FUN_007615c0  SDF chassis BODY selection
    |
    +-- 0x007615ed -> FUN_007b6900  SDF construction
                            |
                            +-- 0x007b6e8f -> FUN_007b3670
                                                   |
                                                   +-- 0x007b3792 -> FUN_007bba90
```

The source-backed BODY construction path writes parsed BODY mass directly into
runtime `BODY+0x120`, with inverse mass at `+0x90`.

`FUN_007615c0` then performs exactly twelve `FUN_007b3da0` name lookups. The
reviewed callsite/name bindings are:

```text
body        -> HDVehicle+0x33a0
fl_wheel    -> HDVehicle+0x0820
fl_spindle  -> HDVehicle+0x0824
fr_wheel    -> HDVehicle+0x12a0
fr_spindle  -> HDVehicle+0x12a4
rl_wheel    -> HDVehicle+0x1d20
rl_spindle  -> HDVehicle+0x1d24
rr_wheel    -> HDVehicle+0x27a0
rr_spindle  -> HDVehicle+0x27a4
rear_axle   -> HDVehicle+0x2e00
fuel_tank   -> HDVehicle+0x0280
driver_head -> HDVehicle+0x0298
```

`FUN_007b3da0` returns null when a requested BODY name is absent. The exact BMW
SDF contains no `rear_axle`, so its optional mass/COM term is absent. The same SDF
contains `driver_head`, and `FUN_0076b280` explicitly excludes the BODY at
`HDVehicle+0x298` when subtracting non-chassis mass from the CDF vehicle mass.

## Exact BMW arithmetic

The hash-locked BMW resource contract provides:

```text
CDF Mass = 1460.0
first-bootstrap additional mass = 0.0
```

The eight wheel/spindle BODY masses are:

```text
FL: 25 + 18 = 43
FR: 25 + 18 = 43
RL: 26 + 17 = 43
RR: 26 + 17 = 43
```

so the four corner pairs total `172`. `FUN_0076b280` forces the fuel-tank runtime
BODY mass to `1.0` before its weighted-COM accumulation, and the exact BMW SDF
independently also has fuel-tank mass `1.0`.

Therefore:

```text
auxiliary_mass = 172 + 1 = 173
BODY0_mass     = 1460 + 0 - 173 = 1287
mass_ratio     = 173 / 1287
               = 0.134421134421...
```

The `driver_head` SDF mass is `5`, but it is deliberately not part of
`auxiliary_mass` and is deliberately not subtracted from the CDF chassis mass on
this path.

## Positive handoff

```text
offset33b_runtime_BODY_mass_construction_join_ready = true
offset33b_driver_head_exclusion_ready                = true
offset33b_rear_axle_absence_ready                    = true
offset33b_auxiliary_mass_ready                       = true
offset33b_BODY0_bootstrap_mass_ready                 = true
offset33b_mass_ratio_ready                           = true
```

Still fail-closed:

```text
offset33b_auxiliary_weighted_COM_ready = false
offset33b_target_CG_ready               = false
BMW_numeric_offset33b_ready             = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready            = false
vehicle_world_transform_ready           = false
```

## Scope boundary

This is a first-bootstrap construction-order proof. It does not claim raw SDF
mass equals runtime BODY mass at arbitrary later frames. It does not assign the
remaining corner vectors, effective CG-height settings, or target-CG setup
values by name or displacement. Those two vector terms are now the only numeric
inputs left in the `offset33b` expression.

## Run

```bash
python3 tools/ghidra/analyze_bmw_offset33b_bootstrap_mass_ratio.py \
  out/shift_ghidra_database \
  evidence/bmw_offset33b_resource_inputs.json \
  out/bmw_offset33b_semantic_static_proof/03_bmw_offset33b_actual_additional_mass_bootstrap_zero.json \
  --json-out out/bmw_offset33b_bootstrap_mass_ratio.json
```
