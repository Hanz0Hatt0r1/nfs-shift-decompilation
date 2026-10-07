# Phase 731 scope

Phase 731 is limited to ownership of the `FUN_007675f0` distance-filter cap read from object offset `+0xa0`.

In scope:

- preserve the Phase 379 PC retail expression `FUN_00783a30(previous, distance, body_field+0xa0, 0.5)`;
- use the Xbox 360 counterpart only as independent corroboration that `+0xa0` belongs to the same vehicle/object state as `+0x4080`;
- remove `distance_filter_cap` from production per-pass `ContactOuterSessionInput`;
- require an explicit one-time setup seed because the initializer/value is not proven;
- preserve compatibility conversion for historical fixtures;
- preserve seven top-level external provider boundaries.

Out of scope:

- guessing the selected-session `+0xa0` value;
- claiming the `+0xa0` initializer or refresh schedule;
- naming physical units/semantics;
- internalizing the `planar_delta` producer;
- changing `FUN_00783a30` arithmetic;
- using Xbox offsets to override PC retail evidence.
