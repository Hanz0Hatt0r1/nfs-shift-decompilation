# Phase 634 — named four-slot FUN_00757d2c dispatch

Phase 633 ports the set-only relation-state mutation performed by
`FUN_00757d2c` and proves the 0..3 component trampoline plus the named
FL/FR/RL/RR wheel/spindle and rear-axle BODY fields. Phase 634 closes the next
static source boundary: selecting the correct normalized BODY identities for
one recovered vehicle component slot.

This phase still does **not** assign the retail event meaning or frame timing.

## Recovered slot geometry

Raw executable disassembly and `FUN_0076ed60` establish four component slots:

| Slot | Name | Component block | wheel field | spindle field |
|---:|---|---:|---:|---:|
| 0 | FL | `vehicle+0x400` | `vehicle+0x820` | `vehicle+0x824` |
| 1 | FR | `vehicle+0xE80` | `vehicle+0x12A0` | `vehicle+0x12A4` |
| 2 | RL | `vehicle+0x1900` | `vehicle+0x1D20` | `vehicle+0x1D24` |
| 3 | RR | `vehicle+0x2380` | `vehicle+0x27A0` | `vehicle+0x27A4` |

The component base is `0x400`, the stride is `0xA80`, and the BODY fields
are component-relative `+0x420` and `+0x424`. The named `rear_axle` BODY is
stored at vehicle `+0x2E00`.

Phase 634 represents those identities with
`VehicleConstraintBodyIdentityMap`; raw pointers remain replaced by the
existing CSRF BODY-index identity domain.

## Exact branch selection

Inside `FUN_00757d2c`, the selected component's `+0x424` BODY pointer is
loaded first.

When that spindle BODY pointer is null, retail scans JOINT and HINGE relations
for the unordered pair:

`slot.wheel ↔ rear_axle`

When the spindle BODY pointer is non-null, retail scans BAR relations for any
endpoint equal to:

`slot.spindle`

Phase 634 exposes this as:

`dispatch_fun_00757d2c_vehicle_slot_relation_state_mutation(...)`

The caller supplies the component slot and the observed spindle-presence state.
The dispatcher only selects the already-proven BODY identities and then invokes
the Phase 633 set-only mutation kernels.

It does not synthesize the spindle-presence value from unrelated state.

## Fail-closed checks

The dispatcher rejects:

- component slots outside the recovered 0..3 domain;
- any named wheel/spindle/rear-axle BODY index outside the CSRF BODY domain;
- all Phase 633 relation/state cardinality and endpoint-domain errors.

No distinctness rule is invented for the named BODY indices.

## Regression coverage

`shift_runtime_constraint_relation_state_dispatch_check` verifies:

- all four recovered component block offsets: `0x400`, `0xE80`, `0x1900`,
  `0x2380`;
- exact 0xA80 stride;
- wheel/rear-axle pair dispatch for slots 0 and 1;
- spindle BAR dispatch for slots 2 and 3;
- repeated BAR selection remains set-only;
- slot-domain and BODY-domain failures;
- scheduler integration remains disabled;
- event timing remains unassigned.

Linux Vulkan CI executes the checker independently of the native frame loop.

## Deliberate boundary

Phase 634 is a static dispatcher, not a scheduler event.

The project now has a source-backed chain from:

`named component slot → FUN_00757d2c relation bit0 mutation → FUN_007b3f40 reset selection → FUN_007b2210 reset`

but the first arrow still lacks runtime event provenance and timing.

The next safe boundary is retail runtime evidence that records which slot
triggers `FUN_00757d2c`, whether the slot spindle pointer is present at that
moment, and where that call sits relative to the solver frame. Only after that
evidence is captured should the dispatcher be wired into the fixed-step CRRF
path.
