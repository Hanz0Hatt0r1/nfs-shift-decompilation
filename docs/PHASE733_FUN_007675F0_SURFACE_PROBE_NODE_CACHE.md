# Phase 733 — FUN_007675f0 surface-probe node cache ownership

Phase 733 recovers the PC retail ownership and refresh policy for the node pointer that Phase 732 forwards into native `FUN_00759210`.

## Exact caller ownership

`FUN_007675f0` has one direct PC retail caller: `FUN_00769ef0` at `0x0076a1c7`.

The caller loads:

```text
mov edi,[esi+0x120]
...
push edi
call FUN_007675f0
```

Inside `FUN_007675f0`, `mov edx,[ebx+0x8]` reads stack argument 1 and forwards that pointer into `FUN_00759210`. It is not an object-field `+0x8` dereference. `FUN_00759210` immediately preserves `edx` as its node base and reads the already-recovered node fields from it.

Therefore the immediate PC owner is `HDVehicle+0x120`.

## Setup state

The vehicle setup path explicitly initializes `HDVehicle+0x120` to null at `0x00763496`.

No initial value for `+0x128/+0x130/+0x138` is required for the recovered policy because a null cached node forces lookup before the cached displacement can suppress refresh.

## Refresh policy in FUN_00769ef0

The caller keeps the last exact BODY0 origin at:

- `HDVehicle+0x128` — X f64;
- `HDVehicle+0x130` — Y f64;
- `HDVehicle+0x138` — Z f64.

When `+0x120` is non-null, `FUN_00769ef0` computes the exact f64 3D displacement from current chassis BODY0 `+0/+8/+0x10`, squares it, and compares the sum with the f64 constant at `0x00b09180` (`0.01`). The lookup refresh condition is strict:

```text
cached_node == null || squared_displacement > 0.01
```

When refresh is required, the source:

1. narrows current BODY0 XYZ to f32 for the lookup query;
2. passes the current cached node as the second lookup argument;
3. calls `FUN_00717cd0` through the global receiver at `0x00c10f68`;
4. stores the returned pointer back to `HDVehicle+0x120`;
5. stores the exact current BODY0 f64 XYZ to `+0x128/+0x130/+0x138`.

The last-position commit happens after every lookup call, including a null result. A null cached node therefore forces lookup again on the next evaluation.

## Native contract

`SHIFT.Fun007675f0SurfaceProbeNodeCache/1` implements only the source-backed cache policy. It exposes `Fun00717cd0SurfaceProbeNodeLookupProvider` with two exact boundary inputs:

- the f32-narrowed current BODY0 query position;
- the previous cached node pointer.

The native helper owns null-first refresh, strict `> 0.01` displacement refresh, previous-node forwarding, and last-position commit timing.

## Deliberate boundary

This phase does not name or implement `FUN_00717cd0`'s world/node-search semantics. It also does not yet replace the selected-session direct per-pass node boundary, because the surrounding `FUN_00769ef0` active-path/null-node gate must be preserved when the lookup is wired.

The seven top-level external provider boundaries therefore remain unchanged.

## Regression

`shift_runtime_fun_007675f0_surface_probe_node_cache_check` covers:

- exact offsets `+0x120/+0x128/+0x130/+0x138`;
- null-first lookup;
- no refresh while displacement stays within the strict threshold;
- refresh above `0.01` squared displacement;
- previous-node forwarding;
- exact last-position commit after lookup;
- repeated lookup after a null result;
- fail-closed missing-provider and non-finite input paths.
