# Process 1 — BMW SDF vehicle-assembly receiver provenance

## Playable-slice blocker reduced

The dynamic BMW world-transform path is blocked on a positive
`SHIFT.BMWBody0BindFrameProof/1`.

The existing construction proof already establishes the retail data path:

```text
vehicles/physics/suspension/aarm_multilink.sdf
  -> FUN_007b6900 SDF BODY descriptor
  -> FUN_007b3670 persistent BODY builder
  -> BODY0 origin + basis
```

but correctly stops in the SDF model construction frame. Phase 645 independently
proves the canonical body-MEB transform in the VHF vehicle hierarchy. The
remaining frame relation therefore cannot be closed by matching BODY/MEB names
or by assuming an identity bind matrix.

The saved retail Ghidra database narrows the SDF construction owner to this
direct call chain:

```text
FUN_0076df50
  debug/source anchor: MWL::Core::HighDetailVehicle::Init
  call 0x0076e238 -> FUN_007615c0

FUN_007615c0
  vehicle physics assembly path
  references fl/fr/rl/rr wheel + spindle, rear_axle, fuel_tank, steering names
  call 0x007615ed -> FUN_007b6900

FUN_007b6900
  proven SDF BODY loader
```

Callgraph edges and method strings identify the finite investigation path, but
they do not show which physical object is in `ECX` at either callsite. That
receiver provenance is the blocker removed by this pass.

## Analyzer

```text
tools/ghidra/analyze_bmw_sdf_vehicle_assembly_receiver_provenance.py
```

Output contract:

```text
SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1
```

The analyzer consumes:

1. the ordinary saved retail Ghidra evidence directory (`binary.json`,
   `functions.jsonl`, `callgraph.jsonl`, `strings_xrefs.jsonl`);
2. one targeted `SHIFT.GhidraFunctionInstructions/2` JSONL containing
   `FUN_0076df50` and `FUN_007615c0`.

It reuses the finite all-path IA-32 register-provenance engine already used by
the `FUN_00765470` BODY-owner proof. `ECX` is evaluated immediately before each
direct call, before the engine applies caller-saved call clobbering.

The retail anchors are frozen by exact executable identity, mnemonic hashes and
callsite edges:

```text
SHIFT.exe MD5 705af8b420e5eb1e3834ac43d5533c6b

FUN_0076df50
  mnemonic SHA-256 73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda
  0x0076e238 -> FUN_007615c0

FUN_007615c0
  mnemonic SHA-256 0b2268dceb26dfaff8814b4091e50d48371b74083ac6d41e3d50da99cc036a22
  0x007615ed -> FUN_007b6900

FUN_007b6900
  mnemonic SHA-256 154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81
```

The exact `MWL::Core::HighDetailVehicle::Init` string must also remain anchored
to `FUN_0076df50`. The string is source/debug corroboration only; it is not a
coordinate-frame proof.

## Targeted export

No new Java exporter and no full Ghidra re-analysis are required. The existing
instruction exporter already emits instruction bytes, operands, control flow and
raw p-code.

From the analyzed Ghidra project:

```bash
GHIDRA_HOME=/opt/ghidra

"$GHIDRA_HOME/support/analyzeHeadless" \
  /home/pes/ghidra_projects/shift shift \
  -process SHIFT.exe \
  -noanalysis \
  -scriptPath "$PWD/tools/ghidra" \
  -postScript ShiftFunctionInstructionExporter.java \
    "$PWD/out/bmw_sdf_vehicle_assembly_instructions.jsonl" \
    0x0076df50 0x007615c0
```

Then:

```bash
python3 tools/ghidra/analyze_bmw_sdf_vehicle_assembly_receiver_provenance.py \
  out/shift_ghidra_database \
  out/bmw_sdf_vehicle_assembly_instructions.jsonl \
  --json-out out/bmw_sdf_vehicle_assembly_receiver_provenance.json
```

This is a database read only: `SHIFT.exe` is not executed and Ghidra auto-analysis
is not restarted.

## Positive proof meaning

A ready report requires both all-path equalities:

```text
ECX before 0x0076e238 == FUN_0076df50 entry ECX
ECX before 0x007615ed == FUN_007615c0 entry ECX
```

For direct IA-32 `__thiscall` calls, those equalities compose physically as:

```text
FUN_0076df50 entry ECX
  == FUN_007615c0 entry ECX
  == FUN_007b6900 entry ECX
```

This proves that the SDF loader runs on the same physical receiver propagated
from the vehicle initialization object along this retail path.

Any memory reload, derived pointer, call-clobbered receiver, divergent CFG
origin, or other non-entry producer blocks the corresponding link. A unique but
different entry register is reported as verified non-identity rather than being
promoted heuristically.

## Deliberate non-claim

Receiver identity is **not coordinate-frame identity**.

Even a positive receiver chain keeps all of these false:

```text
SDF_model_to_VHF_vehicle_root_frame_relation_ready = false
BODY0_bind_frame_proof_ready                       = false
vehicle_world_transform_ready                      = false
```

In particular, this pass does not assume:

- `HighDetailVehicle this` is numerically a VHF transform;
- an object pointer defines the local coordinate basis of all owned resources;
- the SDF model frame equals the VHF root frame;
- BODY0 local equals body-MEB local;
- the BODY0 bind matrix is identity;
- the method-name debug string is frame evidence.

A positive report instead changes the next static question from an unspecified
SDF ownership problem to one narrow semantic join:

```text
HighDetailVehicle assembly owner frame
  -> VHF vehicle-root frame
```

That join, plus the exact BODY0 `pos`/`ori` values from the already-identified
retail SDF bytes, is what can eventually produce
`SHIFT.BMWBody0BindFrameProof/1`.

## Regression coverage

`tests/test_ghidra_bmw_sdf_vehicle_assembly_receiver_provenance.py` covers:

- `entry:ECX` continuity through preserved callee-saved registers across helper
  calls on both links;
- a memory-derived ECX replacement before the SDF loader;
- divergent CFG paths producing `entry:ECX` vs `entry:EDI`;
- wrong direct-call target rejection;
- retail mnemonic fingerprint drift rejection;
- missing `HighDetailVehicle::Init` source/debug anchor rejection.

No synthetic positive receiver result is promoted to a bind-frame proof.
