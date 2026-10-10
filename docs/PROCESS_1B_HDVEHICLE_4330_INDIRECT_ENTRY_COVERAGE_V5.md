# Process 1B — HDVehicle+0x4330 indirect-entry coverage v5

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/5` supersedes `/4` and keeps a single current handoff for bounded exact-carrier indirect-entry evidence.

## Added coverage

The previous `/4` contract contained seven bounded classes with zero exact P1B carrier hits. `/5` adds two more:

1. **Statically reachable imported-GetProcAddress result storage**
   - 101 physical `GetProcAddress` callsites are covered by the corrected resolver/storage contracts;
   - exact internal P1B carrier identities in that bounded storage surface: **0**.
2. **Direct copy/store from an already-materialized exact canonical carrier value**
   - source-visible address-taking/value use is zero;
   - the composed bounded seed domains contain zero exact carrier hits;
   - direct known-carrier value copy origins: **0**.

The composed bounded class count is therefore **9**, with bounded exact carrier hits still **0**.

## Gates

The bounded coverage aggregate advances, but the following remain fail-closed:

- runtime-created or unrelated runtime-populated pointer tables;
- cross-block/table-derived exact-carrier reconstruction;
- runtime-generated/copied function pointers globally;
- generic function-pointer stores/copies globally;
- runtime patching/generated code;
- global indirect entry into the carrier set;
- `manager+0x374 -> HDVehicle+0x4330` identity;
- `0x004b86cf` final adjudication;
- aggregate P1.3.

Provider count remains 7.
