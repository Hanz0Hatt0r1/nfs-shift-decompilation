# Process 1B — HDVehicle+0x4330 bounded indirect-entry coverage

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/1` composes the current fail-closed Process 1B evidence for three already-bounded indirect-entry classes on PC retail 1.02.

## Composed classes

| Class | Bounded surface | Exact P1B carrier hits |
| --- | ---: | ---: |
| Runtime callback registrations | 7 closed callback surfaces, 49 physical callback-capable callsites, 34 unique possible callback entrypoints | 0 |
| Static/source-visible function-pointer materialization | 4 closed materialization classes over the canonical 15 exact carriers | 0 |
| Computed/loader entry materialization | 3 closed classes: canonical CALL-next/POP, x87 saved-EIP extraction, PE loader-published entries | 0 |

The aggregate therefore has zero exact `HDVehicle+0x4330` carrier hits across all three bounded classes.

## Fail-closed boundary

This is not a global indirect-entry proof. The following remain open and are preserved as `false` gates:

- unresolved callback families, including `_bsearch` until its unusual comparator argument is machine-proven;
- application-owned wrappers not yet inventoried;
- generic function-pointer stores/copies;
- runtime-generated, copied, encoded or reconstructed code pointers;
- noncanonical non-x87 code-address synthesis;
- runtime patching and arbitrary heap/global function-pointer writes;
- opaque indirect dispatch;
- manager+0x374 to `HDVehicle+0x4330` identity join;
- final `0x004b86cf` rejection and aggregate P1.3 completion.

External provider count remains 7.

## Next step

Close `_bsearch` with machine evidence, then continue runtime-generated/copied/encoded exact-carrier pointer stores and noncanonical address synthesis before promoting `indirect_entry_into_carriers_ruled_out` or any downstream P1.3 gate.
