# Process 1 — composed global vehicle BODY-owner identity

## Playable-slice blocker reduced

Three independent pieces now define the physics-side vehicle pose identity:

```text
PR #1194  SHIFT.GlobalVehicleComponentBaseIdentity/1
          FUN_00770e80 receiver = global vehicle base 0x00c13700

PR #1195  SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
          FUN_00765470 entry ECX -> FUN_007b2270 BODY-owner ECX

PR #1188  SHIFT.BMWChassisBodyIdentityFrontier/1
          retail BMW main/chassis BODY = index 0
```

The local #1195 artifact deliberately cannot admit Phase 698 on its own. This
phase adds the missing semantic composition without re-proving any machine code.

## Contract

```text
SHIFT.GlobalVehicleBodyOwnerIdentity/1
```

Builder:

```text
tools/ghidra/build_global_vehicle_body_owner_identity.py
```

Inputs:

```text
SHIFT.GlobalVehicleComponentBaseIdentity/1
SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
SHIFT.BMWChassisBodyIdentityFrontier/1
```

## Positive composition

A positive #1195 receiver result means:

```text
FUN_00765470 entry ECX
  ==
FUN_007b2270 BODY-array owner ECX
```

The existing outer-update source contract already forwards the global vehicle
receiver as `FUN_00765470(this, ...)`, while #1194 independently proves that
outer receiver is the vehicle component base at `0x00c13700`.

Composing those facts gives:

```text
0x00c13700 global vehicle / outer receiver
  -> FUN_00765470 same receiver
  -> FUN_007b2270 same BODY-array owner
  -> retail BODY domain
  -> proven BMW chassis BODY 0
```

Only that complete composition emits:

```text
outer_receiver_to_BODY_owner_continuity_proven = true
vehicle_BODY_selection_ready = true
selected_BODY_index = 0
phase698_positive_selection_admissible = true
phase700_runtime_handoff_admissible = true
```

## Fail-closed rules

The builder rejects any input that tries to short-circuit the proof:

- #1194 must still have BODY-owner continuity and Phase 698 admission false;
- the obsolete update-child equality requirement must remain false;
- #1188 must select exact BODY name `body`, index 0, while its own vehicle BODY
  readiness remains false;
- the #1195 continuity/composition/rewrite flags must agree;
- a positive #1195 report must resolve the all-path receiver origin exactly to
  `entry:ECX`, be non-ambiguous, and have no blockers;
- the #1195 artifact must continue to state that it cannot admit Phase 698 by
  itself.

A negative #1195 report is accepted as a valid blocked input and produces a
blocked composed identity with `selected_BODY_index = null`.

## Current retail status

The repository does not yet contain the targeted retail
`SHIFT.GhidraFunctionInstructions/2` export for `FUN_00765470`. Therefore #1195
cannot yet produce a committed positive retail report.

This composition phase does **not** promote the synthetic regression result to
retail evidence. It prepares the exact downstream contract so that one future
positive read-only Ghidra result can flow directly into Process 2 without a new
identity model.

## Process 2 handoff

Process 2 Phase 698/700 already supports a proven BODY selection and persistent
BODY pose transport. Phase 703 still carries the now-obsolete historical
`update-child -> vehicle-base` typed gate from before PR #1194.

After a positive composed contract exists, Process 2 should consume
`SHIFT.GlobalVehicleBodyOwnerIdentity/1` instead and remove that obsolete proof
requirement. No second BODY-pose selector ABI is needed.

## Process 3 Phase 645 handoff

Phase 645 already proves the canonical retail BMW VHF vehicle-root/body-MEB bind
transform and its SVWT preparation path. It is a static resource bind transform,
not a dynamic physics pose.

Once the composed BODY-owner identity is positive and Phase 700 exposes BODY0,
the next cross-process blocker is specifically:

```text
persistent BODY0 pose frame
  -> exact frame/composition relation
  -> Phase 645 VHF vehicle-root/body-MEB bind frame
  -> dynamic SVWT for the prepared BMW renderer subgroup
```

Renderer object rediscovery is no longer the blocker.

## Preserved negative claims

This contract does not prove or assign:

- `*record+0x340 == 0x00c13700`;
- a retail `rear_axle` BODY index;
- BODY0 pose -> VHF/SVWT composition;
- camera follow;
- automatic deep-physics `fixed_step()` scheduling;
- original-game execution or new runtime capture.
