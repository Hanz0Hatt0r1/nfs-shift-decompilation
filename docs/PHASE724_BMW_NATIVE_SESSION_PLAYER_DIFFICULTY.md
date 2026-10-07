# Phase 724 — selected native Player Difficulty owns DAT_00c128cc

## Result

Phase 724 closes the last late `FUN_007682c0` raw machine-input field for the selected `Silverstone+BMW_M3_E36` native vertical slice.

The join is deliberately narrower than a retail-session observation:

- `SHIFT.BMWOffset33bNativeSessionSelection/1` already selects `player_difficulty = 1` as explicit native vertical-slice policy.
- Existing PC retail selector evidence proves the valid `Player Difficulty (0-2)` domain is `{0,1,2}`.
- Existing PC static control-flow evidence maps `RaceModeInfo+0x6c` through the race-mode staging copy to `DAT_00c128cc`.
- `FUN_007682c0` consumes `DAT_00c128cc` as the angle-limit selector (`<2` takes the 40-degree branch, `>=2` the 55-degree branch).

Therefore the selected native policy value can be consumed directly by the native machine-input composition. The profile initialization value `1` is **not** used as proof: the retail profile field is mutable, and the selected native policy was already explicit independently of that initialization.

## Native change

`shift_bmw_native_session_player_difficulty.hpp` publishes the selected value and constrains it to the proven retail domain. `compose_fun_007682c0_machine_input` consumes that helper directly.

The active `NativeVehicleProviderSession` no longer exposes `NativeVehicleMotionReadInputProvider`, `Fun007682c0ExternalMachineInput`, or a per-pass `motion_read_input` callback. The lower internal `Fun007682c0MachineInputProvider` remains: it is the native pass-chain interface carrying an already-composed machine input, not an external provider boundary.

## Frontier effect

The immutable Phase 699 inventory remains nine boundaries for history. The current executable S6 frontier drops from eight to seven active external provider/ownership boundaries because both legacy `fun_007682c0_delta_consumer` and `fun_007682c0_effect_provider` are now fully closed for the selected session.

No transform, retail scheduler, `FUN_007560c0` gate, steering, selected-BMW `+0x4054`, projection-state, or typed `FUN_00765c40` load ownership is reopened.

## Non-claims

Phase 724 does not claim that every retail race uses difficulty `1`, does not infer a live retail session setting from the profile initialization default, and does not internalize the remaining complete contact/collision providers. The selected native policy remains explicit and source-domain validated.
