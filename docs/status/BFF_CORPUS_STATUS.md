# BFF corpus status

## Current evidence

The local 2026-09-28 vehicle corpus contains 15 BFF archives:

- BMW_M3_E36.bff
- BMW_M3_E36_Cockpit.bff
- RENDER.bff
- 12 additional vehicle/cockpit archives from Vehicles.zip

The header/entry audit observed:

The corpus auditor also correlates normalized logical paths across archives. This is a name/layout correlation layer only; payload identity and runtime material identity remain separate proofs.

A separate raw-payload parity audit now compares exact logical paths in the 14 vehicle/cockpit BFFs. The 2026-09-28 corpus contains 1,375 paths with byte-identical stored payloads across at least 3 archives, including 1,309 FXO and 61 DDS paths. The evidence snapshot is evidence/vehicle_bff_raw_payload_parity_2026-09-28.json. This remains stored-byte evidence only.

For the base vehicle physics set, the corpus contains 7 CDF, 7 EDF, 7 GDF, 7 SDF and 7 TBF entries plus 5 BBF entries. `vehicles/physics/gearbox/common.gdf` is byte-identical in all 7 base vehicle archives; CDF/EDF names are vehicle-specific. The detailed snapshot is evidence/vehicle_bff_physics_parity_2026-09-28.json.

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


## Physics bundle extraction

`vehicle_physics_bundle.py` now resolves the default CDF/EDF/GDF/SDF/TBF/BBF set directly from a BFF. Exact BMW paths remain authoritative; non-BMW fallback uses vehicle-name matching and known shared basenames, and ambiguous selections fail closed. This makes the existing `VehiclePhysicsAssetGraph/1` parser directly reusable across the vehicle corpus.
