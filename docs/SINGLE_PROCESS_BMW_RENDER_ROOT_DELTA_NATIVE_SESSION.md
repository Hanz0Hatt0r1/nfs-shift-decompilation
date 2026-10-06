# Single process — selected BMW render-root delta numeric materialization

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

It closes S1 `BMW-render-root-delta-numeric-materialization` for the selected
fresh Silverstone + BMW M3 E36 native session. The already-positive
`SHIFT.OuterVehicleBMWVHFRootRelation/1` is setup-fixed affine but cannot yet be
turned into a finite `M_outer_to_vhf_root` until
`outerVehicle+0x19c/+0x1a0/+0x1a4` are numeric.

## INPUT

- retail `SHIFT.exe`, MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
- `SHIFT.GhidraEvidenceDatabase/1` for that image;
- bounded retail `SHIFT.exe.c` decompile;
- native vertical-slice policy: fresh process bootstrap, selected primary
  participant role/index `0`, target `Silverstone+BMW_M3_E36`.

The role choice is an explicit native-session policy, analogous to the existing
selected-session difficulty/physics-mode policy. It is **not** claimed to be an
observation of a retail live session or a universal retail default.

## STATIC PROOF

The fresh owner path is source- and callgraph-bounded:

```text
FUN_00715240
  -> FUN_007125e0
      -> FUN_0072ed20
          -> FUN_0079c1c0
              -> FUN_0079bfd0
                   Vehicle+0x19c = 0
                   Vehicle+0x1a0 = 0
                   Vehicle+0x1a4 = 0
  -> FUN_0074e1a0
      -> FUN_0074ddb0
          -> FUN_0041cbd6
              -> FUN_0074ddc3  PhysicsParticipant::Restart
                   -> FUN_00797fd0(Vehicle, RestartInfo+0x10, 0, 1)
                   -> FUN_00798df0  Vehicle::InitVehicle
                        -> FUN_00795d60
```

`FUN_00797fd0` stores its role/index argument at `Vehicle+0x234`. In Restart,
role/index `0` also promotes the participant to `DAT_00c10b30/34`, so the
selected native primary participant enters the `outerVehicle+0x234 == 0`
producer branch.

That branch overwrites the geometry-derived candidate values with:

```text
delta.x = old_delta.x - DAT_00c16ab0
delta.y = old_delta.y - DAT_00c16ab8
delta.z = old_delta.z - DAT_00c16ac0
```

The retail PE proves all three globals live in the `.data` zero-fill tail:
inside `VirtualSize`, beyond `SizeOfRawData`. Their process-start values are
therefore exact `+0.0f`.

The Ghidra callgraph gives exactly three direct callers of `FUN_0078ef00`, the
function that materializes `DAT_00c16ab0/ab8/ac0` through `FUN_007afd20`:

```text
FUN_0074bfd0
FUN_00794a30
FUN_0079b2d0
```

None belongs to the fresh constructor -> Restart -> `InitVehicle` chain above.
Therefore, for the explicitly selected fresh primary native session, the first
`FUN_00795d60` evaluates all three override components as `0 - 0`.

## OUTPUT

Machine-readable checkpoint:

```text
evidence/bmw_render_root_delta_native_silverstone_session.json
SHIFT.BMWRenderRootDeltaNativeSession/1
```

Exact numeric value:

```text
delta_local = (0.0, 0.0, 0.0)
source fields = outerVehicle +0x19c/+0x1a0/+0x1a4
producer = FUN_00795d60
branch = outerVehicle+0x234 == 0
```

This promotes only:

```text
selected_BMW_render_root_delta_numeric_ready = true
```

It deliberately keeps false:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

## CONSUMER

S2 now consumes this exact zero delta plus the already-positive exact BMW VHF
root frame and evaluates the finite matrix required by
`SHIFT.OuterVehicleBMWVHFRootRelation/1`:

```text
M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))
```

Then S3 composes that matrix with the already-positive selected-session
BODY0->outer numeric matrix and publishes `SHIFT.BMWBody0BindFrameProof/1`.

## LIMITS

- Scope is the fresh-process first primary participant selected for the native
  vertical slice. A later Restart after runtime global-origin updates is not
  assigned this numeric value by this proof.
- Nonzero participant roles are not assigned this numeric delta.
- The native role policy is not presented as a retail live-session observation.
- The non-primary geometry branch, including FuelSetting-dependent terms, is not
  used and is not broadened here.
- No rejected car-body `+0x34/+0x534`, render-manager `+0xca4`, or
  `FUN_007b7840` branch is reopened.
- No runtime capture or original-game execution is used.

## TESTS

```bash
pytest -q tests/test_ghidra_bmw_render_root_delta_native_session.py
```

Focused local result: `7 passed`.

Retail regeneration:

```bash
python3 tools/ghidra/analyze_bmw_render_root_delta_native_session.py \
  out/shift_ghidra_database \
  /path/to/SHIFT.exe.c \
  /path/to/SHIFT.exe \
  --role-index 0 \
  --fresh-process-bootstrap \
  --json-out out/bmw_render_root_delta_native_silverstone_session.json
```

## NEXT_STEP

Consume the exact BMW VHF HIERARCHY-root numeric matrix, evaluate finite
`M_outer_to_vhf_root`, publish that numeric relation checkpoint immediately, and
then compose `SHIFT.BMWBody0BindFrameProof/1`.
