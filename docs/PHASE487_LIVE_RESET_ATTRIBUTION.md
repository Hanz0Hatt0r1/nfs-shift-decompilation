# Phase 487 — live scalar-reset callsite attribution

## Goal

Phase 487 integrates the Phase 486 source/disassembly-backed callsite table directly into the Phase 485 GDB probe.

Each runtime `scalar_reset_events.jsonl` event now contains a `callsite` object with:

- exact caller `return_address`;
- exact `call_address`;
- constraint group (`JOINT/HINGE`, `SECONDARY`, `BAR`);
- ordinal within the group;
- group width;
- source line;
- observed selector and declared selector delta.

## Fail-closed behavior

An event is marked `capture_ready=false` when either the scalar schema validation or callsite attribution fails. Unknown caller return addresses are therefore never silently assigned to one of the three groups.

## Runtime chain

`constraint record → selector expression → direct CALL site → FUN_007b2210(selector) → provider vtable +0x1c(selector)`

The first three links are now representable from the same runtime event record, while the last link is represented by the provider pointer/vtable fields captured at the same breakpoint.

## Scope boundary

The attribution layer does not infer selector semantics beyond source grouping. It does not assign matrix coordinates, physical meanings, or provider class names.