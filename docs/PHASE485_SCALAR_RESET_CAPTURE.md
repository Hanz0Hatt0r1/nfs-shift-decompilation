# Phase 485 — runtime capture of scalar reset selectors

## Goal

Phase 485 extends the existing GDB SDF probe with an observer breakpoint at `FUN_007b2210`. Every scalar-reset dispatch is recorded as one JSONL event before the retail function executes.

## Captured fields

Each event records:

- `frame_index` from the existing `FUN_007b3f40` frame-entry observation;
- monotonically increasing `call_index`;
- `physics_system` (`ECX`);
- raw `provider_pointer` from `physics_system+0x48`;
- first provider vtable word (`provider_vtable`) when the pointer is nonzero;
- exact `provider_id` only when the vtable matches the recovered provider-0/1 vtable;
- `scalar_count`;
- selector `param_1` from `[ESP+0x04]`;
- raw caller return address from `[ESP]`;
- register snapshot.

The event stream is written to:

`scalar_reset_events.jsonl`

## Provider identification

The probe does not infer provider identity merely from a nonzero pointer. It dereferences the pointer's first word and accepts provider 0/1 only on an exact vtable match.

A nonzero pointer with an unknown vtable becomes `backend=unknown` and fails validation. This prevents accidental attribution when another object shares the same storage slot.

A null provider pointer is classified as `builtin`.

## ABI basis

`FUN_007b2210` is `__thiscall`, so the probe reads:

`ECX` → `physics_system`

`[ESP+0x04]` → `param_1` selector

`[ESP]` → caller return address

This matches the source-backed Phase 482 ABI.

## Why this matters

Phase 484 established the static chain:

`constraint record → selector source → FUN_007b2210 → provider +0x1c`

Phase 485 now captures the runtime side of that chain. A real capture can therefore answer:

- which selectors are actually dispatched;
- how many reset events occur per frame;
- which provider vtable is active for each event;
- which caller return sites generate the events.

The caller return address is intentionally preserved raw. Its mapping to the three source call groups is a subsequent correlation step.

## Scope boundary

This phase observes the selector dispatch and provider identity boundary only. It does not infer matrix semantics, coefficient values, constraint names, or physical units.

Unknown provider identities are fail-closed rather than mapped heuristically.