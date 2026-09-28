# Phase 483 — acceptance-to-provider handoff

## Goal

Phase 483 formalizes the storage handoff around provider selection.

## Before selection

The acceptance helper reads the currently bound physics-system row table at `physics_system+0x3c` and scalar count at `physics_system+0x34`.

The provider acceptance predicate (`+0x14`) therefore evaluates the **pre-selection logical matrix domain**.

## On provider acceptance

`FUN_007b3820` replaces the physics-system storage bindings with provider accessors:

- `+0x0c` → row-pointer table → `physics_system+0x3c`;
- `+0x04` → output vector → `physics_system+0x40`;
- `+0x08` → factor workspace → `physics_system+0x44`;
- `+0x2c` → workspace-size value propagated to BODY `+0xa8`.

The actual provider addresses are the fixed static regions reconstructed in Phases 433–435.

## After selection

The later `FUN_007b3f40` provider path invokes vtable `+0x20` cleanup and eventually vtable `+0x18` solve. The provider solve functions are parameterless and operate on the fixed global provider storage.

## Key consequence

The acceptance RLE pattern and the provider factor topology are **not required to match** because they live at different stages:

`acceptance → pre-selection matrix sparsity`

`factor topology → post-selection provider workspace writes`

This provides the architectural reason for the distinction introduced in Phases 454 and 465.

## Scope boundary

This phase records pointer rebinding and stage separation. It does not claim cell-for-cell equivalence between the pre-selection matrix and the provider packed workspace.
