# Phase 503 — BFF to pre-PhysX/provider handoff

## Goal

Phase 503 adds a single orchestration entry point from a vehicle BFF to the
source-backed pre-PhysX/provider handoff:

`BFF → CDF/EDF/GDF/SDF/TBF/BBF extraction → VehiclePhysicsAssetGraph/1 → SDF report → PrePhysXProviderHandoffRuntime/1`

Contract:

`SHIFT.VehiclePhysicsPrePhysXHandoff/1`

## CLI

    python tools/build_vehicle_physics_handoff.py BMW_M3_E36.bff out/bmw-handoff

The command creates:

- `vehicle_physics_handoff.json` — complete top-level manifest;
- `vehicle_physics_asset_graph.json` — canonical vehicle physics profile;
- `prephysx_provider_handoff.json` — Phase 502 cross-contract handoff.

`--strict` is forwarded to the canonical vehicle physics extractor.

## Semantics

The report keeps the bundle, asset graph and pre-PhysX/provider handoff as nested
evidence domains. Provider candidates are only dimension-compatible candidates;
runtime `+0x14` acceptance is not executed or inferred.

`ready=true` requires the underlying vehicle bundle and the Phase 502 handoff to
be ready. Bundle parser blockers are propagated unchanged.

## Scope boundary

Phase 503 does not create runtime provider observations, capture packed workspace
values, or infer PhysX class identities. A real provider frame remains required
for numerical retail/provider differential.
