# Process 1 — one-command outer Vehicle/VHF receiver static proof

## Playable-slice blocker reduced

The outer Vehicle -> VHF frame proof now has two fail-closed static stages:

```text
SHIFT.OuterVehicleVHFRootRelationFrontier/1
SHIFT.OuterVehicleTransformSinkReceiverProvenance/1
```

This runner removes the remaining manual coordination between the saved retail
Ghidra evidence, the targeted instruction export and the receiver-domain report.

Contract:

```text
SHIFT.OuterVehicleVHFReceiverStaticProofBundle/1
```

Runner:

```text
tools/ghidra/run_outer_vehicle_vhf_receiver_static_proof.py
```

## One command

```bash
cd /home/pes/nfs-shift-decompilation

python3 tools/ghidra/run_outer_vehicle_vhf_receiver_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  evidence/bmw_body0_vehicle_root_bind_relation.json \
  out/outer_vehicle_vhf_receiver_static_proof \
  --ghidra-home /opt/ghidra \
  --timeout-seconds 300
```

The runner:

1. validates/builds the exact source-labelled Restart -> outer Vehicle setter
   frontier from the saved Ghidra database;
2. opens the existing Ghidra project through the established read-only/noanalysis
   targeted exporter;
3. exports exactly `FUN_007927c0`;
4. runs the all-path ECX receiver proof;
5. partitions the surviving anonymous `__thiscall` owner candidates by physical
   origin expression relative to the proven HDVehicle control lane.

The original game is not executed.

## Persisted artifacts

```text
01_outer_vehicle_vhf_root_relation_frontier.json
02_outer_vehicle_setter_instructions.jsonl
03_outer_vehicle_sink_receiver_provenance.json
outer_vehicle_vhf_receiver_static_proof_bundle.json
```

Each failure stage writes a bundle and preserves every already-valid earlier
artifact.

## Decision classes

A completed bundle returns one of:

### `resolve-receiver-ambiguity`

At least one owner candidate has multiple/derived reachable ECX origins. Resolve
only those exact callsites before doing callee semantics or stack-transform work.

### `deterministic-owner-domain-partition`

All anonymous `__thiscall` candidates have deterministic ECX origins. The bundle
separates:

- candidates sharing the same *origin-expression set* as the proven HDVehicle
  sink;
- candidates with a distinct origin-expression set.

That grouping is a worklist optimization only. Repeated memory expressions are
not pointer equality because intervening state may change.

## Deliberate non-claims

The runner always keeps:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

It does not promote receiver groups to pointer/class/frame identity and does not
evaluate stack position/orientation values yet.

## Next proof

For each deterministic surviving `__thiscall` domain, prove the callee's concrete
writes/forwards and owner-producing edge. The first source-backed owner that
joins to the canonical BMW VHF hierarchy loader becomes the precise target for
the final outer Vehicle-root -> VHF-root affine relation. Only then should the
corresponding transform argument values be evaluated.
