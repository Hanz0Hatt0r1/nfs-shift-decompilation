# Process 1 — BMW `offset33b` resource inputs

## Playable-slice blocker reduced

The remaining numeric BODY0-to-outer-Vehicle bind translation is:

```text
M_BODY0_to_outer_vehicle_root.translation = -offset33b
```

The existing reduced static proof turns `FUN_0076b280` STORE dependencies into
an exact machine memory-LOAD worklist. The next semantic join needs exact BMW
resource/init values, but those values must not be assigned to a machine LOAD
from displacement alone.

This phase freezes the resource side of that join as:

```text
SHIFT.BMWOffset33bResourceInputs/1
```

with validator:

```text
tools/ghidra/validate_bmw_offset33b_resource_inputs.py
```

## Exact retail identities

The observations come from the same hash-locked BMW archive already admitted by
the vehicle-physics and BODY0 proofs:

```text
BMW_M3_E36.bff
SHA-256 c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
```

Exact CDF:

```text
entry 1088
vehicles/physics/chassis/bmw_m3_e36.cdf
type 2
compressed 5358
uncompressed 24817
SHA-256 bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d
```

Exact SDF:

```text
entry 1091
vehicles/physics/suspension/aarm_multilink.sdf
type 2
compressed 1110
uncompressed 5056
SHA-256 fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
```

No archive, CDF, or SDF payload is committed by this phase.

## CDF values relevant to `FUN_0076b280`

The exact decoded BMW values retained by the contract are:

```text
Mass            = 1460.0
CGHeight        = 0.28
GraphicalOffset = (0.0, 0.0, 0.0)
FuelTankPos     = (0.0, 0.2, -0.6)
FuelTankMotion  = (560.0, 0.7)
```

The existing source-backed CDF schema proves parser destination offsets. The
CDF parser object used by the vehicle load path is `load_data + 0x8`, so the
following mapping is arithmetic, not name inference:

| CDF field | parser offsets | `FUN_0076b280` load-data offsets |
| --- | --- | --- |
| Mass | `+0x1c` | `+0x24` |
| GraphicalOffset | `+0xc8/+0xdc/+0xf0` | `+0xd0/+0xe4/+0xf8` |
| FuelTankPos | `+0x158/+0x160/+0x168` | `+0x160/+0x168/+0x170` |
| FuelTankMotion | `+0x170/+0x178` | `+0x178/+0x180` |

`CGHeight` is retained as an exact resource value, but this pass does **not**
assign it directly to the derived `load_data+0x338` value. `+0x338` remains an
explicit derived-value frontier.

## SDF values

All eleven exact raw SDF BODY names, masses and `pos` values are retained in the
contract. They are candidate resource inputs for the weighted-body calculation,
not a claim that every runtime BODY mass or runtime BODY position is identical
to its raw SDF value after construction and later producers.

In particular, the already-corrected additional-mass bootstrap-zero proof is
not reapplied to a machine LOAD until pointer provenance proves that exact
storage.

## Validator

The validator joins this derived evidence to existing repository contracts:

- `SHIFT.BMWM3VehiclePhysicsResourceManifest/1` for exact CDF/SDF archive-entry
  identity;
- source-backed `src/physics/vehicle_cdf_runtime.py` for CDF parser offsets;
- `SHIFT.BMWBody0BindResourceMaterialization/1` for BODY0 identity/position.

It fails closed on hash, entry metadata, CDF parser offsets, `+0x8` load-data
translation, BODY order, non-finite values, or any positive final transform
claim.

Run:

```bash
python3 tools/ghidra/validate_bmw_offset33b_resource_inputs.py \
  evidence/bmw_offset33b_resource_inputs.json \
  evidence/bmw_m3_vehicle_physics_manifest.json \
  evidence/bmw_body0_bind_resource_materialization.json \
  --json-out out/bmw_offset33b_resource_inputs_validation.json
```

## Handoff

Positive now:

```text
offset33b_resource_inputs_ready                 = true
offset33b_direct_CDF_load_data_mapping_ready    = true
offset33b_SDF_body_resource_values_ready        = true
```

Still fail-closed:

```text
offset33b_memory_LOAD_semantic_join_ready       = false
BMW_numeric_offset33b_ready                     = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                    = false
vehicle_world_transform_ready                   = false
```

## Next exact proof

Run the existing one-command reduced static proof for `FUN_0076b280`. Its exact
`(base-origin, displacement, width)` worklist can then be joined mechanically to
this contract where pointer provenance identifies the CDF load-data object or a
concrete runtime BODY/resource owner.

No second broad Ghidra search is required.
