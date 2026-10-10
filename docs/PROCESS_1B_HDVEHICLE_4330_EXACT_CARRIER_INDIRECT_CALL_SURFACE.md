# Process 1B — exact `HDVehicle+0x4330` carrier indirect-call surface

## Scope

This P1.3B slice checks the 15 already-proven exact `HDVehicle+0x4330` materializer/consumer carrier functions for Ghidra-recorded indirect-call edges.

The SQLite index is navigation/cross-check evidence only. Exact carrier identity comes from merged PC retail 1.02 machine contracts.

Pinned database:

- SHA-256: `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`
- supported format: `SHIFT.GhidraSQLiteIndex/1` or `/2`

Run:

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_exact_carrier_indirect_calls.py \
  shift_ghidra.sqlite \
  --output out/p1b_hdvehicle_4330_exact_carrier_indirect_call_surface.json
```

## Result

The index contains 19,500 `indirect=true` call edges overall, proving the call class is represented. Across the 15 exact carrier functions, the count is zero.

```text
whole-index indirect call edges = 19,500
exact carriers checked          = 15
carrier indirect call edges     = 0
```

This closes the bounded subset where an exact carrier itself performs a Ghidra-recorded indirect dispatch.

## Fail-closed boundary

The result does not rule out indirect entry *into* a carrier, callbacks registered elsewhere, runtime-generated/copied function pointers, or `HDVehicle+0x4330` data aliases created outside the carrier set.

Therefore `global_runtime_derived_4330_alias_surface_complete`, the `manager+0x374 -> HDVehicle+0x4330` join, final `0x004b86cf` rejection, P1.3 completion and provider removal all remain false. Provider count remains 7.

## Next step

Trace indirect entry into the exact carriers and runtime-generated/copied pointer paths; separately continue non-root-derived `HDVehicle+0x4330` data alias provenance. Any positive escape must be joined to its eventual consumer before the manager identity gate changes.
