# Process 1B — render-manager global-origin closure

## Scope

This handoff consumes the already-positive `SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1` proof and narrows the remaining external/unknown-origin frontier.

The exact retail xref rank for `DAT_00bc185c` contains **116** references in **80** functions and exactly **two** writes, both in `FUN_00d36210`:

```text
0x00d362ec  MOV [0x00bc185c],EAX
0x00d362f3  MOV dword ptr [0x00bc185c],ESI
```

The first is reached only after allocation (`0x46e0` bytes) and `FUN_0045ef50`; the constructor proof establishes `EAX origin = entry:ECX` on every reachable return. The second write stores the already-zeroed `ESI` (`0x00d36224 XOR ESI,ESI`).

Therefore every non-null value sourced through `DAT_00bc185c` has the exact `FUN_0045ef50` constructor identity. There is no source-backed external/unknown-origin replacement of the singleton global.

## Composition

The new contract is:

```text
SHIFT.P1B.RenderManagerGlobalOriginClosure/1
```

It is composed with the merged P1B closures for direct callees, copy/return persistence and derived subobjects. Those layers already prove that exact values read from the global do not acquire a second identity through the bounded direct receiver surface.

## Promoted bounded gates

```text
candidate_global_writer_surface_complete = true
candidate_global_non_null_origin_unique = true
external_or_unknown_origin_through_candidate_global_complete = true
external_or_unknown_origin_through_candidate_global_found = false
```

This is intentionally narrower than a global unknown-memory proof.

## Still fail-closed

Pointers materialized from unrelated/unknown memory, opaque helper returns, or non-vtable indirect setters remain open. Consequently these global gates stay false:

```text
arbitrary_unknown_memory_exact_root_alias_surface_complete
memory_load_opaque_runtime_reconstruction_complete
helper_non_vtable_setter_surface_complete
manager_374_join_to_hdvehicle_4330_complete
last_literal_0x004b86cf_rejected
p1_3_control_producer_complete
```

Provider count remains 7.

## Next step

Bound unknown-memory/helper-created exact-root candidates that do not originate at `DAT_00bc185c`. Only after that surface is closed should P1B revisit the final `manager+0x374 -> HDVehicle+0x4330` identity join and slot2 (`0x004b86cf`) adjudication.
