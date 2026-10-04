# Process 1 — outer Vehicle owner candidate roles

## Playable-slice blocker reduced

The first playable Linux slice still needs a source-backed BODY0 bind frame before
retail Phase 704/706 can publish the changing BMW world transform.  The previous
outer-`Vehicle` receiver pass left three anonymous `__thiscall` sinks that could
possibly lead toward the vehicle assembly/VHF owner.

A targeted instruction export for:

```text
FUN_007876e0
FUN_007afb60
FUN_007ac2f0
FUN_007633b0   proven HDVehicle control lane
```

now reduces that search to two concrete static continuations.

New contract:

```text
SHIFT.OuterVehicleOwnerCandidateRoles/1
```

Analyzer:

```text
tools/ghidra/analyze_outer_vehicle_owner_candidate_roles.py
```

## Proven machine-level roles

### `FUN_007876e0` — remove from owner-forward search

The function is call-free.  It reads receiver-side physics scalars including
`+0x1b0`, `+0xb14/+0xb20` and `+0x8a4/+0x8b0` and writes a three-component result
through its output argument.  It has no owner-forward call edge.

This does **not** say the receiver has no class identity.  It says this sink does
not provide a path from the outer setter into another owner domain, so following
it cannot close the current VHF-owner join.

### `FUN_007afb60` — one exact forwarded receiver

The function reaches exactly one direct callee:

```text
0x007afb6c -> FUN_007aef50
```

No instruction before the call overwrites ECX, so the physical entry receiver is
forwarded unchanged.  The remaining body of `FUN_007afb60` performs float-vector
accumulation through arguments.

The owner question for this branch therefore reduces to `FUN_007aef50`.

### `FUN_007633b0` → `FUN_007ac2f0` — concrete HDVehicle child chain

The already-proven HDVehicle control lane contains:

```text
ESI = entry ECX
EDX = [ESI+0x3fe8]
ECX = [EDX]
ECX += 0x340
CALL FUN_007ac2f0
```

So one retail invocation of `FUN_007ac2f0` uses the receiver expression:

```text
*(*(HDVehicle_control + 0x3fe8)) + 0x340
```

The historical `+0x340` update-child signature is useful for targeting, but is
**not** promoted to pointer equality with any previously recovered object and is
not frame identity evidence.

### `FUN_007ac2f0` — concrete sub-owner edges

Inside the callee:

```text
ESI = entry ECX
EDI = [ESI+0x34]
```

The object at `+0x34` receives two adjacent virtual calls through vtable offsets:

```text
+0xe0
+0xe4
```

The same function also forwards an embedded receiver:

```text
ECX = ESI + 0x534
CALL FUN_007a4360
```

These are concrete owner/subobject edges.  They still do not identify a VHF
hierarchy owner.

## Static context join

The broad Ghidra evidence database independently identifies:

```text
FUN_0076df50  MWL::Core::HighDetailVehicle::Init
```

and shows that it directly calls, in the same init region:

```text
FUN_007615c0  vehicle solver setup
FUN_007ac4d0  car-body / CHASSIS initialization
```

`FUN_007ac4d0` is anchored by strings including:

```text
car body
CHASSIS
.joi.xml
trigger1 / trigger2
front bumper / rear bumper
```

This is the highest-value current construction owner join.  Callgraph adjacency
alone remains insufficient; physical receiver/value provenance at these calls is
still required.

## Next minimal export

Only three functions are required next:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/outer_vehicle_chassis_owner_join_instructions.jsonl \
  0x0076df50 \
  0x007ac4d0 \
  0x007aef50
```

Purpose:

1. prove the physical ECX/owner relationship at the `HighDetailVehicle::Init`
   calls to `FUN_007615c0` and `FUN_007ac4d0`;
2. trace concrete writes/forwards performed by the car-body/CHASSIS initializer;
3. either close or eliminate the only remaining `FUN_007afb60 -> FUN_007aef50`
   forwarded-owner branch.

No retail runtime execution or new capture is needed.

## Fail-closed state

This pass deliberately keeps false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                 = false
vehicle_world_transform_ready                = false
```

It does not promote:

- identical `+0x340` offsets to object identity;
- callgraph adjacency to pointer equality;
- callgraph adjacency to frame identity;
- the Phase 645 resource/VHF bind matrix to a physics pose;
- the car-body/CHASSIS label to a numerical BODY0↔VHF bind transform.
