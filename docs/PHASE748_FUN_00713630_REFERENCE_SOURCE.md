# Phase 748 — native `FUN_00713630` dynamic reference-source producer

Phase 747 identified the exact actual-participant source consumed by `FUN_00766510`:

```text
participant+0x16b4/+0x16b8/+0x16bc (f32)
-> explicit f32-to-f64 widening
-> FUN_007af0a0(BODY0+0xd4)
-> local_d8/local_d0/local_c8
```

Phase 748 closes the arithmetic that writes those three participant lanes. It deliberately stops before materializing the writer's earlier runtime inputs.

## Manager cadence

PC `FUN_007144a0` reads the manager counter at `+0x158` and calls `FUN_00713630` exactly when:

```text
manager_counter % 3 == 0
```

`FUN_00713630` walks `manager+0x140` for `manager+0x144` records using byte stride `0x1fa0`. Only records whose byte `+0x4e` is nonzero execute the participant writer.

This cadence is exposed as `fun_007144a0_should_refresh_reference_source()`. Phase 748 does not yet schedule it in `NativeVehicleProviderSession`.

## Three-record aggregate

For each active participant, retail reads exactly three `f32[3]` records beginning at participant `+0x2b10`, stride `0x0c`, and feeds each record to `FUN_00712940`.

`FUN_00712940` consumes seven runtime-global f32 values. Phase 748 keeps them deliberately role-named and explicit:

```text
DAT_00c12eec -> record_0_limit
DAT_00c12ef4 -> record_0_scale
DAT_00c12ef0 -> record_0_offset
DAT_00c12ee0 -> record_2_ramp_begin
DAT_00c12ee4 -> record_2_ramp_end
DAT_00c12ee8 -> record_2_divisor
DAT_00c12f04 -> final_output_scale
```

Their runtime owner/value is not inferred here.

The aggregate helper preserves the source-visible f32 spill boundaries around the gate expression, gate ratio, first-lane ratio, square-root result, squared ratio, ramp, per-record contribution, both accumulators and the final scale.

## Trigonometric wrappers

The two PC CRT helpers are no longer opaque:

- `0x00900c40` executes x87 `FSIN`;
- `0x00900b10` executes x87 `FCOS`.

`FUN_00713630` calls `FSIN` first and `FCOS` second on participant `+0x4b0`, explicitly spilling both results to f32. The native helper reproduces those x87 operations under the retail `0x027f` control word on x86 hosts.

## Output

After the aggregate, PC retail computes:

```text
scale = f32(DAT_00c12f04 * secondary_aggregate)
participant+0x16b4 = f32(-FSIN(f32(participant+0x4b0)) * scale)
participant+0x16b8 = 0.0f
participant+0x16bc = f32(-FCOS(f32(participant+0x4b0)) * scale)
participant+0x2128 = primary_aggregate
participant+0x212c = secondary_aggregate
```

The returned source vector uses the exact `Fun00766510ParticipantReferenceSource3f` type introduced by Phase 747, so the producer and consumer now share one typed boundary.

## Earlier sample writer

PC `FUN_00727870` is a source-visible writer for the three-record history. A new qualifying record enters `+0x2b10`; existing samples shift to `+0x2b1c` and `+0x2b28`. This proves the records are dynamic participant state rather than immutable selected-session constants.

Phase 748 records that owner but does not attempt to reproduce all qualifying event/collision scheduling that calls `FUN_00727870`.

## Scope

The active top-level provider count remains **7**. This phase removes the arithmetic mystery between the earlier participant/config state and Phase747's source vector; it does not yet remove `contact_response`.

The next safe integration target is the earlier input materialization: the seven runtime config globals, the participant three-record history and participant `+0x4b0`, together with the exact `%3` manager cadence. Process1 residual `FUN_00766510` state/diagnostic audit also remains a gate before claiming full provider removal.
