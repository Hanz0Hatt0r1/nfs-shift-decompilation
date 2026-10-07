# Phase 741 — selected BMW `FUN_00765c40` query fallback ownership

Phase 741 removes the selected BMW M3 E36 `HDVehicle+0x38e8` value from residual per-pass provider authority. It does not name the field physically; `query fallback` is the source-visible role already frozen by Phases 370/666/726.

## PC retail setup producer

PC retail `FUN_00756bb0` performs the relevant setup sequence:

```text
HDVehicle+0x38dc = 0
value = FUN_007a6be0(setup_param_2 + 0x6a4)
store f32(value) -> setup_param_2 + 0x6a8
widen the same f32 -> f64
store f64 -> HDVehicle+0x38e8
```

The instruction span `0x00756c40..0x00756c7c` is SHA-256 locked in the Phase741 evidence. The PC machine path contains the explicit f32 store before the f64 caller-state store; therefore the selected value must not be represented as the mathematical binary64 literal `0.1`.

## Source field

`FUN_007c0a20` parses the `FRONTWING` section. Its `FWMaxHeight` call targets front-wing record `+0x04`. That front-wing record is the setup object at `param_2+0x6a0`, so the parsed base scalar is `param_2+0x6a4`.

For the ordinary text CDF parser, `FUN_007a75a0` uses the `%f` path and writes the scalar directly. `FUN_007c08a0` initializes the modifier-chain slot to null; the selected normal BMW CDF path does not attach a modifier list for this scalar. Consequently `FUN_007a6be0` evaluates the selected scalar as its parsed base value.

## Selected BMW resource

The extracted retail resource `vehicles\\physics\\chassis\\bmw_m3_e36.cdf` has SHA-256:

```text
bbee83f0d2fdcbfc2bbd62ddb2a10bf6fed71bb1b4fa78f303a4730d038b970d
```

and contains:

```text
[FRONTWING]
FWMaxHeight=(0.10)
```

The exact source/storage path is therefore:

```text
CDF 0.10
-> parsed f32 bits 0x3dcccccd
-> FUN_007a6be0 selected no-modifier result
-> explicit f32 spill/store at setup+0x6a8
-> widen that f32 to f64 bits 0x3fb99999a0000000
-> HDVehicle+0x38e8
```

## Runtime handoff

`SHIFT.Fun00765c40ExternalPassInput/2` extends the Phase740 pre-call request. On the selected BMW path, Phase739 already makes native `world_position` present before the residual provider runs. That selected-session tag now also exposes `selected_bmw_miss_fallback()`.

The residual provider still returns its complete query-input witness, but validation now rejects a selected-BMW result whose `query_input.miss_fallback` differs from the native source-backed value. Generic historical fixtures have no selected-BMW world-position request and therefore retain their compatibility fallback values.

## Xbox corroboration

Xbox recomp partition `nfs_shift_recomp.118.cpp` independently shows the corresponding setup shape:

```text
stw 0     -> HDVehicle+14556 / 0x38dc
call evaluator with setup+1700 / 0x6a4
stfs f1   -> setup+1704 / 0x6a8
stfd f1   -> HDVehicle+14568 / 0x38e8
```

This is corroboration only. PC source/machine code and the PC retail CDF remain authoritative for PC value and precision.

## Scope

The seven top-level external provider boundaries remain seven. Phase741 only narrows the residual `FUN_00765c40` input ownership for the selected BMW query path. Collision-provider behavior, four load terms and remaining side effects are still external. `+0x38e8` is also read by `FUN_00766510` as an upper clamp bound; this phase does not claim that the separate contact-response boundary is closed.
