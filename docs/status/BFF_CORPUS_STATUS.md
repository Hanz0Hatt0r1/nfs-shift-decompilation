# BFF corpus status

## Current evidence

The local 2026-09-28 vehicle corpus contains 15 BFF archives:

- BMW_M3_E36.bff
- BMW_M3_E36_Cockpit.bff
- RENDER.bff
- 12 additional vehicle/cockpit archives from Vehicles.zip

The header/entry audit observed:

- 15,306 total archive entries;
- 15,286 Type-2 entries;
- 20 Type-0 entries;
- X12d value 0 in every audited archive;
- recurring vehicle and cockpit resource suffixes shared across multiple cars.

The raw evidence snapshot is stored in
evidence/vehicle_bff_corpus_audit_2026-09-28.json.

## Reproduction

Use the canonical BFF parser without payload decoding:

python tools/audit_vehicle_bff_corpus.py <directory-or-zip> -o corpus.json

The corpus auditor is inventory-only. Resource decoding remains the responsibility
of bff_audit.py, so an inventory pass cannot silently become an expensive decode pass.

## Interpretation boundary

The repeated logical suffixes show a shared resource layout across vehicle
archives, but they do not by themselves prove that the resources are byte-identical
or that they use identical runtime material parameters. Those claims require
decoded-payload or same-instance runtime evidence.
