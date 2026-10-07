# Phase 728 — FUN_007675f0 BODY0 motion ownership

## Result

Phase 728 narrows the typed external input boundary for the already-native `FUN_007675f0` outer arithmetic without claiming the remaining caller-side producers.

PC retail evidence already establishes that the speed gate reads the current chassis BODY motion lanes at `BODY+0x78` and `BODY+0x88`. `SHIFT.BodyFrameIntegrationStatic/1` separately proves that those persistent BODY lanes are advanced inside each `FUN_00765470` half-step. They therefore belong to the native persistent BODY state, not to the session-level `FUN_007675f0` external provider.

The session-facing provider now returns `ContactOuterExternalInput`, which retains only:

- `planar_delta`;
- `previous_distance_state`;
- `distance_filter_cap`;
- `surface_scalar`;
- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`;
- `param_3`.

`speed_x` and `speed_z` are absent from that contract.

## Per-pass freshness

The BODY motion values cannot be snapshotted once at the start of `FUN_00770e80`. Retail ordering is:

```text
FUN_0076d100 pass 0
FUN_00765470 half-step 0
FUN_007b8810
FUN_0076d100 pass 1
FUN_00765470 half-step 1
FUN_007b8810
```

Phase 728 therefore adds a narrow current-BODY observer to the composed anchor chain. Immediately before each `FUN_0076d100` anchor sequence, the `FUN_007675f0` adapter decodes BODY0 `+0x78/+0x88`. Pass 1 consequently observes the BODY bytes committed by the first half-step instead of reusing pass-0 values.

This current-BODY observer is also the timing primitive required by Phase 727's `FUN_00765c40` world-position transform. Phase 728 does not silently join that transform to the still-external local-sample producer or collision provider; it only establishes the exact per-pass BODY snapshot transport.

## Compatibility

`ContactOuterKernelInput` remains the complete arithmetic input used by the Phase 662 kernel and by historical fixtures. A compatibility conversion to `ContactOuterExternalInput` deliberately discards legacy `speed_x/speed_z` members. Production composition re-injects speed only from `Fun007675f0BodyMotion` derived from current BODY0.

## Fail-closed behavior

The BODY motion owner rejects:

- empty or non-`0x170`-multiple BODY buffers;
- out-of-range BODY0 reads;
- non-finite `+0x78` or `+0x88` values;
- execution of the `FUN_007675f0` anchor before the current BODY observer has supplied motion for that pass.

## Scope

Phase 728 does not internalize the remaining eight `FUN_007675f0` input fields, does not assign stronger physical names or units to the motion lanes, and does not reduce the seven active top-level external provider boundaries. It only removes two fields whose native owner is already proven.

Phase 727 remains authoritative for the `FUN_00765c40` local-sample-to-world-position transform. Its local-sample producer and collision provider remain separate blockers.
