# Phase 740 — `FUN_00765c40` query-cache lifetime

Phase 740 narrows the residual `FUN_00765c40` boundary by moving ownership of the caller cache slot `HDVehicle+0x38dc` into `NativeVehicleProviderSession`.

## PC retail source result

The already-frozen Phase 370/666 collision-query evidence establishes that:

- `FUN_00765c40` passes the caller cache handle into the `FUN_007b0710` query record;
- the query record stores that handle at its `+0x30` cache slot;
- `FUN_00765c40` stores the handle returned by `FUN_007b0710` back to `HDVehicle+0x38dc`;
- therefore the next `FUN_00765c40` call consumes the previous query result as caller-owned persistent state.

The setup path additionally initializes `HDVehicle+0x38dc` to zero. The native session represents this exact seed as `std::nullopt` rather than inventing pointer/object semantics for the handle.

## Active runtime contract

`SHIFT.Fun00765c40ExternalPassResult/3` splits the residual pass into an input request and output result:

- `Fun00765c40ExternalPassInput.cached_handle` is supplied by native persistent session state before the residual provider runs;
- for the selected BMW domain, `Fun00765c40ExternalPassInput.world_position` is the Phase 739 native world position before the residual provider runs;
- the provider must expose the query input it actually consumed as an audit witness;
- `Fun00765c40ExternalPassResult.returned_cache_handle` is committed back to native session state immediately after the residual pass returns.

The validator rejects a provider that reports consuming a different cache handle, and for the selected BMW domain also rejects a different world position.

## Lifetime/order

The runtime order is now explicit:

```text
initial setup: cache = null / source zero
pass 0 current BODY observation
native selected-BMW world-position derivation
residual FUN_00765c40(input.cache = persistent cache)
commit returned handle to persistent cache
later pass-0 anchors / half-step
pass 1 current BODY observation
residual FUN_00765c40(input.cache = pass-0 returned handle)
commit pass-1 returned handle
...
next explicit step pass 0 consumes the previous step's final handle
```

This mirrors caller-state lifetime without internalizing the collision provider.

## Transactionality

`NativeVehicleProviderSession` snapshots `fun_00765c40_query_cache_handle_` before an explicit step and before a retail inner batch. Any exception restores the prior handle together with BODY state, contact outer state, scheduler state and telemetry. Failed work therefore cannot leak a speculative cache handle into the next query.

## What remains external

Phase 740 does **not**:

- name the physical meaning of the returned handle;
- implement the collision/world lookup provider under `FUN_007b0710`;
- internalize `HDVehicle+0x38e8` miss fallback;
- internalize the four `FUN_00765c40` load terms or other unproven side effects;
- reduce the seven top-level external provider boundaries.

The next bounded target is the setup ownership and lifetime of `HDVehicle+0x38e8`.
