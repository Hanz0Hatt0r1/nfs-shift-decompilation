# Process 1B — incoming direct-call frontier for exact `HDVehicle+0x4330` carriers

## Scope

After closing the bounded vtable, static-table and carrier-local `CALLIND` subsets, this slice inventories direct calls **into** the 15 already-proven exact `HDVehicle+0x4330` materializer/consumer carriers.

The Ghidra SQLite callgraph is navigation/cross-check evidence. A direct edge into a carrier is not, by itself, proof that the receiver/argument is the exact `HDVehicle+0x4330` pointer.

## Result

The pinned SQLite export contains 25 direct callsites targeting the carrier set:

```text
25 total incoming direct callsites
14 callsites whose caller is another exact carrier
11 callsites from outside the exact-carrier set
7 unique external caller functions
```

The external callers are:

- `FUN_00491d86`
- `FUN_0074da70`
- `FUN_00795d60`
- `FUN_00798df0`
- `FUN_00aa2850`
- `Unwind@00a7063f`
- `Unwind@00a72322`

`FUN_00798df0` owns five of the eleven external callsites and reaches `FUN_00772200`, `FUN_0076df50` and `FUN_007c3b00`. The remaining six callsites are distributed one each across the other six external caller records.

## Fail-closed boundary

This is a worklist, not a positive alias proof. Every external callsite still requires exact machine receiver/argument provenance before it can be admitted or rejected as an alternate route carrying `HDVehicle+0x4330`.

The two Ghidra records named `Unwind@...` are deliberately left unresolved. Their label alone is insufficient to classify them as metadata/non-executable for semantic purposes.

Therefore external receiver provenance remains incomplete; indirect entry into carriers remains open; `global_runtime_derived_4330_alias_surface_complete`, the manager `+0x374` identity join, final `0x004b86cf` rejection and P1.3 remain false. Provider count stays 7.

## Next step

Adjudicate the seven external caller functions by exact machine receiver provenance. Start with the one-hop wrapper `FUN_00491d86` and the five-call `FUN_00798df0` cluster, then resolve the two `Unwind@` records by executable ownership rather than name.
