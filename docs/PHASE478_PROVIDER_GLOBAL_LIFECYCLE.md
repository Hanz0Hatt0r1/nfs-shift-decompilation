# Phase 478 — specialized-provider global lifecycle

## Goal

Phase 478 separates global provider construction/destruction from the per-frame physics execution path.

## Provider 0

`FUN_00a8ca80` constructs global `DAT_00c23da8` through `FUN_007d2f70` and registers `FUN_00aa3800` with `atexit`. The teardown function calls provider shutdown `FUN_007c6e10`.

## Provider 1

`FUN_00a8caa0` constructs global `DAT_00c23dac` through `FUN_007cd980` and registers `FUN_00aa3810` with `atexit`. The teardown function calls provider shutdown `FUN_007cdb00`.

## Lifecycle separation

The evidence now supports three distinct layers:

`global bootstrap → provider object/vtable lifetime`

`FUN_007b3820 → runtime provider selection/rebind`

`FUN_007b3f40 → per-frame cleanup/common preparation/provider solve`

The selector-driven reset functions at vtable `+0x1c` remain a separate API. No direct frame-loop callsite is claimed without additional evidence.

## Why this matters

This resolves an apparent lifecycle tension: the provider object is global and persistent, while `FUN_007b3f40` can invoke `+0x20 cleanup` every frame. The reset selector should therefore not be treated as an unconditional per-frame initializer.

## Scope boundary

The phase records function relationships and `atexit` ownership only. It does not infer global initialization order beyond the provider-specific calls shown above, and it does not identify the underlying C++ provider classes.
