# Process 1B — render-manager machine-CFG call-boundary reconciliation

## Scope

The machine-CFG replay over all 112 exact `DAT_00bc185c` loads observes 303 call boundaries at 302 unique callsites. This slice partitions those callsites without reopening the already merged direct-callee ownership work.

## Partition

- 207 unique callsites carry the exact outer root only in callee-saved registers.
- 95 unique callsites have the exact root in at least one caller-saved register (`EAX`, `ECX`, or `EDX`).
- Of those 95, 92 are direct calls and exactly three are indirect calls.
- 41 unique callsites are `EAX`-only residue; no ABI argument meaning is inferred from that fact.
- 54 unique callsites are receiver-like through `ECX` and/or `EDX`; 51 are direct and three are indirect.

## Indirect reconciliation

The three machine-wide indirect callsites are exactly:

- `0x0056bcf2` -> merged slot `+0x1c`;
- `0x0056bd09` -> merged slot `+0x20`;
- `0x0056bd59` -> merged slot `+0x1c`.

These are the same three indirect receiver transfers already frozen by `SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1`. No new machine-only indirect exact-root dispatch appears, and slot `+0x0c` / `FUN_0045b130` does not reappear.

## Boundary

The 92 direct callsites are not re-proven here; the merged receiver-transfer/direct-callee contracts own that surface. The remaining Process 1B risk is therefore opaque callee-created/returned aliases, external/unknown-origin aliases, and two-unknown-origin reconstruction rather than another first-hop indirect dispatch from the exact global root.

P1.3, the manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, and provider removal remain fail-closed. Provider count remains 7.
