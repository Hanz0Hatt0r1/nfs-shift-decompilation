# Phase 742 — `FUN_00766510` primary response application

Phase 742 closes the source-backed application immediately after the already-native `FUN_007551e0` query-response builder inside `FUN_00766510`. It does **not** internalize the complete `FUN_00766510` anchor and does not reduce the external-provider count.

## PC retail sequence

The authoritative PC decompiler export shows:

```text
759686 FUN_007551e0(HDVehicle+0x3950, ..., local_1b8, ...)
759687 FUN_007aefb0((*(HDVehicle+0x33a0))+0xd4, local_1b8, local_120)
759688 FUN_007baa70(*(HDVehicle+0x33a0), HDVehicle+0x38f0, local_120)
```

Machine code at `0x00766fb2..0x00766fd6` independently fixes the same transform/application boundary and is SHA-256 locked in the Phase742 evidence. Earlier in the same machine block, `0x00766e8a` computes `edi = HDVehicle+0x38f0`, which becomes the second argument of `FUN_007baa70`.

The existing BMW identity proof already establishes:

```text
HDVehicle+0x33a0 = selected BMW chassis BODY pointer = BODY0
```

Therefore no new BODY identity or physical interpretation is introduced here.

## Native composition

`execute_fun_00766510_primary_response_application()` consumes:

- the existing `WheelContactResponse` result and specifically its `response_vector`;
- the current BODY frame used by retail `FUN_007aefb0`;
- the current BODY accumulator state;
- the caller-owned point/value triplet corresponding to `HDVehicle+0x38f0`.

It then performs exactly the already-admitted native operations:

1. `transform_fun_007aefb0_refresh(body_frame, response.response_vector)`;
2. `apply_fun_007baa70_body_accumulator(body_accumulator, application_point, transformed_response)`.

This avoids a second implementation of either the x87-backed transform or BODY accumulator arithmetic.

## Xbox corroboration

Xbox recomp partition `nfs_shift_recomp.220.cpp` independently preserves the same topology:

- response builder at vehicle `+0x3950`;
- BODY pointer from vehicle `+0x33a0`;
- transform through BODY `+0xd4`;
- application point from vehicle `+0x38f0`;
- BODY accumulator application using that BODY pointer and transformed response.

Xbox is corroboration only. PC source and PC machine code remain authoritative for this slice.

## Why the provider is not removed

`FUN_00766510` contains more work than this primary query-response application. Remaining source-visible work includes earlier response branches, optional branches, selected/caller configuration fields, diagnostic/state writes, and scheduling of the already-native auxiliary pair. Therefore `NativeVehicleExternalProviderBundle.contact_response` remains required and the active top-level frontier remains seven.
