# Process 1 — one-command BMW SDF vehicle-assembly receiver proof

## BLOCKER

The shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
Construction target identity and BODY0 `pos/ori -> persistent origin/basis`
continuity are already positive. The remaining frame join is now bounded to:

```text
SDF / HighDetailVehicle assembly construction frame
  -> canonical BMW VHF vehicle-root / assembly frame
```

Before attempting that semantic relation, the existing
`SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1` must establish the physical
receiver chain into the SDF loader.

## INPUT

The repository already contains the fail-closed analyzer and exact retail
anchors:

```text
FUN_0076df50
  0x0076e238 -> FUN_007615c0

FUN_007615c0
  0x007615ed -> FUN_007b6900
```

The only acquisition required is a targeted read-only instruction export for the
first two functions.

## OUTPUT

`tools/ghidra/run_bmw_sdf_vehicle_assembly_receiver_proof.py` combines that
acquisition and analysis into one command. It emits:

```text
SHIFT.BMWSDFVehicleAssemblyReceiverProofBundle/1
```

and preserves two explicit artifacts:

```text
01_bmw_sdf_vehicle_assembly_instructions.jsonl
02_bmw_sdf_vehicle_assembly_receiver_provenance.json
```

Only these targets are exported:

```text
FUN_0076df50
FUN_007615c0
```

The existing `run_shift_function_instructions.sh` keeps the Ghidra project
read-only and disables auto-analysis.

## Positive meaning

If the underlying receiver contract is ready, the bundle carries:

```text
SDF_loader_owner_receiver_continuity_ready = true
SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX = true
```

This proves only the physical `ECX` chain:

```text
FUN_0076df50 entry ECX
  == FUN_007615c0 entry ECX
  == FUN_007b6900 entry ECX
```

It deliberately keeps these false:

```text
SDF_model_to_VHF_vehicle_root_frame_relation_ready = false
BODY0_bind_frame_proof_ready                       = false
vehicle_world_transform_ready                      = false
```

Pointer identity is not coordinate-frame identity.

## Fail-closed behavior

If export fails, the runner writes a failure bundle and preserves partial
artifacts. If analysis fails, the validated instruction export is preserved. If
the analyzer produces a legitimate negative/ambiguous receiver result, the
runner completes with a `receiver-continuity-blocked` decision and does not
promote the frame relation.

## Reproduction

```bash
cd /home/pes/nfs-shift-decompilation

git pull

GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_bmw_sdf_vehicle_assembly_receiver_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_sdf_vehicle_assembly_receiver_proof
```

The single artifact to inspect after a completed run is:

```text
out/bmw_sdf_vehicle_assembly_receiver_proof/
  bmw_sdf_vehicle_assembly_receiver_proof_bundle.json
```

No original-game execution or runtime capture is required.

## CONSUMER

A positive bundle moves P1.1 to exactly one semantic proof:

```text
HighDetailVehicle assembly owner frame
  -> canonical BMW VHF vehicle-root frame
  -> SHIFT.BMWBody0BindFrameProof/1
```

A blocked bundle keeps the work limited to the reported ECX producer at the two
frozen callsites; it does not permit broad callgraph expansion.
