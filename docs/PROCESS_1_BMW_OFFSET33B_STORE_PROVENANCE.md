# Process 1 — BMW `offset33b` store provenance

## Playable-slice blocker reduced

`SHIFT.BMWBody0VehicleRootBindRelation/1` proves the symbolic chassis bind:

```text
M_BODY0_to_outer_vehicle_root.translation = -offset33b

offset33b = {
    HDVehicle+0x33b0,
    HDVehicle+0x33b8,
    HDVehicle+0x33c0
}
```

The remaining BMW-specific value gate is the three numeric doubles produced by
`FUN_0076b280` after the SDF load.  This phase adds the finite instruction-level
frontier needed to recover those values without treating source/decompiler names,
callgraph adjacency, or an untyped memory displacement as numeric proof.

Contract:

```text
SHIFT.BMWOffset33bStoreProvenance/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_store_provenance.py
```

## Exact retail boundary

The analyzer requires:

- `SHIFT.exe`, MD5 `705af8b420e5eb1e3834ac43d5533c6b`;
- exact `FUN_0076b280` entry `0x0076b280`;
- size `7796`;
- `__thiscall`;
- mnemonic SHA-256
  `9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6`;
- the already-merged symbolic relation contract, which must still keep
  `BMW_numeric_offset33b_ready = false`.

The targeted instruction export is deliberately one function only.

## Targeted export

From the retail Ghidra project:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/bmw_offset33b_fun_0076b280_instructions.jsonl \
  FUN_0076b280
```

Then run:

```bash
python3 tools/ghidra/analyze_bmw_offset33b_store_provenance.py \
  out/shift_ghidra_database \
  out/bmw_offset33b_fun_0076b280_instructions.jsonl \
  --json-out out/bmw_offset33b_store_provenance.json
```

## What is proved

For every simple register-relative p-code `STORE` overlapping bytes
`+0x33b0..+0x33c7`, the analyzer records:

- exact machine instruction and memory operand;
- store width and touched offset33b field bytes;
- all-path origin of the target base register;
- whether the target base is exactly `FUN_0076b280` entry `ECX`;
- backward structured p-code value slice;
- terminal root kinds (`constant`, memory/register/unique, etc.);
- recent direct CALLs preceding the store.

Positive `offset33b_store_provenance_ready` requires all 24 bytes of the three
fields to be covered by stores whose target base is exactly entry `ECX` on every
reachable path, with no unresolved offset33b-looking complex target operand.

This joins the physical stores to the existing source-backed HDVehicle field
semantics.  It does **not** make their numeric values ready.

## Fail-closed boundary

The contract keeps:

```text
BMW_numeric_offset33b_ready                         = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready    = false
BODY0_bind_frame_proof_ready                        = false
vehicle_world_transform_ready                       = false
```

Even a constant-only dependency slice is not auto-promoted to a `double` value.
The analyzer also refuses to invent:

- CALL return values;
- x87 state across unsupported boundaries;
- SDF field meaning for an arbitrary memory root;
- `this` identity from a displacement alone;
- value identity from callgraph adjacency.

## Next decision after a retail run

The resulting root set makes the next work finite:

1. if all three values reduce to exact constants through supported operations,
   add a narrow numeric evaluator for those exact operations;
2. if roots are loads from already materialized BMW SDF/init data, join the
   exact addresses/fields to `SHIFT.BMWBody0BindResourceMaterialization/1`;
3. if a value is a direct/narrow helper CALL result, trace only that helper's
   return provenance;
4. only if static reproduction fails, request a narrowly targeted three-double
   value witness after `FUN_0076b280` rather than a broad runtime dump.

This keeps the next work on the shortest path to the native vehicle world
transform.
