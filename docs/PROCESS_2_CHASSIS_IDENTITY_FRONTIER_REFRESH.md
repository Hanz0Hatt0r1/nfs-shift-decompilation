# Process 2 — provider and identity frontier refresh after Phase 703

## Playable-slice blocker reduced

This refresh keeps the Phase 699/701 external-provider graph aligned with the
current cross-process contracts. It does not add physics arithmetic or a new
numbered phase.

The important changes since the original frontier are:

```text
Process 1 #1188  BMW chassis BODY = 0
Process 1 #1194  global FUN_00770e80 receiver = vehicle component base
Process 1 #1195  FUN_00765470 BODY-owner receiver provenance frontier
Process 1 #1196  SHIFT.GlobalVehicleBodyOwnerIdentity/1 composition
Process 2 703    consumes that composed identity, old update-child equality gate removed
Process 3 645    exact BMW VHF static bind transform + VHF->SVWT convention
Process 3 646    dynamic vehicle transform transport core + exact vehicle draw-group identity
```

The provider graph must not continue requesting the obsolete
`*record+0x340 == vehicle base` proof or treat renderer object discovery as an
open blocker.

## Provider result

The deepest Phase 697 path, wrapped by the persistent Phase 701 provider session,
still has exactly nine external provider boundaries.

```text
external_provider_count = 9
implement_now            = 0
request_process1         = 9
runtime_only_blocked     = 0
```

No new Process 1 result proves a complete producer strongly enough to replace
one of these nine boundaries. Integration depth therefore must not be faked by
substituting host math, guessed control state, or partial kernels.

## Current vehicle/BODY identity boundary

The authoritative identity model is now:

```text
SHIFT.GlobalVehicleBodyOwnerIdentity/1
```

It composes global vehicle base identity, `FUN_00765470` BODY-owner receiver
provenance and BMW chassis BODY 0. Phase 703 consumes this contract directly and
reuses the existing Phase 698 selector plus Phase 700 runtime pose handoff.

The historical update-child equality condition is explicitly not required.

Current retail admission remains blocked because the targeted retail
`SHIFT.GhidraFunctionInstructions/2` export for `FUN_00765470` is not committed,
so Process 1 cannot yet prove entry ECX reaches `FUN_007b2270` as BODY-array
owner ECX on the required paths.

The correct request is therefore only that finite instruction/provenance proof,
not another vehicle-base identity search.

## FUN_00765470 provider boundary remains larger than identity

Closing BODY-owner receiver identity will not by itself implement
`Fun00765470MachineScalarHalfStepProvider`. The provider still needs exact
source-backed producers for its fields and proof of which values refresh before
pass 0, pass 1, both, or another recovered boundary.

The frontier therefore records both facts separately:

- receiver identity: narrowed to one missing targeted instruction export/proof;
- composite producer semantics/scheduling: still external and Process 1-owned.

## Renderer side after Phases 645/646

Renderer object identity and generic transform transport are no longer semantic
unknowns.

Phase 645 proves the canonical BMW VHF body-MEB static bind transform and exact
column-vector VHF -> row-vector SVWT transpose. Phase 646 adds authoritative
`track|vehicle` draw grouping and a non-cumulative native per-step transform
core.

The remaining semantic join is narrower:

```text
persistent BODY0 pose frame
-> exact composition with Phase 645 VHF vehicle-root/body-MEB bind frame
-> proven vehicle world matrix
-> Phase 646 transform transport
```

Phase 646 still stops before live Vulkan-buffer mutation; that is a Process 3
mechanical wiring task and must not be confused with the missing BODY-frame
proof.

## Other remaining joins

The following remain unchanged and fail-closed:

- exact outer-update cadence owner; explicit outer update must not be silently
  attached to `fixed_step()`;
- retail resources -> concrete initial `0x170` BODY records;
- all machine-scalar sqrt/trig/x87 boundaries in Phase 692;
- complete producers for the remaining eight provider rows besides the narrowed
  `FUN_00765470` ownership evidence.

## Safety / parity

The refreshed frontier preserves:

- two half-steps and recovered ordering;
- persistent BODY bytes and typed snapshots;
- participant admission before side effects;
- missing-provider fail-closed behavior;
- no host `sqrt/sin/cos` substitution;
- no update-child pointer equality requirement;
- no promotion of the Phase 645 static VHF bind transform as a dynamic pose;
- no claim that Phase 646 transport proves BODY0/VHF frame composition;
- no original `SHIFT.exe` execution and no new runtime capture.

## Next Process 2 action

There is currently no source-backed provider that can be replaced immediately.
Process 2 should consume the first new positive producer proof from Process 1.
The highest-impact pending proof is the targeted `FUN_00765470` instruction
export because it can make the global BODY-owner identity positive and unlock
retail BODY0 selection through the already-implemented Phase 703/698/700 path.

Once that identity is positive, the next dynamic vehicle-transform blocker is
BODY0 pose frame -> Phase 645 VHF bind-frame composition; renderer transport
plumbing already has the Phase 646 core.
