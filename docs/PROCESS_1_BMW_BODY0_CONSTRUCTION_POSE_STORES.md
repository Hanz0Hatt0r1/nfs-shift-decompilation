# Process 1 — BMW BODY0 construction pose STORE proof pass

## Blocker reduced

The first playable Linux slice still cannot publish the retail BMW world
transform because `SHIFT.BMWBody0BindFrameProof/1` is negative.

Process 1 already proved:

- BMW chassis identity is BODY index `0`;
- persistent BODY pose storage is origin `+0x00/+0x08/+0x10` (`f64`) plus basis
  `+0xd4..+0xf4` (`f32`);
- Phase 424 source-backed construction lowering for `FUN_007b3670` and helpers
  covers name, mass/inertia and two auxiliary vector groups;
- `FUN_007b7840` has no resolved-direct construction-bind invocation and its
  known external direct call belongs to the `FUN_00770e80` relation-refresh
  path.

The concrete missing observation is therefore construction-time machine/p-code
writes to the persistent BODY pose lanes.

This pass adds:

```text
SHIFT.BMWBody0ConstructionPoseStores/1
```

Tool:

```text
tools/ghidra/analyze_bmw_body0_construction_pose_stores.py
```

## Exact targeted export

Only the already source-backed BODY construction functions are requested:

```text
0x007b3670  FUN_007b3670
0x007bba90  FUN_007bba90
0x007bbb10  FUN_007bbb10
0x007bbb60  FUN_007bbb60
```

Generate the observational export from the existing analyzed Ghidra project:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/bmw_body0_construction_pose_instructions.jsonl \
  0x007b3670 0x007bba90 0x007bbb10 0x007bbb60
```

Then run:

```bash
python3 tools/ghidra/analyze_bmw_body0_construction_pose_stores.py \
  out/shift_ghidra_database \
  out/bmw_body0_construction_pose_instructions.jsonl \
  --json-out out/bmw_body0_construction_pose_stores.json
```

No original `SHIFT.exe` execution or runtime capture is involved. The export is
read-only static observation of the existing Ghidra database.

## What the pass proves mechanically

For every targeted function the analyzer:

1. revalidates the retail executable MD5 and exact function mnemonic hashes;
2. requires the exact four-row `SHIFT.GhidraFunctionInstructions/2` target set;
3. reconstructs CFG-wide incoming IA-32 general-register origins using the
   existing finite provenance engine;
4. requires structured p-code `STORE` rather than inferring writes from an x86
   mnemonic alone;
5. joins one simple register-relative machine memory operand to the STORE width;
6. selects only byte ranges overlapping the proven persistent BODY pose layout;
7. records the base register and all-path entry provenance at that instruction;
8. takes p-code `STORE input[2]` as the written value and emits the conservative
   backward dependency slice plus terminal roots.

The pose layout used for selection is exactly:

```text
origin f64: +0x00, +0x08, +0x10
basis  f32: +0xd4, +0xd8, +0xdc,
            +0xe0, +0xe4, +0xe8,
            +0xec, +0xf0, +0xf4
```

Frame-relative `EBP`/`ESP` matches are retained separately and are never
promoted to object evidence.

## Fail-closed semantics

A matching STORE is only a candidate. The pass deliberately keeps these false:

```text
construction_pose_target_parameter_ready = false
BODY0_pointer_at_construction_pose_write_ready = false
BODY0_bind_origin_basis_values_ready = false
BODY0_bind_frame_proof_ready = false
```

It does **not** infer semantics from:

- Ghidra parameter names/types;
- parameter ordinal;
- register position;
- a coincidental `+0xd4`/other offset;
- a dependency slice existing at all.

A positive candidate still needs two semantic joins:

```text
candidate target pointer
  -> persistent 0x170 BODY record
  -> exact BMW chassis BODY0

STORE terminal roots
  -> source-backed BODY[0] pos/ori or another independently proven bind producer
```

If no object-base pose STORE exists in this exact target set, the report does
not revive the rejected resolved-direct `FUN_007b7840` hypothesis. It instead
requests traversal of the exact construction side-effect/call chain to the next
writer.

## Structural ambiguity policy

Any p-code STORE whose machine memory target cannot be joined to exactly one
simple register-relative operand is retained as a blocker. Complex addressing
is not silently treated as absence of a pose writer.

This means a negative result is useful only when `construction_pose_store_discovery_complete=true`.
