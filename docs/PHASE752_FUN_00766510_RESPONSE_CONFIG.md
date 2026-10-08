# Phase 752 — FUN_00766510 response config state

Phase 752 consumes `SHIFT.Fun00766510ResponseConfigOwnership/1` as a native state slice without promoting the full runtime response chain.

The setup-owned response configuration is pinned at:

- scalar `HDVehicle+0x3910`;
- curve helper state rooted at `+0x3918`;
- six-vector table rooted at `+0x3950`, count 6, stride `0x18`.

The persistent derived value `HDVehicle+0x3908` is explicitly not a setup constant. Its source-backed refresh is:

`+0x3908 = +0x3750 * s^2 + +0x3748 * s + +0x3740`, with selector `HDVehicle+0x3c78`.

The same refresh must be repeated after the proven mutator paths `FUN_00757e60`, `FUN_00758210`, and `FUN_00769d60`; Phase 752 therefore computes the derived value from the current coefficients and selector rather than freezing a selected setup result.

The runtime chain `curve(+0x3918) -> scale(+0x3910,+0x3908) -> six-vector response(+0x3950)` is recorded as ownership/order evidence only. Its exact combined arithmetic is not synthesized in this phase. Caller accumulation and diagnostics also remain external.

`contact_response` is not removed. The active external-provider count remains seven.
