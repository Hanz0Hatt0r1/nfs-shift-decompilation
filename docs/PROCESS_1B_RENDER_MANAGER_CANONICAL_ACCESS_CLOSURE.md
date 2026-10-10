# Process 1B — canonical render-manager access closure

## Scope

This slice composes the bounded canonical access classes for the exact render-manager singleton slot `DAT_00bc185c`.

The shipped image contains exactly **115** little-endian occurrences of `0x00bc185c`:

- 112 direct loads;
- 2 direct stores;
- 1 address-of-slot literal at `0x004fb9af`.

The partition is exhaustive. The one address literal is immediately dereferenced and does not represent an outer-root value literal.

A separate simple reconstruction scan covers 38,128 `MOV r32,imm32` seeds and 267 same-register add/sub/LEA transitions within the bounded lookahead. It finds one literal production (the known address-of-slot site) and **zero** non-literal productions of `0x00bc185c`.

## Origin and propagation

`SHIFT.P1B.RenderManagerGlobalOriginClosure/1` proves that every non-null value written to the canonical slot originates from `FUN_0045ef50` and the only other writer stores zero.

The merged copy/return and bounded-callee closures prove, for exact direct slot loads:

- exact-root memory stores = 0;
- exact-root pushes = 0;
- bounded direct receiver targets = 17/17 closed;
- known returned-root persistence/dispatch = false.

## Contract

```text
SHIFT.P1B.RenderManagerCanonicalAccessClosure/1
```

Promoted bounded gates:

```text
canonical_render_manager_slot_access_surface_complete = true
canonical_raw_slot_occurrence_partition_complete = true
canonical_hidden_simple_arithmetic_slot_access_found = false
canonical_non_null_origin_unique = true
canonical_direct_propagation_escape_found = false
```

## Fail-closed boundary

This does not prove the absence of a numerically equal exact-root pointer synthesized from unrelated/unknown memory or returned by an opaque helper without ever passing through `DAT_00bc185c`. It also does not close non-vtable setter paths globally.

Therefore the final manager join, `0x004b86cf` rejection and aggregate P1.3 remain false. Provider count remains 7.
