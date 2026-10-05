# Process 1 — outer Vehicle visual-hierarchy frontier

## Playable-slice blocker

The target Linux slice already has an exact native-session numeric
`BODY0 -> outer Vehicle` matrix.  The remaining transform blocker is the missing
relation from that outer Vehicle/car-body runtime domain to the canonical BMW VHF
vehicle-root/assembly frame used by resource-driven rendering.

`SHIFT.OuterVehicleChassisOwnerJoin/1` narrowed the runtime owner to the
car-body/CHASSIS child initialized as:

```text
*([HDVehicle + 0x3fe8]) + 0x340
```

Inside `FUN_007ac4d0` the `+0x534` embedded child is passed to
`FUN_007a3d60`.  The previous phase correctly did **not** promote that fact to a
VHF-frame identity claim.

This phase adds the finite analyzer needed to continue that exact edge instead
of reopening broad renderer or BODY-construction searches.

## Static anchors

The saved retail database provides three independent anchors for
`FUN_007a3d60`:

1. it has exactly one direct caller in the current callgraph, the proven
   car-body/CHASSIS initializer `FUN_007ac4d0` at `0x007accc3`;
2. that call is made with the already-proven `EDI + 0x534` receiver;
3. the function owns all four retail vehicle LOD names:

```text
_WHEEL_FL_LODA
_WHEEL_FR_LODA
_WHEEL_RL_LODA
_WHEEL_RR_LODA
```

The same function contains the direct call:

```text
0x007a402a -> thunk_FUN_00d5bf10 (0x0047bdf0)
```

whose concrete target is `FUN_00d5bf10`.

These anchors are sufficient to call the lane **vehicle visual/LOD setup**. They
are not sufficient to call the resolver result a VHF node or vehicle root.

## Analyzer

`tools/ghidra/analyze_outer_vehicle_visual_hierarchy_frontier.py` consumes:

- the normal Ghidra evidence database (`binary.json`, `functions.jsonl`,
  `strings_xrefs.jsonl`, `callgraph.jsonl`);
- `evidence/outer_vehicle_chassis_owner_join_retail.json`;
- a targeted `SHIFT.GhidraFunctionInstructions/2` export containing exactly
  `FUN_007a3d60` and `FUN_00d5bf10`.

It then:

- revalidates the retail executable identity and mnemonic fingerprints;
- revalidates the four `_WHEEL_*_LODA` string/xref witnesses;
- revalidates the unique chassis-init -> visual-setup call edge;
- revalidates the exact `0x007a402a -> 0x0047bdf0` resolver call;
- runs the existing all-path IA-32 register-provenance engine at that callsite;
- follows only the direct fallthrough block and inventories lexical EAX
  consumers/stores after the call;
- uses structured Ghidra p-code to inventory simple register-relative memory
  accesses inside concrete `FUN_00d5bf10`.

The output format is `SHIFT.OuterVehicleVisualHierarchyFrontier/1`.

## Targeted export command

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/outer_vehicle_visual_hierarchy_instructions.jsonl \
  FUN_007a3d60 FUN_00d5bf10

python tools/ghidra/analyze_outer_vehicle_visual_hierarchy_frontier.py \
  out/shift_ghidra_database \
  evidence/outer_vehicle_chassis_owner_join_retail.json \
  out/outer_vehicle_visual_hierarchy_instructions.jsonl \
  --json-out out/outer_vehicle_visual_hierarchy_frontier.json
```

No game execution or new runtime capture is required.

## What a positive result means

A ready frontier proves:

```text
HDVehicle
  -> car-body/CHASSIS child
  -> +0x534 visual subobject
  -> FUN_007a3d60 vehicle visual/LOD setup
  -> exact physical resolver callsite 0x007a402a
  -> finite resolver result-consumer frontier
```

It still deliberately leaves these gates false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                  = false
vehicle_world_transform_ready                 = false
```

## Required next join

After running the targeted export, the next proof should use the analyzer output
to answer one bounded question: **what source-backed RenderHierarchy/VHF runtime
object, if any, is represented by the physical resolver result or its immediate
consumer?**

The promotion criterion remains strict.  A wheel-name hit, a lexical EAX store,
a decompiler type, or membership in the car-body visual lane is not enough.
The result must be joined to an independently identified RenderHierarchy/VHF
runtime object and then to the canonical BMW assembly/root affine relation.
