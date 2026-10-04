# Process 1 — outer Vehicle transform storage domain

## Playable-slice blocker reduced

`SHIFT.OuterVehicleTransformSinkReceiverProvenance/1` separates the physical ECX
receiver domains at the complete `FUN_007927c0` fan-out, but it intentionally
stops before deciding which receiver actually stores outer-Vehicle transform
state.

This stage converts that pointer-routing frontier into exact receiver-relative
state bytes without assuming that any object is the VHF hierarchy root.

Contract:

```text
SHIFT.OuterVehicleTransformStorageDomain/1
```

Analyzer:

```text
tools/ghidra/analyze_outer_vehicle_transform_storage_domain.py
```

## Why this is the next finite proof

The retail static database already narrows the three anonymous `__thiscall`
lanes further:

```text
FUN_007876e0(this, ptr)
  direct-call leaf in callgraph

FUN_007afb60(this, float*, float*, float*)
  0x007afb6c -> FUN_007aef50

FUN_007ac2f0(this, char)
  reached from outer Vehicle setter at 0x007928f0
  reached from proven HDVehicle setter at 0x007634df
```

The last fact is important: `FUN_007ac2f0` is a shared downstream hook. Its
presence is therefore not a unique VHF-owner signal and must not be promoted to
outer/VHF frame identity merely because it follows a transform setter.

The receiver report determines which `__thiscall` sink(s), if any, receive the
**outer setter entry ECX itself** on every reachable path. Only those functions
are instruction-analyzed by this stage.

## Inputs

1. ordinary saved retail Ghidra export directory containing at least
   `binary.json`, `functions.jsonl`, and `callgraph.jsonl`;
2. positive `SHIFT.OuterVehicleTransformSinkReceiverProvenance/1`;
3. one `SHIFT.GhidraFunctionInstructions/2` JSONL containing exactly the sink
   function(s) selected by the receiver report as deterministic direct
   outer-receiver candidates.

The retail identity remains:

```text
SHIFT.exe MD5 705af8b420e5eb1e3834ac43d5533c6b
```

The analyzer also freezes these topology anchors:

```text
0x007928f0 : FUN_007927c0 -> FUN_007ac2f0
0x007634df : FUN_007633b0 -> FUN_007ac2f0
0x007afb6c : FUN_007afb60 -> FUN_007aef50
```

and exact fingerprints for the candidate sinks, the proven HDVehicle setter and
`FUN_007aef50`.

## Selecting the targeted instruction export

Inspect the receiver report first. The selected functions are exactly rows where:

```text
physical_ecx_role == "thiscall-receiver"
ECX_origin_deterministic == true
ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths == true
callee != FUN_007633b0
```

For example, if that selection contains only `FUN_007876e0`:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/outer_vehicle_direct_storage_instructions.jsonl \
  FUN_007876e0
```

If the real report selects more than one function, export all selected targets;
the analyzer deliberately keeps the result ambiguous until their concrete side
effects separate them.

Then run:

```bash
python3 tools/ghidra/analyze_outer_vehicle_transform_storage_domain.py \
  out/shift_ghidra_database \
  out/outer_vehicle_transform_sink_receiver_provenance.json \
  out/outer_vehicle_direct_storage_instructions.jsonl \
  --json-out out/outer_vehicle_transform_storage_domain.json
```

This is a read-only static database workflow. The original game is not executed.

## What is proven

For every selected direct outer-receiver sink, the analyzer:

- runs the existing all-path IA-32 register-provenance engine;
- inventories p-code `STORE` operations;
- accepts a physical store only when one simple register-relative machine
  operand can be joined to exactly one p-code `STORE`;
- proves whether the store base is `entry:ECX` on all reachable paths;
- records exact displacement, width and receiver bytes;
- builds a conservative p-code backward value frontier for the stored value;
- inventories direct calls that may forward the owner when the sink is not a
  leaf.

A unique selected receiver plus unambiguous receiver-relative storage produces:

```text
outer_vehicle_transform_storage_domain_ready = true
```

This means only that exact bytes of the outer Vehicle receiver are now known to
hold transform/state data on this lane.

## Deliberate non-claims

The following remain false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready          = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready    = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready  = false
BODY0_bind_frame_proof_ready                          = false
vehicle_world_transform_ready                         = false
```

In particular this stage does not promote:

- equal ECX origin expressions to pointer equality;
- receiver-relative stores to VHF hierarchy ownership;
- a shared `FUN_007ac2f0` call edge to class or frame identity;
- p-code terminal roots to semantic position/orientation values;
- lexical adjacency or callgraph adjacency to coordinate-frame identity.

## Next proof

Once exact outer receiver field spans are available, the next static question is
finite:

```text
exact outer Vehicle transform field consumer(s)
  -> concrete assembly/hierarchy owner
  -> canonical BMW VHF vehicle-root owner
```

That consumer join decides whether the VHF root is identical to the outer root
or differs by a fixed affine transform. Only after that owner/storage join is
closed should position/orientation stack-value reconstruction be promoted into a
numeric bind matrix.
