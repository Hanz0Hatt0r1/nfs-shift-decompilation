# Process 1D — exact-carrier static pointer surface

This P1.3D slice bounds two static pointer-registration avenues for the 15 already-proven exact HDVehicle/wheel carrier functions.

Inputs are the pinned retail Ghidra candidate exports:

- `vtables.json` SHA-256 `15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed`;
- `static_tables.jsonl` SHA-256 `798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2`.

Run:

```bash
python3 tools/ghidra/analyze_p1d_slot3_exact_carrier_static_pointers.py \
  vtables.json static_tables.jsonl \
  --output out/p1d_slot3_exact_carrier_static_pointer_surface.json
```

## Result

The vtable candidate inventory contains:

```text
2,533 candidate vtables
22,416 slots
0 slots targeting any of the 15 exact carriers
```

The static-table export contains:

```text
55,066 records
956,464 declared bytes
684,472 raw_hex bytes available for exact byte scanning
0 little-endian 32-bit absolute pointers to any of the 15 exact carriers
```

This closes only these two exported static candidate subsets. It means the current Ghidra vtable candidates do not install an exact carrier as a slot target and the current static-table candidate records do not contain a literal absolute pointer to one of those carriers.

## Fail-closed boundary

The result does **not** rule out:

- runtime-generated or copied function pointers;
- encoded pointers;
- computed destinations;
- heap/global pointer stores outside the exported static-table records;
- unresolved indirect calls;
- callee-created aliases;
- callbacks registered through nonliteral or transformed values.

The Ghidra table exports remain navigation/cross-check artifacts. Exact object identity continues to come from merged retail machine contracts. Therefore `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D and aggregate P1.3 all remain false, and the external provider count remains 7.

Next work should trace runtime/generated pointer stores and callee-created aliases from the exact carrier set, joining any positive escape to its later consumer before changing semantic gates.
