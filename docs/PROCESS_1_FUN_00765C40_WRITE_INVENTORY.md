# Process 1 — `FUN_00765c40` residual write/call inventory

## BLOCKER

P1.2b requires an exhaustive audit of source-visible `FUN_00765c40` side effects before Process 2 can remove the complete residual provider. Existing positive contracts already cover the selected query input, cache handle, `+0x38e0` hit/miss scalar, typed collision output, and four wheel `+0x738` load terms, but they do not prove that no other writes or side-effecting calls remain.

Because the full authoritative `SHIFT.exe.c` is not stored in the repository, the next safe step is a reproducible source-hash-locked inventory rather than an absence claim.

## OUTPUT

Adds:

```text
tools/ghidra/inventory_fun_00765c40_write_surface.py
```

The probe emits `SHIFT.Fun00765c40WriteSurfaceInventory/1` from exactly the `FUN_00765c40` body in the pinned PC-retail export. It records a **raw write/call inventory**:

- every simple or compound assignment line;
- the assignment LHS and operator;
- whether the line mentions `param_1` or `this`;
- direct `FUN_xxxxxxxx` call sites;
- referenced `DAT_` / `PTR_` / `LAB_` / `UNK_` globals;
- hexadecimal offset frequency.

## Safety boundary

This inventory is **not a proof that all writes target HDVehicle**. Local aliases, wheel pointers, output records, stack temporaries, and callee side effects can all hide or redirect mutations.

The report therefore keeps these gates false:

```text
residual_side_effects_classified = false
absence_of_other_writes_proven = false
safe_to_remove_FUN_00765c40_provider = false
manual_pointer_and_alias_review_required = true
```

Known closed surfaces are included only as review hints:

```text
HDVehicle+0x38dc returned cache handle
HDVehicle+0x38e0 hit/miss scalar
four wheel +0x738 f64 load terms
```

They are not automatically filtered out because the audit must first verify each assignment's pointer provenance and order.

## Usage

Run against the exact authoritative full Ghidra C export:

```bash
python3 tools/ghidra/inventory_fun_00765c40_write_surface.py \
  /path/to/SHIFT.exe.c \
  --output /tmp/fun_00765c40_write_surface.json
```

The probe fails closed unless the source SHA-256 is:

```text
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

## Review order

For P1.2b, review the generated report as follows:

1. classify every assignment against an already-positive contract or a new residual state target;
2. resolve local aliases before assigning an object domain to a store;
3. inspect direct callees as possible side-effect carriers until their contracts prove otherwise;
4. preserve exact source order for any state that Process 2 must reproduce;
5. only after every write/call is accounted may Process 1 publish an absence/exhaustiveness claim.

## TESTS

`tests/test_process1_fun_00765c40_write_inventory.py` verifies target extraction, assignment-vs-comparison handling, call/global/offset collection, source-hash locking, and the fail-closed documentation boundary.

## GATES_CHANGED

None. P1.2b remains open and the provider count remains 7. This tooling only makes the next exhaustive side-effect audit deterministic and reviewable.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Generate the inventory from the pinned PC-retail `SHIFT.exe.c`, classify every assignment/callee against the existing P1.2 contracts, and publish only the residual writes that remain positively source-backed after pointer/alias review.
