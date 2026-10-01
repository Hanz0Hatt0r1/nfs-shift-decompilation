# Phase 631 — fixed-step constraint refresh from CSRF

Phase 630 closes the prepared relation → BODY-owned endpoint-sample ownership
join. Phase 631 moves that join onto every admitted native fixed step without
changing the legacy Phase 628 GBCF-only mode.

## New runtime option

`shift_runtime` now accepts:

```text
--constraint-sample-relation-frame FILE.csrf
```

The option is valid only together with:

```text
--generated-body-constraint-frame FILE.gbcf
```

GBCF still carries prepared BODY state and BODY-owned sample storage. CSRF
carries the source-order top-level relation ownership and raw local rows needed
by `FUN_007b3ed0`.

## Two cardinality domains

Phase 631 keeps the two source-backed domains separate.

Workspace/top-level relation cardinality:

- BMW JOINT relations: 4;
- BMW HINGE relations: 4;
- BMW BAR relations: 20.

BODY-owned endpoint-sample cardinality after the Phase 630 ownership join:

- JOINT endpoint samples: 8;
- HINGE endpoint samples: 8;
- BAR endpoint samples: 40.

When CSRF is present, startup admission compares **relation counts** to the
native physics workspace. It does not compare endpoint-sample counts to the
workspace relation counts.

After refresh, the generated GBCF sample counts must instead equal the exact
endpoint coverage reported by the CSRF ownership join.

The legacy Phase 628 GBCF-only path remains unchanged and retains its old
prepared-fixture count gate for backward compatibility.

## Fixed-step order

With GBCF + CSRF, every admitted fixed step now executes:

```text
prepared BODY state / BODY-owned sample storage (GBCF)
  + source-order relation ownership / raw local rows (CSRF)
  → FUN_007b3ed0
      → FUN_007b2da0 JOINT refresh
      → FUN_007b2de0 HINGE refresh
      → FUN_007b2f70 BAR refresh
  → refreshed GBCF
  → FUN_007bc680 BODY contribution generation
  → FUN_007bb8d0 BODY sparse-row storage
  → FUN_007ba570 global matrix/RHS accumulation
  → exact generated matrix/RHS == SBFR gate
  → FUN_007b2210 selected reset
  → FUN_007b0f20 builtin solve
  → optional existing FUN_007b4110 post-solve projection
```

The refresh result is produced from the original prepared GBCF on every step;
the packet is not mutated in place.

## Startup gates

CSRF mode requires:

1. solver-frame mode;
2. GBCF mode;
3. GBCF BODY count equal to the native workspace;
4. CSRF BODY count equal to the native workspace;
5. CSRF JOINT/HINGE/BAR relation counts equal to workspace relation counts;
6. complete Phase 630 endpoint ownership/side/scalar identity validation;
7. refreshed endpoint counts equal to the generated GBCF sample counts;
8. exact refreshed generated matrix/RHS equality with SBFR.

All existing participant-identity, workspace and provider-absent gates remain
in force.

## Telemetry

`SHIFT.NativeRuntimeFrameLoop/1` now reports:

- `physics_constraint_sample_relation_frame_loaded`;
- `physics_constraint_sample_relation_joint_count`;
- `physics_constraint_sample_relation_hinge_count`;
- `physics_constraint_sample_relation_bar_count`;
- `physics_constraint_sample_relation_refreshed_joint_samples`;
- `physics_constraint_sample_relation_refreshed_hinge_samples`;
- `physics_constraint_sample_relation_refreshed_bar_samples`;
- `physics_constraint_sample_relation_refresh_steps`;
- `physics_constraint_sample_relation_values_stored_in_packet=false`.

The ordinary generated-BODY counters remain active. In CSRF mode they expose
the endpoint-sample cardinality rather than top-level relation cardinality.

## Full-cardinality regression

Linux Vulkan CI adds a separate Phase 631 fixture while preserving the Phase
628 smoke unchanged.

The new fixture uses the real BMW structural shape:

- 11 BODY;
- 4 JOINT relations → 8 endpoint samples;
- 4 HINGE relations → 8 endpoint samples;
- 20 BAR relations → 40 endpoint samples;
- 40 solver scalars.

All BODY/sample numerical inputs are zero with identity BODY frames,
`inverse_scalar=0`, zero BODY tensors and zero projection scales. Therefore
the refreshed/generated pre-reset matrix and RHS remain exactly zero. The SBFR
resets all 40 rows, making the builtin solve deterministic while testing the
scheduler, ownership and cardinality joins rather than inventing retail
dynamics.

For three fixed steps CI requires:

- 3 CSRF refresh steps;
- 3 generated GBCF→SBFR joins;
- relation counts 4/4/20;
- endpoint/generated sample counts 8/8/40;
- zero matrix/RHS join error;
- zero Vulkan validation errors.

## Boundary after Phase 631

Phase 631 removes prepared post-refresh sample values from the CSRF-enabled
fixed-step path: the native runtime now regenerates them through the
source-backed `FUN_007b3ed0` stage before contribution assembly.

Still open:

- authentic per-frame BODY transforms/positions and raw relation local inputs;
- runtime reset-node selection from the retail `sample+0x70 & 1` relation
  state instead of an externally prepared SBFR reset list;
- provider-present refresh/generation behavior;
- applying solved BODY state into persistent vehicle transform/motion state.

The next safe source-backed step is the reset-selection boundary feeding
`FUN_007b2210`.
