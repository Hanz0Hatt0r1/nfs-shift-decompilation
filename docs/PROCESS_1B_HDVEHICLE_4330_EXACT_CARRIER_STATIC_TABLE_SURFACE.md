# Process 1B — exact `HDVehicle+0x4330` carrier static-table surface

## Scope

This P1.3B slice checks the pinned Ghidra `static_tables.jsonl` export for literal little-endian 32-bit absolute pointers to the 15 already-proven exact `HDVehicle+0x4330` materializer/consumer carrier functions.

Pinned export:

- SHA-256: `798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2`
- 55,066 records
- 956,464 declared bytes
- 684,472 raw bytes available for exact scanning

Run:

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_exact_carrier_static_tables.py \
  static_tables.jsonl \
  --output out/p1b_hdvehicle_4330_exact_carrier_static_table_surface.json
```

## Result

All 15 proven exact carrier addresses have zero literal absolute-pointer hits in the exported static-table raw bytes.

```text
55,066 static-table records
684,472 scanned raw bytes
15 exact carrier addresses
0 matching absolute function pointers
```

Together with `SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1`, this eliminates two finite static registration subsets for the known exact carriers: direct vtable slots and literal static-table pointers.

## Fail-closed boundary

The result is not a whole-image pointer-provenance proof. Runtime-generated, copied or encoded function pointers, computed destinations, arbitrary heap/global stores and callee-created data aliases remain open.

Consequently `global_runtime_derived_4330_alias_surface_complete`, `manager_374_join_to_hdvehicle_4330_complete`, final `0x004b86cf` rejection, P1.3 completion and provider removal stay false. Provider count remains 7.

## Next step

Trace runtime-generated/copied indirect entry and non-root-derived `HDVehicle+0x4330` data aliases. Any positive escape must be joined to its later consumer before the manager identity gate changes.
