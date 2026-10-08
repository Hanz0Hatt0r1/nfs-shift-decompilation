# Phase 751 — FUN_00766510 optional response state

Phase 751 consumes `SHIFT.Fun00766510OptionalResponseBranchOwnership/1` without promoting unproven runtime arithmetic.

The native slice records the setup-owned optional block:

- gate byte at `HDVehicle+0x3bc8`;
- initial mutable value at `+0x3bd0`;
- coefficient block `+0x3bd8/+0x3be0/+0x3be8/+0x3bf0/+0x3bf8/+0x3c00/+0x3c08/+0x3c10/+0x3c30`;
- derived shape `+0x3c18/+0x3c20/+0x3c28/+0x3c38`;
- curve helper state at `+0x3c40`;
- application vector `+0x3c60/+0x3c68/+0x3c70`.

`HDVehicle+0x3bd0` remains persistent mutable state. Process 1 proves the complete writer surface for this slice: setup evaluation, `FUN_00757fa0`, `FUN_00758170`, `FUN_00769d60`, and `FUN_0076ed60`. The ownership contract does not promote the exact arithmetic of every mutator, so Phase 751 accepts each source-computed result explicitly instead of synthesizing increment/clamp/reset formulas.

The exact runtime gate is internalized:

`+0x3bc8 != 0 && local_50 < 0`.

The following remain outside this phase: coefficient polynomial/clamps, the curve-scaled negative-result path, `FUN_007af040`, `FUN_007baa70`, caller accumulation, and optional diagnostics. Therefore `contact_response` is not removed and the active external-provider count remains seven.
