# Process 1 — `Vehicle::InitVehicle` render-root delta input frontier

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

Merged PR #1331 makes the semantic outer Vehicle-root -> canonical BMW VHF
HIERARCHY-root relation positive as setup-fixed affine, but deliberately leaves
its numeric matrix closed.  The exact remaining value is:

```text
delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
producer    = FUN_00795d60
lifetime    = Vehicle::InitVehicle setup state
```

The existing delta-provenance contract already proves the three stores and their
terminal p-code roots.  The immediate unresolved upstream input is the stack
pointer passed as `FUN_00795d60` parameter 3 by the unique retail caller:

```text
FUN_00798df0 / MWL::Core::Vehicle::InitVehicle
0x007990ed -> FUN_00795d60

FUN_00795d60(
    this,
    param_1,
    local_2390,
    *(void **)((int)this + 0x1d00),
    param_1
);
```

This shard bounds only the exact `local_2390` producer frontier.  It does not
reopen frame ownership or infer a numeric delta from source order.

## INPUT

`tools/ghidra/analyze_outer_vehicle_render_root_delta_initvehicle_input.py`
requires:

- positive merged `SHIFT.OuterVehicleBMWVHFRootRelation/1`;
- retail `SHIFT.GhidraEvidenceDatabase/1` files `binary.json`, `functions.jsonl`,
  `callgraph.jsonl`, `strings_xrefs.jsonl`;
- exact retail decompiler source with SHA-256
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

It revalidates:

```text
SHIFT.exe MD5 = 705af8b420e5eb1e3834ac43d5533c6b
FUN_00798df0 size/ABI/mnemonic fingerprint
FUN_00795d60 size/ABI/mnemonic fingerprint
MWL::Core::Vehicle::InitVehicle source label
.\Source\Vehicle\Vehicle.cpp source label
unique direct caller FUN_00798df0 -> FUN_00795d60
exact callsite 0x007990ed
exact decompiled param3 source local = local_2390
```

Invocation:

```bash
python3 tools/ghidra/analyze_outer_vehicle_render_root_delta_initvehicle_input.py \
  out/shift_ghidra_database \
  /path/to/SHIFT.exe.c \
  --json-out out/initvehicle_render_root_delta_input_frontier.json
```

No original-game execution or runtime capture is required.

## OUTPUT

New bounded contract:

```text
SHIFT.OuterVehicleRenderRootDeltaInitVehicleInputFrontier/1
```

The analyzer extracts exactly one `FUN_00798df0` source definition, locates the
source statement that corresponds to the already-proven target call, and emits
all `local_2390` references before and after that statement.

Pre-call references are classified as:

```text
local-declaration
direct-local-write
direct-function-call-reference
other-call-reference
other-local-reference
```

Only direct writes and pre-call call references are placed on the producer
candidate worklist.  A source reference to `FUN_xxxxxxxx` is additionally joined
to the retail direct callgraph when possible.  That join records physical
callsite context only; it does not prove that the callee writes the pointer.

The output therefore gives the next static pass a finite worklist:

```text
exact local_2390 producer statements
+ exact directly referenced producer functions/callsites
-> targeted instruction/value analysis only for those candidates
-> exact three setup scalars
-> finite outer->VHF matrix
```

## CONSUMER

Immediate Process 1 consumer:

```text
SHIFT.OuterVehicleRenderRootDeltaInitVehicleInputFrontier/1
        |
        v
candidate-only targeted instruction/value slices
        |
        v
selected BMW delta_local numeric materialization
        |
        v
SHIFT.OuterVehicleBMWVHFRootRelation/1 numeric matrix
        |
        v
SHIFT.BMWBody0BindFrameProof/1
```

Once a provenance-bearing finite relation matrix exists, merged Process 2 PR
#1329 can consume it through its strict normalized admission seam.

## GATES_CHANGED

New bounded gates may become positive:

```text
initvehicle_delta_param3_source_local_binding_ready = true
initvehicle_delta_input_reference_frontier_ready    = true
initvehicle_delta_input_producer_worklist_ready     = true  # only if candidates exist
```

The playable-slice semantic gates remain fail-closed:

```text
selected_BMW_render_root_delta_numeric_ready           = false
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready   = false
BODY0_bind_frame_proof_ready                           = false
vehicle_world_transform_ready                          = false
```

## LIMITS

- Source lexical order is not all-path value proof.
- Passing `local_2390` to a function is not proof that the callee writes it.
- Callgraph adjacency is not value provenance.
- No number is inferred from variable names or nearby constants.
- The positive setup-fixed affine semantics from PR #1331 are consumed, not
  re-adjudicated.
- No VHF/resource hierarchy is used to infer executable ownership.
- No runtime capture or original-game execution is used.
- No broad resource audit is performed.

If a pre-call `local_2390` reference cannot be classified, the report keeps an
explicit blocker for that reference instead of silently ignoring it.

## TESTS

`tests/test_ghidra_outer_vehicle_render_root_delta_initvehicle_input.py` covers:

- exact positive source/callsite binding;
- finite producer candidate classification;
- direct-callgraph join for a referenced producer function;
- unique direct caller enforcement;
- retail source SHA drift rejection;
- param3 source-local drift rejection;
- explicit unclassified-reference blocker;
- upstream numeric preclaim rejection;
- source-label ownership drift rejection;
- lexical/callgraph context never promoted to numeric value proof.

## NEXT_OWNER

Process 1 should run this analyzer against the exact retail `SHIFT.exe.c` and
follow **only** the emitted `producer_candidates` / `direct_fun_target_worklist`.
For call candidates, use targeted `SHIFT.GhidraFunctionInstructions/2` value
slices to prove whether and how they write `local_2390`.  For direct local writes,
resolve only their RHS roots.  Stop as soon as the three exact setup scalars are
source-backed; then evaluate the already-proven setup-fixed affine relation and
compose the existing numeric BODY0->outer matrix into
`SHIFT.BMWBody0BindFrameProof/1`.
