# Phase 502 — pre-PhysX/provider handoff contract

## Goal

Phase 502 joins the existing source-backed physics construction layers into one
machine-readable handoff contract:

`SDF → pre-PhysX construction → pre-acceptance storage → provider selection → provider rebinding → provider vtable lifecycle`

Contract:

`SHIFT.PrePhysXProviderHandoffRuntime/1`

## Cross-contract checks

The layer verifies that the already recovered modules agree on:

- solver scalar count produced by SDF construction and the pre-PhysX topology view;
- provider candidate dimensions (40 and 34 scalar domains);
- provider acceptance input `physics_system+0x3c`;
- provider state pointer `physics_system+0x48`;
- post-selection row/output/workspace rebinding;
- vtable offsets for acceptance, reset, solve, cleanup and workspace accessors.

A candidate with the same scalar dimension is only a dimension-compatible candidate.
The actual provider `+0x14` acceptance predicate remains runtime-dependent.

## CLI

    python tools/build_prephysx_provider_handoff.py sdf_report.json \\
      -o prephysx_provider_handoff.json

The command returns `0` when all cross-contract structural checks are ready and
`2` when a component is inconsistent or not ready.

## Scope boundary

This phase does not implement or name the underlying PhysX/provider C++ classes.
It also does not claim that the pre-selection matrix and provider packed workspace
share a cell-for-cell representation, and it does not establish numerical parity.
