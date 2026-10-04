# Process 1 — outer Vehicle root -> VHF vehicle-root relation frontier

## Playable-slice blocker reduced

The current bind chain already proves:

```text
BODY0-local -> outer Vehicle-root
```

symbolically, and independently proves the canonical BMW VHF hierarchy/body-MEB
assembly transform. The remaining frame question is only:

```text
outer Vehicle-root -> VHF vehicle-root
```

The frames must not be equated from naming, callgraph adjacency, or a shared
spawn position. If the retail assembly inserts a fixed transform between them,
that affine delta must be recovered instead.

This phase freezes the smallest exact retail neighborhood needed for that proof.

Contract:

```text
SHIFT.OuterVehicleVHFRootRelationFrontier/1
```

Builder:

```text
tools/ghidra/build_outer_vehicle_vhf_root_relation_frontier.py
```

## Source-labelled spawn anchor

The raw retail Ghidra evidence identifies `FUN_0074ddc3` with all three source
labels:

```text
.\Source\System\PhysicsParticipant.cpp
MWL::Core::PhysicsParticipant::Restart
Car %d tried to spawn at 0,0,0 - was attempting to spawn to grid spot %d
```

Their exact string addresses/xrefs are validated rather than treating a factory
heuristic as class identity.

`PhysicsParticipant::Restart` reaches the already source-backed outer Vehicle
transform setter `FUN_007927c0` on four branch-specific paths:

```text
0x0074de8c -> FUN_007927c0
0x0074df26 -> FUN_007927c0
0x0074df62 -> FUN_007927c0
0x0074dfce -> FUN_007927c0
```

All four are required. The switch-dependent spawn paths are not collapsed into
one representative callsite.

## Exact outer Vehicle setter fan-out

The complete direct-call fan-out of `FUN_007927c0` is frozen as:

```text
0x007927fd -> FUN_007af6e0
0x0079280e -> FUN_007876e0
0x00792828 -> FUN_007afb60
0x00792837 -> FUN_004a7870
0x00792884 -> FUN_00787160
0x007928e3 -> FUN_007633b0
0x007928f0 -> FUN_007ac2f0
```

`FUN_007633b0` is independently source-backed as the HDVehicle chassis transform
sink. The other callees are deliberately classified only by their physical ABI
and position in this exact fan-out. No class, render-owner, VHF-owner or transform
semantics are inferred from anonymous names.

## Next targeted instruction export

The initial machine-value proof is bounded to:

```text
FUN_0074ddc3
FUN_007927c0
FUN_007876e0
FUN_007afb60
FUN_00787160
FUN_007633b0
FUN_007ac2f0
```

The two no-`this` fastcall helpers (`FUN_007af6e0`, `FUN_004a7870`) are deferred
unless the exact value slice terminates in them.

The instruction pass must answer, fail-closed:

1. receiver and transform-argument origins at every reachable
   `Restart -> FUN_007927c0` branch;
2. which `FUN_007927c0` outgoing calls receive the same spawn position/orientation
   or a deterministic derivative;
3. receiver origin and concrete writes/forwards for each `thiscall` candidate;
4. whether a resulting concrete owner is the same assembly/hierarchy owner that
   loads the canonical BMW VHF vehicle root; otherwise follow only that exact
   owner-producing edge.

## Deliberate non-claims

This frontier keeps all of these false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready          = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready    = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready  = false
BODY0_bind_frame_proof_ready                          = false
vehicle_world_transform_ready                         = false
```

It does not use:

- callgraph adjacency as frame identity;
- `thiscall` ABI as owner/class identity;
- helper names as transform semantics;
- an identity affine delta assumption;
- VHF body-MEB local frame as an assumed vehicle root;
- a new runtime capture or original-game execution.

## Why this is the shortest next proof

`FUN_007927c0` is already the shared spawn bridge used by the symbolic BODY0
relation. Starting from `PhysicsParticipant::Restart` avoids searching arbitrary
runtime callers, while freezing its complete fan-out prevents selecting only the
known physics sink and ignoring a parallel assembly/render sink. Once the exact
receiver/argument flow is known, the VHF owner join is a pointer-ownership proof,
not a broad renderer reverse-engineering task.
