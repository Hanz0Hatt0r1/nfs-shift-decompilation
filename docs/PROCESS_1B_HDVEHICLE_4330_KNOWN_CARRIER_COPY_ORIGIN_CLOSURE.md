# Process 1B — HDVehicle+0x4330 known-carrier copy-origin closure

`SHIFT.P1B.HDVehicle4330KnownCarrierValueCopyOriginClosure/1` closes one narrow runtime store/copy class: a direct copy whose source is already an exact one of the 15 canonical P1B carrier values.

## Inputs

- `SHIFT.P1B.HDVehicle4330SourceSymbolAddressTaking/1`
  - 15 canonical carrier symbols;
  - 40 exact source-symbol occurrences;
  - 0 source-visible address-taking uses;
  - 0 non-call symbol-as-value uses.
- `SHIFT.P1B.HDVehicle4330BoundedRuntimePointerSeedCoverage/1`
  - 8 bounded seed/materialization domains;
  - 0 exact internal carrier hits.

## Adjudication

A direct runtime store or copy of an already-materialized exact carrier requires such a carrier value to exist first. The bounded source-visible and seed/materialization surfaces produce no such value.

Therefore, within this bounded origin class:

- direct known-carrier copy/store origins: **0**;
- an already materialized exact canonical carrier cannot seed a runtime-populated pointer table;
- the scoped copy-origin subset is complete and negative.

## Limits

This is not a global function-pointer store/copy theorem. The following remain open:

- reconstructed or cross-block values;
- runtime-populated/table-derived values;
- decoded/encoded pointers outside the bounded seed contracts;
- opaque helper returns or externally supplied addresses;
- runtime patching/generated code.

Accordingly the global runtime-generated/copied-function-pointer, generic store/copy, indirect-entry, manager identity and P1.3 gates remain fail-closed. Provider count remains 7.
