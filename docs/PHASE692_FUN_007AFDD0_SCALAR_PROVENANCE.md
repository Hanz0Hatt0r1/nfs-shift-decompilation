# Phase 692 — `FUN_007afdd0` machine scalar provenance frontier

Phase 691 removes the arbitrary basis callback from the composed persistent
outer-update path. The remaining external boundary is exactly four f32 scalar
values consumed by the recovered `FUN_007afdd0` source core:

```text
squared_magnitude_test
sqrt_magnitude
sine
cosine
```

Phase 692 does not guess those values. It adds a static-only provenance stage
for the targeted Ghidra instruction export so the next machine-backed step can
be driven by exact instruction evidence.

## New analyzer

```text
tools/ghidra/analyze_fun_007afdd0_scalar_provenance.py
```

Output format:

```text
SHIFT.Fun007afdd0ScalarProvenance/1
```

Inputs are both:

- the original `SHIFT.GhidraFunctionInstructions/2` row for `FUN_007afdd0`;
- the corresponding `SHIFT.Fun007afdd0BasisRotationStatic/1` Phase 680 report.

The analyzer rejects the join unless the Phase 680 machine byte count and
SHA-256 exactly match the raw instruction export and structured p-code varnodes
are complete.

## Facts frozen by this phase

The report extracts without semantic ranking:

- every direct CALL site and exact flow target;
- the unique direct call to `FUN_00900c40` (`0x00900c40`) when present;
- the unique direct call to `FUN_00900b10` (`0x00900b10`) when present;
- every `FST`, `FSTP` or `MOVSS` candidate that performs a structured dword
  STORE;
- structured p-code dependency slices rooted at those STORE operations;
- all other direct calls as unresolved helper candidates.

The scalar provenance frontier is considered structurally ready only when the
sine and cosine direct callsites are each unique and at least one structured
f32 store candidate exists.

That readiness is **not** machine scalar-production readiness.

## No store-role guessing

Every f32 store candidate is emitted with:

```text
source_role = null
```

and all four Phase 691 scalar roles are emitted with:

```text
assigned_store_candidate = null
```

Phase 692 intentionally does not assign a store by address order, nearest CALL,
stack-slot displacement, or apparent mathematical shape. A later source/machine
join must prove those identities.

## Remaining blockers made explicit

Even a structurally ready report retains blockers for:

- scalar store-role mapping;
- exact sqrt helper identity;
- floating return-register provenance across CALL p-code;
- ambient x87 control-word/MXCSR state.

This is important because Ghidra CALL p-code does not by itself prove which x87
or SSE register contains a helper return value. Therefore a nearby f32 store is
not promoted to a sine/cosine result merely because it follows the known helper
call.

`machine_scalar_production_ready` remains `false` and
`host_libm_substitution_allowed` remains `false`.

## Static runner

```text
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_fun_007afdd0_scalar_provenance.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/fun_007afdd0_scalar_provenance
```

The runner first executes the existing Phase 680 targeted export/freeze and then
builds:

```text
fun_007afdd0_scalar_provenance.json
```

It uses the already analyzed Ghidra project and does not launch the game.

## Regression coverage

Synthetic `SHIFT.GhidraFunctionInstructions/2` fixtures cover:

- exact sine/cosine direct target recovery;
- preservation of an unrelated helper as an unresolved call candidate;
- dword x87 store candidate extraction;
- source-role fields remaining unassigned;
- duplicate trig-helper callsites blocking frontier readiness;
- Phase 680 machine-SHA mismatch rejection;
- malformed structured p-code rejection;
- Phase 680 structured-varnode gate rejection.

## Next gate

The useful next artifact is a real Phase 692 report from the existing analyzed
`SHIFT.exe` Ghidra project. With that report, development can join recovered C
local-variable/store roles to exact machine stores, identify the sqrt callee,
and then inspect the trig/sqrt callees and inherited floating-control state.

Until that evidence exists, the Phase 691 typed scalar provider remains the
correct fail-closed native boundary.
