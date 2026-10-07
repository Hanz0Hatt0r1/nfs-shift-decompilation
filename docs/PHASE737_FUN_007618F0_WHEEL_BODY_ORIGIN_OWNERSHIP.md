# Phase 737 — FUN_007618f0 wheel-BODY origin ownership

Phase 737 closes two of the four source inputs left external by Phase 728 without inventing new vehicle semantics.

## Proven ownership chain

Phase 728 proved that `FUN_007618f0` reads two f64 vec3 values through pointers stored at:

- `HDVehicle+0x820`;
- `HDVehicle+0x12a0`.

Phase 634 independently proved the named four-slot component geometry:

```text
FL wheel BODY pointer = vehicle+0x820
FR wheel BODY pointer = vehicle+0x12a0
```

Phase 702 then proved the selected BMW M3 E36 retail BODY identities:

```text
FL wheel BODY = BODY 3
FR wheel BODY = BODY 4
BODY count     = 11
```

The existing BODY ABI proves each BODY record has stride `0x170` and stores its f64 origin at `+0x00/+0x08/+0x10`.

Therefore the two Phase728 pointer-backed vec3 inputs are no longer caller-supplied values:

```text
vec(*HDVehicle+0x820)  = current persistent BODY[3] origin
vec(*HDVehicle+0x12a0) = current persistent BODY[4] origin
```

This identity comes from the named component/BODY topology proofs, not from matching numeric offsets alone.

## Native handoff

`shift_fun_007618f0_wheel_body_origin_ownership.hpp` exposes:

```text
compose_fun_007618f0_input_from_current_bmw_wheel_bodies(...)
```

The helper:

1. requires the exact selected BMW 11-record BODY domain;
2. consumes the source-backed BMW wheel topology;
3. selects BODY indices 3 and 4;
4. reads their current f64 origins from `+0/+8/+0x10`;
5. fills the existing `Fun007618f0LocalSampleProducerInput` wheel-origin fields;
6. forwards only the still-unresolved second-source `+0x338` and `+0x918` values.

The existing Phase728 arithmetic is unchanged.

## Timing

Phase729 already established a current persistent BODY observation for each recovered `FUN_0076d100` pass, with pass 1 observing state after the first `FUN_00765470` half-step. Phase737 therefore does not need a new BODY snapshot model.

However, this slice deliberately does not wire the helper into the complete production `FUN_00765c40` anchor yet. The second `FUN_007618f0` source argument is still unresolved, so doing so would replace one explicit boundary with guessed storage ownership.

## Remaining FUN_007618f0 input boundary

Only these source fields remain external to the exact Phase728 producer:

- second source argument f64 at `+0x338`;
- second source argument inline f64 vec3 at `+0x918`.

Once that source object's identity and refresh timing are proven, the native chain can be composed as:

```text
current BMW BODY[3]/BODY[4] origins
+ source +0x338/+0x918
-> FUN_007618f0 local sample
-> Phase727 BODY0 transform
-> FUN_00765c40 query world_position
```

That is the next route toward shrinking the complete `FUN_00765c40` provider boundary.

## Provider frontier

Phase737 removes two raw values from the unresolved world-position producer, but does not eliminate a complete top-level provider. The active external-provider count therefore remains seven.
