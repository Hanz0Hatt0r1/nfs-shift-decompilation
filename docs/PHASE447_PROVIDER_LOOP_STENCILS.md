# Phase 447 — specialized-provider scaled update stencils

## Goal

Phase 447 records the source-order stencil behind scaled workspace updates in `FUN_007c7200` and `FUN_007cdfc0`.

For each pivot block it captures the active `local_10` range, the current `dVar1` loader form, and each expanded workspace destination written under that scale. The retail numeric RHS expression is not stored.

## Why this matters

The specialized provider source does not expose a clean row-at-a-time storage model. Some update loops use row-pointer lookups, some use flat workspace addresses, and some use array-form destinations. The stencil preserves these concrete source mechanisms without assigning semantic matrix names to them.

The `dVar1` source is carried across loop boundaries because the retail solver frequently loads the scale immediately before a normalization loop and reuses it across that loop.

Output-vector writes are excluded from the workspace stencil so forward-RHS/back-substitution activity stays in its own execution layer.

## Local audit

Against the supplied local `SHIFT.exe.c`, the extractor sees 40 pivot blocks for provider 0 and 34 for provider 1. Expanded scaled workspace-update sites are 2,862 for provider 0 and 1,901 for provider 1.

These counts are **source assignment-site counts after loop expansion**. They are not matrix non-zero counts and are not used to assign provider identity.

## Interpretation boundary

The stencil records address-level execution evidence only. Packed workspace aliasing and semantic cell ownership remain unresolved. The next layer can use these stencils together with pivot geometry and factor-pattern evidence to reconstruct exact dependency schedules.

Run locally with:

    python specialized_provider_loop_stencil_runtime.py SHIFT.exe.c
