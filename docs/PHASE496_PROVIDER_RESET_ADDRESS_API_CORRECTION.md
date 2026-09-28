# Phase 496 — provider reset address API correction

Phase 496 fixes a latent integration error introduced by Phase 494.

`SpecializedProvider` stores solve/identity/accessor fields, while reset and cleanup entry addresses are defined by the specialized-provider vtable lifecycle model.

The GDB probe therefore must resolve:

- provider 0 reset through `get_vtable_lifecycle(0).reset_function`;
- provider 1 reset through `get_vtable_lifecycle(1).reset_function`.

The previous `get_provider(...).reset_function` references were invalid because that dataclass intentionally does not expose a reset field.

## Validation

Source-smoke coverage now explicitly rejects the old attribute access and requires the vtable-lifecycle API.

## Scope

This is a compatibility correction only. It does not change the provider reset ABI, capture schema, selector semantics, or runtime evidence format.