# Process 1 — outer Vehicle/VHF storage static-proof runner

## Playable-slice blocker reduced

The current outer-`Vehicle`-root -> VHF-root proof already has two bounded static
stages:

```text
SHIFT.OuterVehicleVHFReceiverStaticProofBundle/1
  -> exact FUN_007927c0 receiver routing

SHIFT.OuterVehicleTransformStorageDomain/1
  -> exact receiver-relative transform/state field spans
```

Before this pass, moving from the first stage to the second still required a
manual read of the receiver report followed by a hand-written targeted Ghidra
export. This runner removes that coordination edge.

New contract:

```text
SHIFT.OuterVehicleVHFStorageStaticProofBundle/1
```

Implementation:

```text
tools/ghidra/run_outer_vehicle_vhf_storage_static_proof.py
```

## One-command chain

The runner executes:

```text
saved retail Ghidra evidence
+ symbolic BODY0 -> outer Vehicle relation
+ existing analyzed Ghidra project
        |
        v
#1244 receiver static-proof runner
        |
        +-> Restart/spawn frontier
        +-> read-only/noanalysis FUN_007927c0 export
        +-> sink receiver provenance
        |
        v
select deterministic direct outer-receiver __thiscall sinks
        |
        v
read-only/noanalysis targeted export of exactly those sinks
        |
        v
#1245 transform storage-domain analyzer
        |
        v
exact outer receiver field spans
```

The selected storage targets are never hardcoded. They are exactly the rows in
the current receiver report satisfying:

```text
physical_ecx_role == "thiscall-receiver"
ECX_origin_deterministic == true
ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths == true
callee != FUN_007633b0
```

Targets are sorted by address before the second export so the artifact is
reproducible.

## Invocation

```bash
GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_outer_vehicle_vhf_storage_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  evidence/bmw_body0_vehicle_root_bind_relation.json \
  out/outer_vehicle_vhf_storage_static_proof
```

The Ghidra project is opened only through the existing targeted exporter, which
uses `-readOnly -noanalysis`. `SHIFT.exe` itself is not executed.

## Artifacts

The first three artifacts come from the existing receiver runner:

```text
01_outer_vehicle_vhf_root_relation_frontier.json
02_outer_vehicle_setter_instructions.jsonl
03_outer_vehicle_sink_receiver_provenance.json
```

This runner adds:

```text
04_outer_vehicle_direct_storage_instructions.jsonl
05_outer_vehicle_transform_storage_domain.json
outer_vehicle_vhf_storage_static_proof_bundle.json
```

The original receiver-runner bundle is also preserved.

## Zero-target behavior

A receiver report may legitimately prove that no anonymous `__thiscall` sink
receives the outer setter entry receiver directly. In that case the runner does
**not** invoke Ghidra with an empty target list and does not manufacture a storage
owner. It emits:

```text
status = blocked-by-receiver-routing
```

with the storage export/analyzer stages marked `blocked_by_upstream_gate`.

## Multiple-target behavior

If more than one deterministic direct outer-receiver sink survives, all selected
functions are exported together and passed to the #1245 analyzer. The analyzer
keeps the storage domain unresolved until concrete side effects separate the
receivers; the runner never selects one based on lexical order, function size or
callgraph shape.

## Positive handoff

When #1245 reports a unique, structurally valid storage domain, the bundle
exposes:

```text
outer_vehicle_transform_storage_domain_ready = true
outer_vehicle_transform_field_spans_ready     = true
```

and carries `exact_outer_receiver_field_spans` forward verbatim.

The next proof is then finite:

```text
exact outer Vehicle transform field consumer(s)
  -> concrete assembly/hierarchy owner
  -> canonical BMW VHF vehicle-root owner
```

## Deliberate non-claims

Even a positive storage bundle keeps these false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready          = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready    = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready  = false
BODY0_bind_frame_proof_ready                          = false
vehicle_world_transform_ready                         = false
```

The runner does not promote:

- receiver routing to pointer equality;
- receiver-relative field storage to VHF ownership;
- a shared post-transform hook to class identity;
- static field spans to semantic position/orientation values;
- any static adjacency to coordinate-frame identity.

## Failure behavior

Every downstream failure preserves the artifacts already produced plus a bundle
containing the failed stage. A failed export or storage analysis is never turned
into a partial positive frame proof.
