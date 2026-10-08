# Phase 747 — `FUN_00766510` shared reference-vector ownership

Phase747 closes the source owner and transform of the shared `local_d8/local_d0/local_c8` vector used by the early `+0x3b20` response branch and later contact-response work. It does not claim the dynamic source value is native yet.

## Owner chain

PC retail `FUN_0076df50` stores its initialization manager record at:

```text
HDVehicle+0x3fe8
```

The already-proven `SHIFT.OuterVehicleChassisOwnerJoin/1` contract establishes the corresponding participant chain:

```text
HDVehicle
 -> [HDVehicle+0x3fe8]
 -> dereference
 -> actual participant
```

`FUN_00766510` uses the same chain and reads three float lanes from the participant at:

```text
+0x16b4
+0x16b8
+0x16bc
```

Each lane is explicitly widened from f32 to f64 before the existing `FUN_007af0a0` BODY-frame transform.

## Dynamic writer

The source vector is not immutable setup data. PC `FUN_00713630` writes the participant lanes:

```text
participant+0x16b4 = dynamic f32 X
participant+0x16b8 = 0.0f
participant+0x16bc = dynamic f32 Z
```

`FUN_007144a0` calls `FUN_00713630` when its manager counter/state at `+0x158` is divisible by three. Phase747 freezes this only as a source-visible update cadence; it does not assign physical meaning to the generated X/Z values.

## Consumer

In `FUN_00766510` the three source floats are widened to doubles and passed through:

```text
FUN_007af0a0(BODY0+0xd4, participant_source, local_d8)
```

The active native helper `execute_fun_00766510_shared_reference_vector()` reproduces exactly that boundary by accepting three f32 lanes, widening them independently to f64, then delegating to the already machine-backed `transform_fun_007af0a0_refresh()`.

## Consequence

This removes the anonymous ownership of `local_d8/local_d0/local_c8`. The remaining boundary is earlier and concrete: the dynamic actual-participant `+0x16b4/+0x16b8/+0x16bc` writer state.

The top-level provider count remains **7**. `contact_response` cannot be removed yet because the optional `+0x3bc8/+0x3cxx` branch and the dynamic participant source materialization are still not fully integrated.
