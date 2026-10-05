# Process 1 — BMW `offset33b` selector-complete numeric family

## Playable-slice blocker reduced

The remaining BMW BODY0 bind translation was already source-backed symbolically:

```text
M_BODY0_to_outer_vehicle_root.translation = -offset33b

offset33b =
    (auxiliary_weighted_COM - target_CG)
  * (auxiliary_mass / BODY0_mass)
```

PR #1274 closed the scalar mass ratio but deliberately left both vectors
non-numeric. This phase closes those vectors for the complete retail selector
domain without assuming one player-profile default.

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

No retail resource bytes are committed.

The derived input contract records the exact source identities:

```text
PHYSICSPERSISTENT.bff
sha256 18b62954c54e1b7e791c8a0e808480b4ddc41ffbbb08f1babb5bd52f2587761f

entry 40
vehicles/physics/vehicles/bmw_m3_e36.vdf
decoded sha256 f4c925bc6799439a12906d0aed9b73e22052cb46f7fbd4ea6f48409b9776a082
```

and:

```text
PHYSICSBOOTFLOW.bff
sha256 f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a

entry 49
vehicles/physics/physicstweaker.xml
decoded sha256 6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f

entry 8
vehicles/physics/tyres/street_1.hdt
decoded sha256 93277c754fb0f6ed76d683acd89c261d8d18b7bcf26ffbd76c5bf50846eb9df3
```

The BMW VDF supplies:

```text
FL offset = ( 0.7110, 0.31, -1.35)
FR offset = (-0.7110, 0.31, -1.35)
RL offset = ( 0.7225, 0.31,  1.35)
RR offset = (-0.7225, 0.31,  1.35)

all wheel dimensions = (0.225, 0.62)
Vehicle Tyres = Street_1
```

The exact `Street_1.hdt` resource exists, so the reviewed retail tire-present
path uses the VDF wheel width rather than the missing-tire fallback.

The BMW CDF contributes:

```text
CGHeight = 0.280

CGRightRange   = (0.50,  0.000, 0)
CGRightSetting = 0

CGRearRange    = (0.47,  0.000, 0)
CGRearSetting  = 0

front RideHeightRange   = (0.100, -0.005, 6)
front RideHeightSetting = 0

rear RideHeightRange    = (0.110, -0.005, 6)
rear RideHeightSetting  = 0
```

The hash-locked resource contract from #1271 also supplies:

```text
GraphicalOffset = (0, 0, 0)
FuelTankPos     = (0, 0.2, -0.6)
FuelTankMotion  = (560, 0.7)
Mass            = 1460
```

## Corrected wheel geometry

The already-positive
`SHIFT.BMWOffset33bVehicleReferenceYBootstrapZero/1` proves the first-bootstrap
vehicle reference Y is zero. The reviewed retail wheel-point expression is:

```text
corner_y =
    vehicle_reference_y
  - GraphicalOffset.y
  - selected_RideHeight
  + wheel_width / 2
```

Therefore:

```text
FL = ( 0.7110, 0.0125, -1.35)
FR = (-0.7110, 0.0125, -1.35)
RL = ( 0.7225, 0.0025,  1.35)
RR = (-0.7225, 0.0025,  1.35)
```

## Fuel point and auxiliary COM

The retail fuel point is:

```text
rear_midpoint = 0.5 * (RL + RR)
fuel_point    = rear_midpoint + FuelTankPos
fuel_point.y -= 9.81 / FuelTankMotion.x
```

which gives:

```text
fuel_point =
(0,
 0.184982142857142857142857142857142857...,
 0.75)
```

PR #1274 proves each wheel/spindle corner pair is `43 kg`, four pairs total
`172 kg`, the effective fuel mass is `1 kg`, and the total auxiliary mass is
`173 kg`.

The resulting exact auxiliary COM is:

```text
auxiliary_weighted_COM =
(0,
 0.0085259083402146985962014863748967795...,
 0.0043352601156069364161849710982658960...)
```

The scalar mass factor remains:

```text
BODY0_mass = 1287
mass_ratio = 173 / 1287
           = 0.134421134421134421134421134421...
```

## Target CG X/Z

The VDF wheel offsets plus the BMW CDF settings give:

```text
target_CG.x = 0
target_CG.z = -0.081
```

No symmetry assumption is used without the exact resource values: the analyzer
recomputes the left/right and front/rear midpoints.

## Source-backed selector domain

The selector is not frozen to one profile default.

The reviewed retail chain is:

```text
FUN_00498b80
  -> FUN_0070e1c0          creates event type 0x20
  -> FUN_00492520
       -> FUN_00492250     builds RaceModeInfo
            -> FUN_0048dd90
                 RaceModeInfo+0x6c = Player Difficulty

FUN_00711210 case 0x20
  -> FUN_00714560           PhysicsParticipantManager::ChangeRaceMode
```

Retail reflection names the source profile field:

```text
Player Difficulty (0-2)
```

at profile/options `+0x10f4`. `FUN_0041a730` initializes it to `1`, and
`FUN_00d3b190` is a setter, but the numeric family does **not** require that
default.

Therefore the admitted difficulty domain is exactly:

```text
0, 1, 2
```

Array index `3` is deliberately not promoted to a valid Player Difficulty.

`physicstweaker.xml` gives:

```text
CGHeight Scale       = (0.6,  0.6,  0.75, 0.825)
Drift CGHeight Scale = (0.25, 0.25, 0.25, 0.67)
```

`FUN_007bfbe0` derives:

```text
target_CG.y = BMW_CGHeight * selected_CGHeight_scale
```

so the valid family contains six selector combinations but only three unique
translations.

## Numeric BODY0 -> outer Vehicle family

### Normal CGHeight-scale branch, difficulty 0 or 1

```text
target_CG.y = 0.168

offset33b =
(0,
 -0.0214366883116883116883116883116883...,
  0.0114708624708624708624708624708625...)

BODY0 -> outer Vehicle translation =
(0,
 +0.0214366883116883116883116883116883...,
 -0.0114708624708624708624708624708625...)
```

### Normal CGHeight-scale branch, difficulty 2

```text
target_CG.y = 0.210

offset33b =
(0,
 -0.0270823759573759573759573759573760...,
  0.0114708624708624708624708624708625...)

BODY0 -> outer Vehicle translation =
(0,
 +0.0270823759573759573759573759573760...,
 -0.0114708624708624708624708624708625...)
```

### Drift CGHeight-scale branch, difficulty 0/1/2

```text
target_CG.y = 0.070

offset33b =
(0,
 -0.00826341713841713841713841713841714...,
  0.0114708624708624708624708624708625...)

BODY0 -> outer Vehicle translation =
(0,
 +0.00826341713841713841713841713841714...,
 -0.0114708624708624708624708624708625...)
```

The matrix uses the already-established D3D row-vector affine convention:

```text
[1 0 0 0]
[0 1 0 0]
[0 0 1 0]
[x y z 1]
```

## Positive handoff

```text
offset33b_auxiliary_weighted_COM_ready                    = true
offset33b_target_CG_selector_family_ready                  = true
BMW_numeric_offset33b_selector_family_ready                = true
BODY0_to_outer_vehicle_root_selector_family_ready          = true
BMW_numeric_offset33b_ready_when_race_mode_selector_bound  = true
BODY0_to_outer_vehicle_root_numeric_matrix_ready_when_selector_bound = true
```

Still fail-closed:

```text
BMW_numeric_offset33b_ready                      = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
outer_vehicle_root_to_VHF_vehicle_root_ready     = false
BODY0_bind_frame_proof_ready                     = false
vehicle_world_transform_ready                    = false
```

The two singular flags stay false because no particular session selector has
yet been bound into the native bootstrap. More importantly, this phase does not
invent the independent `outer Vehicle root -> VHF vehicle root` frame relation.

## Next blocker

The Process 2 side can now consume the source-backed session selector pair:

```text
(use_drift_cgheight_scale, Player Difficulty 0..2)
```

and select one of the exact BODY0-to-outer-Vehicle translations above.

The remaining transform-semantic proof is then:

```text
outer Vehicle root
    ->
VHF vehicle root / assembly frame
```

Only after that join may the existing persistent BODY0 pose path promote a
retail-admissible vehicle world transform.

## Reproduce

With the existing semantic proof bundle:

```bash
python3 tools/ghidra/analyze_bmw_offset33b_selector_complete_numeric.py \
  out/shift_ghidra_database \
  evidence/bmw_offset33b_resource_inputs.json \
  out/bmw_offset33b_semantic_static_proof/03_bmw_offset33b_actual_additional_mass_bootstrap_zero.json \
  out/bmw_offset33b_semantic_static_proof/04_bmw_offset33b_vehicle_reference_y_bootstrap_zero.json \
  --json-out out/bmw_offset33b_selector_complete_numeric.json
```
