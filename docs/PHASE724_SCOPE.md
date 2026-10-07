# Phase 724 scope

Phase 724 is intentionally limited to the selected-session `DAT_00c128cc` ownership closure and the removal of the final late `FUN_007682c0` raw-input provider.

In scope:

- join the existing explicit native `player_difficulty = 1` selection to the proven retail `RaceModeInfo+0x6c -> DAT_00c128cc` mapping;
- preserve the retail difficulty domain `{0,1,2}`;
- consume the selected value in native `FUN_007682c0` machine-input composition;
- remove `Fun007682c0ExternalMachineInput` and `NativeVehicleMotionReadInputProvider` from the active session API;
- reduce the current active external provider count from eight to seven;
- keep all earlier S5/S6 transform, timing, gate, steering, load-term, response-field and projection-state proofs intact.

Out of scope:

- claiming that retail live-session difficulty was observed as `1`;
- treating the retail profile initialization value as selected-session proof;
- deriving the still-explicit selected `FUN_007560c0` setup-gate value;
- internalizing complete `FUN_00765c40` contact/collision semantics or any other remaining provider;
- changing renderer/frame scheduling or substituting host `1/60` timing.
