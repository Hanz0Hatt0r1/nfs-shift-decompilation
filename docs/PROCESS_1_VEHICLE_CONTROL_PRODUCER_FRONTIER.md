# Process 1 — vehicle control producer frontier

## BLOCKER

P1.3 needs exact retail input -> drivetrain/wheel/control value provenance. The upper persistent-vehicle update path is already strongly recovered, but those scheduler/update values must not be relabeled as player controls without an independent value-transfer proof.

## Closed scheduler/update side

The existing PC-retail contracts positively recover:

```text
FUN_00715380
  -> FUN_00713050
       -> FUN_00794a30
            -> FUN_00770e80(&DAT_00c13700, ...)
```

The two `FUN_00794a30` object channels at `+0x1aa8/+0x1ab0` are forwarded into `FUN_00770e80`, which stores them at `DAT_00c13700+0x98/+0xa0` around the two physics passes. `FUN_00713050` also exposes the already-recovered scheduler accumulator `+0x348`, channel seed `+0x160`, and retail cadence/rate machinery.

These are update/cadence facts. No existing contract proves that either 64-bit channel is throttle, brake, steering, gear, clutch, or another player-control quantity.

## Closed wheel structure

Inside each `FUN_0076d100` pass, `FUN_00758b50` is the proven wheel-update anchor. `SHIFT.WheelKinematicsSourceEvidence/1` fixes the four-wheel structure:

- wheel-state base `HDVehicle+0x848`;
- wheel-runtime base `HDVehicle+0x400`;
- count 4;
- stride `0xa80`.

The arithmetic/native structure is substantially recovered, but the exact retail control-state producer feeding the state consumed by this pass is not yet positively owned.

## Boundary adjudication

The native `VehicleControlIntent` interface is a useful host-side boundary, not retail evidence. P1.3 must therefore prove a PC-retail value transfer rather than connecting that native type to nearby vehicle-update fields by naming similarity or callgraph adjacency.

The open chain is deliberately written as:

```text
retail input/control producer
  -?-> concrete vehicle/wheel state writer
       -?-> state consumed before/during FUN_0076d100
            -> FUN_00758b50 four-wheel update
```

The already-closed outer scheduler path is not substituted for either `-?->` edge.

## GATES_CHANGED

- outer scheduler/update value provenance: **closed for cadence/update use**;
- those channels identified as player control: **false**;
- `FUN_00758b50` four-wheel structural boundary: **closed**;
- concrete `FUN_00758b50` control-state owner: **open**;
- P1.3 control producer complete: **false**;
- retail control chain complete: **false**;
- external-provider count: **7**.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Trace writers/readers of the vehicle/wheel fields consumed by the `FUN_00758b50` path back to a concrete retail input/control producer and selected BMW object. Do not infer control semantics from the scheduler channels or from native `VehicleControlIntent`.
