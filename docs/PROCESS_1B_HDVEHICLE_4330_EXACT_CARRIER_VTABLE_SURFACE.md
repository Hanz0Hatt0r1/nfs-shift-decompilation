# Process 1B — exact `HDVehicle+0x4330` carrier vtable surface

## Scope

This P1.3B slice checks whether any of the 15 already-proven exact `HDVehicle+0x4330` materializer/consumer carrier functions is installed as a target in the pinned Ghidra vtable-candidate export.

The carrier identities come from merged retail machine contracts. `vtables.json` is navigation/cross-check evidence only.

Pinned export:

- format: `SHIFT.GhidraVtableCandidates/1`
- SHA-256: `15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed`

Run:

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_exact_carrier_vtables.py \
  vtables.json \
  --output out/p1b_hdvehicle_4330_exact_carrier_vtable_surface.json
```

## Result

The pinned inventory contains:

```text
2,533 candidate vtables
22,416 slots
15 exact HDVehicle+0x4330 carrier entrypoints checked
0 matching vtable targets
```

The checked carrier set spans the four proven root-derived materializers plus their exact direct/forwarded consumers from `SHIFT.HDVehicle64e8RootDerived4330MaterializerPersistenceClosure/1` and `SHIFT.HDVehicle64e8Large4330ConsumerPersistenceClosure/1`.

This closes the finite static-vtable-target subset: none of those exact carrier entrypoints is installed in any exported vtable candidate.

## Fail-closed boundary

This result does **not** rule out runtime-generated, copied or encoded function pointers; unresolved indirect entry; callee-created data aliases; or persistence of the `HDVehicle+0x4330` pointer itself through non-vtable memory.

Therefore `global_runtime_derived_4330_alias_surface_complete`, the `manager+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf` rejection, P1.3 completion and provider removal all remain false. Provider count stays 7.

## Next step

Trace runtime/generated indirect entry and non-root-derived `HDVehicle+0x4330` data aliases. Any positive escape must be joined to its eventual consumer before the manager identity gate can change.
