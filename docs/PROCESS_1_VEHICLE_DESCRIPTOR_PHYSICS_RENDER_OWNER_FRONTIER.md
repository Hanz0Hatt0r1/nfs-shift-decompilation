# Process 1 — VehicleDetails physics/render owner frontier

## Playable-slice blocker reduced

The remaining P1.1 frame blocker is no longer BODY0 construction identity. The
current positive chain already proves:

```text
BMW SDF BODY0
  -> persistent chassis BODY0
  -> numeric BODY0 -> outer Vehicle relation for the selected Silverstone session
```

and independently proves the selected BMW render resource:

```text
VehicleDetails +0x54 (Vehicle Render Model)
  -> participant RenderHierarchy owner
  -> BMW_M3_E36.vhf
```

The unresolved edge is still:

```text
HighDetailVehicle / outer Vehicle assembly frame
  -> canonical BMW VHF vehicle-root frame
```

A common vehicle name, descriptor class, archive, or resource family is not a
coordinate-frame proof.

## Contract

```text
SHIFT.VehicleDescriptorPhysicsRenderOwnerFrontier/1
```

Builder:

```text
tools/ghidra/analyze_vehicle_descriptor_physics_render_owner_frontier.py
```

## Exact reflected descriptor pair

Retail `FUN_00d6b610` registers both properties in the same VehicleDetails
reflection registry:

```text
Vehicle Render Model  -> +0x54
Vehicle Physics Model -> +0x60
```

The analyzer validates both the decompiler source registration calls and the
exact retail string/xref anchors:

```text
0x00abbbcc  Vehicle Render Model   -> 0x00d6b929
0x00abbb8c  Vehicle Physics Model  -> 0x00d6bacf
```

This only establishes the paired fields. It does not imply that the resources
use the same runtime owner pointer or coordinate frame.

## Positive owner endpoints consumed

The pass requires two already-positive contracts:

```text
SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1
SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1
```

The render contract must prove the selected descriptor's `+0x54` path into the
vehicle RenderHierarchy owner while keeping outer-Vehicle/VHF frame identity
false.

The physics contract must prove:

```text
HighDetailVehicle::Init
  -> vehicle physics assembly
  -> SDF loader
```

with physical receiver continuity and without preclaiming SDF/VHF frame
identity.

## Exact HighDetailVehicle::Init caller frontier

For retail `SHIFT.exe` MD5
`705af8b420e5eb1e3834ac43d5533c6b`, the complete direct caller set of
`FUN_0076df50` is frozen as:

```text
0x0074da70 @ 0x0074dadf -> FUN_0076df50
0x00798df0 @ 0x00798f9c -> FUN_0076df50
```

The source pass also records the observed second source argument expression at
each call. Those expressions are discovery evidence only. They are explicitly
not promoted to `VehicleDetails+0x60` until instruction-level value provenance
proves that relation.

The output therefore emits only these two callers as:

```text
targeted_instruction_worklist.functions
```

with `max_functions = 8` and `neighbors_added = false`.

## Build the frontier

```bash
python3 tools/ghidra/analyze_vehicle_descriptor_physics_render_owner_frontier.py \
  out/shift_ghidra_database \
  /path/to/SHIFT.exe.c \
  out/vehicle_render_hierarchy_resource_owner_join.json \
  out/bmw_sdf_vehicle_assembly_receiver_provenance.json \
  --json-out out/vehicle_descriptor_physics_render_owner_frontier.json
```

## Export the exact caller instructions

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_ranked_function_instructions.py \
  out/vehicle_descriptor_physics_render_owner_frontier.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/vehicle_descriptor_physics_render_init_callers.jsonl
```

The Ghidra exporter remains targeted and read-only/noanalysis. The original game
is not executed.

## Next proof

The resulting two-function instruction artifact must answer one bounded value
question:

```text
At each exact FUN_0076df50 callsite, what is the all-path provenance of the
physical vehicle-load argument, and is it the selected VehicleDetails+0x60
Vehicle Physics Model value?
```

A positive result narrows the final frame proof to one common runtime assembly
owner. A negative result closes this descriptor-field branch and identifies the
actual producer edge without broad callgraph expansion.

## Deliberate non-claims

This frontier keeps all of these false:

```text
vehicle_physics_model_to_HighDetailVehicle_Init_argument_ready = false
descriptor_physics_render_common_runtime_owner_ready           = false
outer_vehicle_root_to_VHF_vehicle_root_ready                    = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready              = false
BODY0_bind_frame_proof_ready                                    = false
vehicle_world_transform_ready                                   = false
```

It does not use:

- common `VehicleDetails` membership as pointer identity;
- common `VehicleDetails` membership as frame identity;
- resource names or archive membership as frame identity;
- callgraph adjacency as value provenance;
- an identity affine delta assumption;
- original-game execution or a new runtime capture.
