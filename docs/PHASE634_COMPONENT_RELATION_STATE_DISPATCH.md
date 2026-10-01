# Phase 634 — exact component dispatch for FUN_00757d2c

Phase 633 ported the two set-only relation-state mutation primitives recovered
inside `FUN_00757d2c`:

- unordered JOINT/HINGE pair matching;
- BAR single-endpoint matching.

Phase 634 corrects and closes the branch selector and four-slot wrapper from
raw x86 disassembly.

## Raw executable control flow

`FUN_00757d20` is a wrapper around the selected component slot:

```asm
757d20: mov eax,[ebp+8]
757d26: jmp 469736

469736: imul eax,eax,0xA80
46973c: jmp 757d2c
```

`FUN_00757d2c` then computes:

```text
component = vehicle + 0x400 + slot * 0xA80
```

and always sets component byte `+0x504 = 1`.

The critical branch is the pointer at component `+0x424`.

## Exact branch semantics

### component +0x424 is non-null

Retail sets component byte `+0x540 = 1`, scans only the BAR array and sets
relation `+0x70 bit0` when either BAR endpoint equals the `+0x424` BODY.

JOINT and HINGE arrays are not scanned in this branch.

### component +0x424 is null

Retail reads component `+0x420` and vehicle `+0x2E00`, then scans JOINT and
HINGE arrays for the unordered pair:

```text
(component.primary, vehicle.rear_axle)
```

BAR relations are not scanned in this branch.

If either pointer is null, no CSRF relation endpoint can match it, so the
neutral implementation leaves JOINT/HINGE state unchanged.

## Native representation

Phase 634 adds:

```cpp
ConstraintRelationComponentIdentity {
    optional primary_body_index;
    optional secondary_body_index;
}

ConstraintRelationVehicleComponentMap {
    components[4];
    optional rear_axle_body_index;
}

apply_fun_00757d2c_component_relation_state_mutation(...)
apply_fun_00757d20_component_slot_relation_state_mutation(...)
```

`std::optional<size_t>` is required because BODY index 0 is valid and must be
distinguished from a retail null pointer.

The four-slot wrapper rejects slot indices outside 0..3.

## Vehicle source mapping

Vehicle solver setup resolves the four repeated component fields through the
same SDF BODY lookup:

| Slot | vehicle field | source lookup |
|---:|---:|---|
| 0 | `+0x820/+0x824` | `fl_wheel/fl_spindle` |
| 1 | `+0x12A0/+0x12A4` | `fr_wheel/fr_spindle` |
| 2 | `+0x1D20/+0x1D24` | `rl_wheel/rl_spindle` |
| 3 | `+0x27A0/+0x27A4` | `rr_wheel/rr_spindle` |

The common vehicle `+0x2E00` field is the SDF lookup result for
`rear_axle`.

For the current BMW M3 E36 `aarm_multilink.sdf` evidence, the 11 BODY names
are:

```text
body,
fl_spindle, fr_spindle,
fl_wheel, fr_wheel,
rl_spindle, rr_spindle,
rl_wheel, rr_wheel,
fuel_tank, driver_head
```

There is no `rear_axle` BODY in that SDF, so the lookup is null. The four
wheel/spindle secondary pointers are present, therefore the current BMW path
selects the BAR branch for those components; the JOINT/HINGE rear-axle branch
cannot match a relation endpoint in this vehicle configuration.

Phase 634 does not hardcode a fake rear-axle BODY index.

## Regression coverage

`shift_runtime_constraint_relation_component_dispatch_check` proves:

- `FUN_00757d20` four-slot range;
- `0x400 + slot*0xA80` component layout provenance;
- non-null secondary selects only BAR mutation;
- null secondary selects only JOINT/HINGE mutation;
- JOINT/HINGE pair uses primary + rear-axle identities;
- null rear axle produces no JOINT/HINGE match;
- component `+0x504` is set in both branches;
- component `+0x540` is set only in the BAR branch;
- state mutation remains set-only.

## Boundary

The exact source branch and component-slot identity are now reconstructed.

Still intentionally outside `shift_runtime`:

- the runtime event that calls `FUN_00757d20(slot)`;
- when that event occurs relative to constraint refresh/reset/solve;
- live production of component pointer changes.

The next safe integration step is event/call-site provenance and timing, not
additional guessing about relation state.
