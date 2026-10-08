# Phase 745 next blocker

Phase745 establishes the selected same-pass `FUN_00765c40 -> FUN_00766510` handoff inside `NativeVehicleProviderSession` without removing the residual contact-response provider.

## Phase746 target

Close the primary caller-accumulator delta immediately after the already-native Phase742 BODY application:

```text
FUN_00753650(application_point, transformed_response)
HDVehicle+0x40a0 += delta.x
HDVehicle+0x40a8 += delta.y
HDVehicle+0x40b0 += delta.z
```

Preserve the exact PC argument order and f64 store boundaries. Do not interpret this vec3 physically.

After Phase746, reassess the remaining `FUN_00766510` optional/auxiliary branches against Process1 proofs before removing `NativeVehicleExternalProviderBundle.contact_response`. Only that complete removal can legitimately reduce the active provider frontier from 7 to 6.
