# Process 1A — `FUN_00713630` participant `+0x4b0` frontier

## BLOCKER

After the config-global owner/materialization and sample-history scheduling were closed, P1.1a still requires the exact producer of the f32 value read from the selected PhysicsParticipant at `+0x4b0` by `FUN_00713630`.

## OUTPUT

`SHIFT.Fun00713630Participant4b0Frontier/1` turns that final unknown into a bounded writer frontier without assigning identity from a shared numeric offset.

The selected object path is already exact:

```text
manager record (stride 0x1fa0)
  -> FUN_007125e0
  -> allocate 0x2b90 with flag 0x20
  -> FUN_0072ed20(actual PhysicsParticipant)
  -> [manager record+0] = actual PhysicsParticipant
```

The existing allocator proof establishes a full zero-fill before construction. Therefore actual participant `+0x4b0` is f32 zero immediately after the allocation zero-fill. This is only a pre-constructor value; it is not promoted to the value later consumed by `FUN_00713630`.

The exact `FUN_0072ed20` machine body (`0x0072ed20..0x0072f1a9`) contains no direct receiver-relative store to `+0x4b0`. Callee-mediated/alias writes during construction remain possible.

A retail-image machine scan finds exactly 16 direct stores whose destination operand is a base register plus displacement `0x4b0`. The previously tempting site `0x00748956` in `FUN_00748280` is already rejected: that receiver is the fixed PhysicsTweaker object `DAT_00c12c40`, not a selected PhysicsParticipant. The other 15 sites remain identity candidates only; none is promoted by offset equality.

Known selected-participant code in `FUN_00713630`, `FUN_00736510`, `FUN_00736f20`, and `FUN_007473b0` reads `+0x4b0` directly but does not provide the missing direct write.

## GATES_CHANGED

- selected manager-record to actual `0x2b90` PhysicsParticipant identity: **closed**;
- pre-constructor `+0x4b0 == 0.0f` after allocation zero-fill: **closed**;
- direct store inside `FUN_0072ed20` body: **absent/closed**;
- whole-image direct-displacement `+0x4b0` store inventory: **bounded to 16 sites**;
- `FUN_00748280 +0x4b0` PhysicsTweaker candidate: **rejected**;
- remaining direct-site object identities: **open**;
- computed/alias/bulk writer surface: **open**;
- P1.1a complete: **false**;
- P1.1 complete: **false**;
- external provider count: **7**.

## NEXT_STEP

Join or reject the remaining 15 direct-displacement writer sites against the exact `0x2b90` PhysicsParticipant root. If none survives, continue with computed-address, escaped-alias and bulk-copy writers. Provider reduction remains forbidden until this runtime producer is closed and the final Process 1 handoff is published.
