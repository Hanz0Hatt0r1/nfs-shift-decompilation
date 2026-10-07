# Phase 742 next blocker

The query-response application immediately following the native `FUN_007551e0` result is now closed as:

```text
WheelContactResponse.response_vector
-> FUN_007aefb0 with selected BODY0 +0xd4
-> FUN_007baa70 with selected BODY0 and HDVehicle+0x38f0
```

Do not remove the top-level `FUN_00766510` / `contact_response` provider yet. The next useful ownership slice is the caller configuration feeding this already-native path:

- `HDVehicle+0x38f0/+0x38f8/+0x3900` application-point triplet;
- `HDVehicle+0x3908` base term;
- `HDVehicle+0x3910` query-scalar slope;
- `HDVehicle+0x3918` directional-curve record;
- `HDVehicle+0x3950` response table.

In parallel, preserve the earlier `+0x3b20` response branch, the optional `+0x3bc8/+0x3cxx` branch, the native two-record auxiliary pair, and all source-visible diagnostic/state writes. Provider count may fall from seven only after the complete callback can be removed without dropping any of those operations.
