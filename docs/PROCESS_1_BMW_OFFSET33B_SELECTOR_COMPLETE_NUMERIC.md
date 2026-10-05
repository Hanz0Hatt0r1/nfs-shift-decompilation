# Process 1 — BMW `offset33b` selector-complete numeric family

## Playable-slice blocker reduced

The retail BODY0 bind relation was already reduced to

```text
M_BODY0_to_outer_vehicle_root.translation = -offset33b

offset33b =
    (auxiliary_weighted_COM - target_CG)
  * (auxiliary_mass / BODY0_mass)
```

PR #1274 proved the BMW first-bootstrap scalar factor `173 / 1287`. This phase
closes both remaining vectors for the complete admitted retail race-mode
selector domain, without assuming one player-profile default.

Contracts:

```text
SHIFT.BMWOffset33bSelectorGeometryInputs/1
SHIFT.BMWOffset33bSelectorCompleteNumeric/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_selector_complete_numeric.py
```

## Exact resource inputs

No retail resource bytes are committed. The derived evidence records exact
archive/entry identities.

BMW VDF:

```text
PHYSICSPERSISTENT.bff
archive sha256 18b62954c54e1b7e791c8a0e808480b4ddc41ffbbb08f1babb5bd52f2587761f
entry 40: vehicles/physics/vehicles/bmw_m3_e36.vdf
decoded sha256 f4c925bc6799439a12906d0aed9b73e22052cb46f7fbd4ea6f48409b9776a082
```

Exact values:

```text
Wheel FL Offset = ( 0.7110, 0.31, -1.35)
Wheel FR Offset = (-0.7110, 0.31, -1.35)
Wheel RL Offset = ( 0.7225, 0.31,  1.35)
Wheel RR Offset = (-0.7225, 0.31,  1.35)

Wheel * Dimensions = (0.225, 0.62) for all four corners
Vehicle Tyres       = Street_1
```

The VDF property names are anchored to `FUN_00703f10`; the retail layout is
`Wheel * Offset` at record `+0x34/+0x40/+0x4c/+0x58` and `Wheel * Dimensions`
at `+0x64/+0x6c/+0x74/+0x7c`.

Physics tweaker:

```text
PHYSICSBOOTFLOW.bff
archive sha256 f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a
entry 49: vehicles/physics/physicstweaker.xml
decoded sha256 6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f

CGHeight Scale       = (0.6, 0.6, 0.75, 0.825)
Drift CGHeight Scale = (0.25, 0.25, 0.25, 0.67)
```

The two property names are anchored to `FUN_00749a60`. The selected ordinary
BMW tire also exists as exact Type-2 resource:

```text
entry 8: vehicles/physics/tyres/street_1.hdt
decoded sha256 93277c754fb0f6ed76d683acd89c261d8d18b7bcf26ffbd76c5bf50846eb9df3
```

The exact BMW CDF contributes:

```text
CGHeight = 0.280
GraphicalOffset = (0,0,0)
FuelTankPos = (0,0.2,-0.6)
FuelTankMotion = (560,0.7)

CGRightRange=(0.50,0.000,0), setting=0
CGRearRange =(0.47,0.000,0), setting=0
front RideHeightRange=(0.100,-0.005,6), setting=0
rear  RideHeightRange=(0.110,-0.005,6), setting=0
```

`VehicleLoadData+0x338` is kept as a derived field rather than being named from
displacement. The retail `FUN_007bfbe0` construction path supplies that derived
CG-height value from `CDF.CGHeight` and the selected PhysicsTweaker scale.

## Correct retail wheel geometry

`SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1` proves first-bootstrap
`vehicle_reference_y = 0`; exact BMW `GraphicalOffset.y = 0`.

The reviewed `FUN_0076b280` path advances through the **second** scalar of each
VDF `Wheel * Dimensions` pair (`+0x68/+0x70/+0x78/+0x80`). Therefore the exact
operation is deliberately described only as:

```text
corner_y =
    vehicle_reference_y
  - GraphicalOffset.y
  - selected_RideHeight
  + VDF_Wheel_Dimensions[1] / 2
```

No unsupported semantic name such as width or diameter is assigned to that
component. Since `0.62 / 2 = 0.31`, the corrected points are:

```text
FL = ( 0.7110, 0.21, -1.35)
FR = (-0.7110, 0.21, -1.35)
RL = ( 0.7225, 0.20,  1.35)
RR = (-0.7225, 0.20,  1.35)
```

## Fuel point and auxiliary weighted COM

The retail path does not retain rear-midpoint Y for the fuel anchor:

```text
rear_midpoint = 0.5 * (RL + RR)
fuel_anchor = rear_midpoint
fuel_anchor.y = vehicle_reference_y - GraphicalOffset.y
fuel_point = fuel_anchor + FuelTankPos
fuel_point.y -= 9.81 / FuelTankMotion.x
```

Therefore:

```text
fuel_point =
(0,
 0.182482142857142857...,
 0.75)
```

PR #1274 proves the four wheel/spindle corner masses are each `43`, their total
is `172`, the effective fuel mass is `1`, auxiliary mass is `173`, and BODY0
mass is `1287`.

The resulting exact auxiliary COM is:

```text
auxiliary_weighted_COM =
(0,
 0.204869838976052848885218827415359207...,
 0.004335260115606936416184971098265896...)

mass_ratio = 173 / 1287
           = 0.134421134421134421...
```

## Target CG and selector provenance

The BMW X/Z target components are fully numeric:

```text
target_CG.x = 0
target_CG.z = -0.081
```

The Y component is:

```text
target_CG.y = 0.28 * selected_CGHeight_scale
```

The admitted selector domain is source-backed by the profile reflection property
`Player Difficulty (0-2)`, so valid difficulty values are exactly `0,1,2`.
Array index `3` exists in the PhysicsTweaker arrays but is deliberately not
promoted to a valid Player Difficulty.

The retail event/staging path is:

```text
FUN_00498b80
  -> FUN_0070e1c0        event type 0x20
  -> FUN_00492520
       -> FUN_00492250
            -> FUN_0048dd90
                 RaceModeInfo+0x6c = profile/options+0x10f4

FUN_00711210 case 0x20
  -> FUN_00714560        ChangeRaceMode
       manager staging +0x3b4
  -> FUN_00714ed0
       copies the same 0x7c-byte RaceModeInfo to DAT_00c12860
```

Thus the selected fields consumed by `FUN_007bfbe0` are retained as the same
RaceModeInfo data:

```text
RaceModeInfo+0x0e -> DAT_00c1286e   normal/drift CGHeight-scale selector
RaceModeInfo+0x6c -> DAT_00c128cc   Player Difficulty index
```

`FUN_0041a730` initializes profile difficulty to `1` and `FUN_00d3b190` can
change it, but this proof does not assume the default.

## Complete numeric family

There are six admitted selector combinations and three unique BODY0-to-outer
Vehicle translations.

### Normal branch, difficulty 0 or 1

```text
CGHeight scale = 0.6
target_CG.y = 0.168

offset33b =
(0,
 +0.004956085581085581085581085581085581...,
 +0.011470862470862470862470862470862471...)

BODY0 -> outer Vehicle translation =
(0,
 -0.004956085581085581085581085581085581...,
 -0.011470862470862470862470862470862471...)
```

### Normal branch, difficulty 2

```text
CGHeight scale = 0.75
target_CG.y = 0.210

offset33b =
(0,
 -0.000689602064602064602064602064602065...,
 +0.011470862470862470862470862470862471...)

BODY0 -> outer Vehicle translation =
(0,
 +0.000689602064602064602064602064602065...,
 -0.011470862470862470862470862470862471...)
```

### Drift branch, difficulty 0, 1 or 2

```text
CGHeight scale = 0.25
target_CG.y = 0.070

offset33b =
(0,
 +0.018129356754356754356754356754356754...,
 +0.011470862470862470862470862470862471...)

BODY0 -> outer Vehicle translation =
(0,
 -0.018129356754356754356754356754356754...,
 -0.011470862470862470862470862470862471...)
```

The matrices use the already-established D3D row-vector affine convention:

```text
[1 0 0 0]
[0 1 0 0]
[0 0 1 0]
[x y z 1]
```

## Positive handoff and fail-closed boundary

Positive:

```text
offset33b_auxiliary_weighted_COM_ready = true
offset33b_target_CG_selector_family_ready = true
BMW_numeric_offset33b_selector_family_ready = true
BODY0_to_outer_vehicle_root_selector_family_ready = true
BMW_numeric_offset33b_ready_when_race_mode_selector_bound = true
BODY0_to_outer_vehicle_root_numeric_matrix_ready_when_selector_bound = true
```

Still deliberately false:

```text
BMW_numeric_offset33b_ready = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

The singular numeric flags remain false because this artifact proves a selector
family, not a particular live session selection. It also does not invent the
independent `outer Vehicle root -> VHF vehicle root` frame relation.

## Next blocker

Process 2 can now bind the source-backed race-mode selector pair
`(normal/drift, Player Difficulty 0..2)` and select one of the exact matrices
above. Independently, Process 1 still needs:

```text
outer Vehicle root
  -> VHF vehicle root / assembly frame
```

Only after that join may the persistent BODY0 pose path promote a
retail-admissible vehicle world transform.

## Reproduce

```bash
python3 tools/ghidra/analyze_bmw_offset33b_selector_complete_numeric.py \
  out/shift_ghidra_database \
  evidence/bmw_offset33b_resource_inputs.json \
  out/bmw_offset33b_semantic_static_proof/03_bmw_offset33b_actual_additional_mass_bootstrap_zero.json \
  out/bmw_offset33b_semantic_static_proof/04_bmw_offset33b_vehicle_reference_y_bootstrap_zero.json \
  --geometry evidence/bmw_offset33b_selector_geometry_inputs.json \
  --json-out out/bmw_offset33b_selector_complete_numeric.json
```
